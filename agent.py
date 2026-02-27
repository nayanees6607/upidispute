"""
agent.py — AI-Enhanced UPI Dispute Resolution Agent
----------------------------------------------------
This module contains the "brain" of the system. When triggered it:

1. Fetches all PENDING disputes from the database.
2. Transitions each dispute to INVESTIGATING (logged to AuditLog).
3. Calls the Mock Bank and Mock Merchant verification endpoints.
4. 🤖 Calls the AI Service for intelligent analysis (risk score, recommendation).
5. If AI is unavailable, falls back to the Decision Matrix:
   ┌──────────────────┬─────────────────────┬──────────────────────────────┐
   │ Bank Status      │ Merchant Status     │ Action                       │
   ├──────────────────┼─────────────────────┼──────────────────────────────┤
   │ DEBITED          │ NOT_RECEIVED        │ Initiate refund → RESOLVED   │
   │ DEBITED          │ RECEIVED            │ Txn→SUCCESS   → RESOLVED     │
   │ FAILED           │ NOT_RECEIVED        │ Txn→FAILED    → RESOLVED     │
   └──────────────────┴─────────────────────┴──────────────────────────────┘
6. Logs every state transition + AI analysis to AuditLog for auditing.

The function `run_agent` is designed to be called within a Flask app context.
"""

from datetime import datetime, timezone, timedelta

import requests

from ai_service import analyze_dispute
from config import Config
from models import AuditLog, Dispute, Transaction, db


def _log(dispute: Dispute, message: str) -> None:
    """Helper — append an entry to the AuditLog for a dispute."""
    entry = AuditLog(
        dispute_id=dispute.dispute_id,
        state_change=message,
        timestamp=datetime.now(timezone.utc),
    )
    db.session.add(entry)
    db.session.flush()


def _set_status(dispute: Dispute, new_status: str) -> None:
    """Helper — update dispute status and log the transition."""
    old_status = dispute.current_status
    dispute.current_status = new_status
    if new_status == "RESOLVED":
        dispute.resolved_at = datetime.now(timezone.utc)
    _log(dispute, f"{old_status} → {new_status}")


def _count_user_disputes(user_id: str) -> int:
    """Count how many disputes this user has raised historically."""
    return (
        db.session.query(Dispute)
        .join(Transaction, Dispute.txn_id == Transaction.txn_id)
        .filter(Transaction.user_id == user_id)
        .count()
    )


def _get_resolution_history(limit: int = 10) -> str:
    """Fetch recent resolved disputes as learning context for the AI."""
    resolved = (
        Dispute.query
        .filter(Dispute.current_status == "RESOLVED")
        .order_by(Dispute.resolved_at.desc())
        .limit(limit)
        .all()
    )
    if not resolved:
        return "No previous resolution history available."

    lines = []
    for d in resolved:
        txn = db.session.get(Transaction, d.txn_id)
        if not txn:
            continue
        last_log = d.audit_logs[-1] if d.audit_logs else None
        resolution_info = last_log.state_change if last_log else "Unknown"
        lines.append(
            f"  - TXN {txn.txn_id}: Amount=₹{txn.amount}, "
            f"BankStatus={txn.status}, "
            f"UserReason='{d.user_reason or 'N/A'}', "
            f"Resolution={resolution_info}"
        )
    return "\n".join(lines)


def run_agent(app) -> dict:
    """
    Execute the AI-enhanced resolution agent inside the given Flask app context.

    Returns a summary dict with counts of resolved disputes by category.
    """
    base = Config.BASE_URL
    api_key = Config.MOCK_BANK_API_KEY

    results = {
        "processed": 0,
        "refunds_initiated": 0,
        "false_alarms": 0,
        "standard_failures": 0,
        "unresolved": 0,
        "ai_analyzed": 0,
        "rule_fallback": 0,
        "details": [],
    }

    with app.app_context():
        # Step 1 — Fetch all PENDING disputes
        pending_disputes = Dispute.query.filter_by(current_status="PENDING").all()

        if not pending_disputes:
            return {"message": "No pending disputes to process.", **results}

        for dispute in pending_disputes:
            results["processed"] += 1

            # Step 2 — Mark as INVESTIGATING
            _set_status(dispute, "INVESTIGATING")
            db.session.commit()

            txn_id = dispute.txn_id

            # Step 3 — Call Mock Bank & Mock Merchant verification endpoints
            try:
                bank_resp = requests.get(f"{base}/mock-bank/verify/{txn_id}", timeout=10)
                bank_data = bank_resp.json()
                bank_status = bank_data.get("bank_status", "UNKNOWN")
            except Exception as exc:
                _log(dispute, f"Bank verification failed: {exc}")
                results["unresolved"] += 1
                db.session.commit()
                continue

            try:
                merchant_resp = requests.get(
                    f"{base}/mock-merchant/verify/{txn_id}", timeout=10
                )
                merchant_data = merchant_resp.json()
                merchant_status = merchant_data.get("merchant_status", "UNKNOWN")
            except Exception as exc:
                _log(dispute, f"Merchant verification failed: {exc}")
                results["unresolved"] += 1
                db.session.commit()
                continue

            _log(
                dispute,
                f"Verification complete — Bank: {bank_status}, Merchant: {merchant_status}",
            )

            txn = db.session.get(Transaction, txn_id)

            # ══════════════════════════════════════════════════════════════
            # Step 4 — 🤖 AI Analysis
            # ══════════════════════════════════════════════════════════════
            
            # Calculate Contextual Factors
            previous_disputes = _count_user_disputes(txn.user_id)
            
            now = datetime.now(timezone.utc)
            txn_time = txn.timestamp.replace(tzinfo=timezone.utc) if txn.timestamp.tzinfo is None else txn.timestamp
            delta = now - txn_time
            time_since = f"{int(delta.total_seconds() // 60)} minutes"
            
            # Count potential duplicates (same user, merchant, amount within a 5 min window)
            five_mins_ago_naive = txn.timestamp - timedelta(minutes=5)
            duplicate_count = Transaction.query.filter(
                Transaction.user_id == txn.user_id,
                Transaction.merchant_id == txn.merchant_id,
                Transaction.amount == txn.amount,
                Transaction.txn_id != txn.txn_id,
                Transaction.timestamp >= five_mins_ago_naive,
                Transaction.timestamp <= txn.timestamp + timedelta(minutes=5)
            ).count()

            # Fetch resolution history for pattern learning
            resolution_history = _get_resolution_history(limit=10)

            ai_result = analyze_dispute(
                txn_id=txn_id,
                amount=txn.amount,
                bank_status=bank_status,
                merchant_status=merchant_status,
                user_id=txn.user_id,
                time_since=time_since,
                duplicate_count=duplicate_count,
                previous_disputes=previous_disputes,
                dispute_reason=dispute.user_reason or "Money debited but merchant did not receive",
                resolution_history=resolution_history,
            )

            detail = {
                "dispute_id": dispute.dispute_id,
                "txn_id": txn_id,
                "bank_status": bank_status,
                "merchant_status": merchant_status,
                "ai_analysis": None,
            }

            if ai_result:
                # ── AI analysis available ─────────────────────────────
                results["ai_analyzed"] += 1

                detail["ai_analysis"] = {
                    "fraud_risk_score": ai_result["fraud_risk_score"],
                    "risk_level": ai_result["risk_level"],
                    "recommended_action": ai_result["recommended_action"],
                    "explanation": ai_result["explanation"],
                    "ai_provider": ai_result["ai_provider"],
                }

                _log(
                    dispute,
                    f"🤖 AI Analysis ({ai_result['ai_provider']}): "
                    f"Risk={ai_result['fraud_risk_score']}/100 ({ai_result['risk_level']}) | "
                    f"Action={ai_result['recommended_action']} | "
                    f"{ai_result['explanation']}",
                )

                action = ai_result["recommended_action"]

                # ── Force auto-decision: No manual review ──────────────
                # If AI tried to escalate, override to APPROVE_REFUND for debited
                # or REJECT_DISPUTE otherwise
                if action == "ESCALATE_TO_MANUAL_REVIEW":
                    if bank_status == "DEBITED":
                        action = "APPROVE_REFUND"
                        _log(dispute, "AI wanted manual review but auto-approving (debited funds).")
                    else:
                        action = "REJECT_DISPUTE"
                        _log(dispute, "AI wanted manual review but auto-rejecting (no debited funds).")

                if action == "APPROVE_REFUND" and bank_status == "DEBITED":
                    # AI says refund — proceed
                    _set_status(dispute, "REFUND_INITIATED")
                    db.session.commit()

                    try:
                        refund_resp = requests.post(
                            f"{base}/mock-bank/refund",
                            json={"txn_id": txn_id, "amount": txn.amount},
                            headers={"Authorization": f"Bearer {api_key}"},
                            timeout=10,
                        )
                        refund_data = refund_resp.json()
                        _log(dispute, f"Refund response: {refund_data.get('status', 'N/A')}")
                    except Exception as exc:
                        _log(dispute, f"Refund request failed: {exc}")
                        results["unresolved"] += 1
                        db.session.commit()
                        continue

                    txn.status = "REFUNDED"
                    _set_status(dispute, "RESOLVED")
                    results["refunds_initiated"] += 1
                    detail["resolution"] = "AI_APPROVED_REFUND"

                elif action == "REJECT_DISPUTE":
                    # AI says reject — mark as false alarm
                    if bank_status == "DEBITED" and merchant_status == "RECEIVED":
                        txn.status = "SUCCESS"
                    _log(dispute, "AI rejected dispute — no refund needed")
                    _set_status(dispute, "RESOLVED")
                    results["false_alarms"] += 1
                    detail["resolution"] = "AI_REJECTED"

                else:
                    detail["resolution"] = _apply_rules(
                        dispute, txn, bank_status, merchant_status,
                        base, api_key, results
                    )

            else:
                # ── AI unavailable — fall back to rules ───────────────
                results["rule_fallback"] += 1
                _log(dispute, "⚠️ AI unavailable — using rule-based engine")

                detail["resolution"] = _apply_rules(
                    dispute, txn, bank_status, merchant_status,
                    base, api_key, results
                )

            results["details"].append(detail)
            db.session.commit()

    return results


def _apply_rules(dispute, txn, bank_status, merchant_status, base, api_key, results):
    """
    Apply the rule-based Decision Matrix.
    Returns the resolution string for the detail record.
    """
    if bank_status == "DEBITED" and merchant_status == "NOT_RECEIVED":
        # ---- Condition A: Stuck Money → Refund ----
        _set_status(dispute, "REFUND_INITIATED")
        db.session.commit()

        try:
            refund_resp = requests.post(
                f"{base}/mock-bank/refund",
                json={"txn_id": dispute.txn_id, "amount": txn.amount},
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            refund_data = refund_resp.json()
            _log(dispute, f"Refund response: {refund_data.get('status', 'N/A')}")
        except Exception as exc:
            _log(dispute, f"Refund request failed: {exc}")
            results["unresolved"] += 1
            return "REFUND_FAILED"

        txn.status = "REFUNDED"
        _set_status(dispute, "RESOLVED")
        results["refunds_initiated"] += 1
        return "REFUND_INITIATED"

    elif bank_status == "DEBITED" and merchant_status == "RECEIVED":
        # ---- Condition B: False Alarm ----
        txn.status = "SUCCESS"
        _log(dispute, "Transaction updated to SUCCESS (false alarm)")
        _set_status(dispute, "RESOLVED")
        results["false_alarms"] += 1
        return "FALSE_ALARM"

    elif bank_status == "FAILED" and merchant_status == "NOT_RECEIVED":
        # ---- Condition C: Standard Failure ----
        txn.status = "FAILED"
        _log(dispute, "Transaction confirmed FAILED (standard failure)")
        _set_status(dispute, "RESOLVED")
        results["standard_failures"] += 1
        return "STANDARD_FAILURE"

    else:
        # ---- Unknown / edge case ----
        _log(
            dispute,
            f"No matching rule — Bank: {bank_status}, Merchant: {merchant_status}",
        )
        results["unresolved"] += 1
        return "UNRESOLVED"
