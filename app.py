"""
app.py — Flask Application (Entry Point)
-----------------------------------------
Registers all routes:

  Mock Ecosystem
  ──────────────
  GET  /mock-bank/verify/<txn_id>      → Bank's view of the transaction
  POST /mock-bank/refund               → Refund endpoint (API-key protected)
  GET  /mock-merchant/verify/<txn_id>  → Merchant's view of the order

  Payment API
  ───────────
  GET  /api/user/<user_id>             → User profile + balance
  GET  /api/merchants                  → List all merchants
  POST /api/pay                        → Process a UPI payment
  GET  /api/transactions/<user_id>     → Transaction history

  Admin / Dispute API
  ────────────────────
  POST /api/disputes/raise             → Create a new PENDING dispute
  GET  /api/disputes/status            → List all disputes + audit logs
  POST /api/agent/run                  → Trigger the resolution agent

  Frontend
  ────────
  GET /                                → Serves the SPA (index.html)
"""

import random
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory

from agent import run_agent
from config import Config
from email_service import notify_user
from models import AuditLog, Dispute, Merchant, Notification, Transaction, User, db
from seed import seed_db

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config.from_object(Config)

db.init_app(app)

# ---------------------------------------------------------------------------
# Merchant order mapping (simulated merchant database)
# ---------------------------------------------------------------------------
# Tracks whether the merchant *actually* received the payment.
# For seed transactions and dynamically updated on new payments.
MERCHANT_ORDER_STATUS = {
    "TXN001": "NOT_RECEIVED",
    "TXN002": "RECEIVED",
    "TXN003": "NOT_RECEIVED",
    "TXN004": "RECEIVED",
    "TXN005": "NOT_RECEIVED",
}


# ═══════════════════════════════════════════════════════════════════════════
# FRONTEND — Serve SPA
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """GET / — Serves the frontend single-page application."""
    return send_from_directory("static", "index.html")

@app.route("/admin")
def admin_page():
    """GET /admin — Serves the dedicated Admin Dashboard application."""
    return send_from_directory("static", "admin.html")


# ═══════════════════════════════════════════════════════════════════════════
# AUTHENTICATION API ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/auth/register", methods=["POST"])
def register_user():
    """POST /api/auth/register — Create a new user account."""
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    phone = data.get("phone")
    email = data.get("email")
    balance = data.get("balance", 0.0)
    pin = data.get("pin")

    if not all([name, phone, pin]):
        return jsonify({"error": "Name, phone, and PIN are required"}), 400

    if len(str(pin)) < 4:
        return jsonify({"error": "PIN must be at least 4 digits"}), 400

    # Ensure unique phone
    existing_user = User.query.filter_by(phone=phone).first()
    if existing_user:
        return jsonify({"error": "Account with this phone number already exists"}), 400

    try:
        balance = float(balance)
        if balance < 0:
            raise ValueError
    except ValueError:
        return jsonify({"error": "Invalid opening balance"}), 400

    # Generate user IDs
    user_id = f"USR{uuid.uuid4().hex[:8].upper()}"
    upi_id = f"{phone}@paysafe"
    
    # Random vibrant avatar color
    colors = ["#4361ee", "#7209b7", "#f72585", "#3a0ca3", "#ff6d00", "#00b4d8", "#2a9d8f"]
    avatar_color = random.choice(colors)

    new_user = User(
        user_id=user_id,
        name=name,
        phone=phone,
        email=email,
        upi_id=upi_id,
        balance=balance,
        pin=str(pin),
        avatar_color=avatar_color
    )

    db.session.add(new_user)
    db.session.commit()

    # Trigger Email & In-App notification for successful registration
    notify_user(
        user_id=new_user.user_id,
        title="🎉 Welcome to PaySafe UPI!",
        message=f"Hi {new_user.name}, your account is active with an opening balance of ₹{new_user.balance:,.2f}.",
        notif_type="INFO"
    )

    return jsonify({"message": "Account created successfully", "user": new_user.to_dict()}), 201


@app.route("/api/auth/login", methods=["POST"])
def login_user():
    """POST /api/auth/login — Authenticate user via phone and PIN."""
    data = request.get_json(silent=True) or {}
    phone = data.get("phone")
    pin = data.get("pin")

    if not all([phone, pin]):
        return jsonify({"error": "Phone and PIN are required"}), 400

    user = User.query.filter_by(phone=phone, pin=str(pin)).first()
    
    if not user:
        return jsonify({"error": "Invalid phone number or PIN"}), 401
        
    return jsonify({"message": "Login successful", "user": user.to_dict()})


# ═══════════════════════════════════════════════════════════════════════════
# PAYMENT API ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/user/<user_id>", methods=["GET"])
def get_user(user_id):
    """GET /api/user/<user_id> — User profile with balance."""
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict())


@app.route("/api/merchants", methods=["GET"])
def get_merchants():
    """GET /api/merchants — List all registered merchants."""
    merchants = Merchant.query.all()
    return jsonify([m.to_dict() for m in merchants])


@app.route("/api/pay", methods=["POST"])
def make_payment():
    """
    POST /api/pay
    Body: {"user_id": "...", "merchant_id": "...", "amount": ..., "pin": "..."}

    Simulates a UPI payment. To make the demo realistic:
    - 60% chance → SUCCESS
    - 25% chance → DEBITED (money stuck — merchant doesn't receive)
    - 15% chance → FAILED
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    merchant_id = data.get("merchant_id")
    amount = data.get("amount")
    pin = data.get("pin")

    # ── Validation ─────────────────────────────────────────────────────────
    if not all([user_id, merchant_id, amount, pin]):
        return jsonify({"error": "user_id, merchant_id, amount, and pin are required"}), 400

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be positive"}), 400

    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    merchant = db.session.get(Merchant, merchant_id)
    if merchant is None:
        return jsonify({"error": "Merchant not found"}), 404

    # ── PIN Check ──────────────────────────────────────────────────────────
    if pin != user.pin:
        return jsonify({"error": "Incorrect UPI PIN"}), 401

    # ── Balance Check ──────────────────────────────────────────────────────
    if user.balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    # ── Simulate transaction outcome ───────────────────────────────────────
    txn_id = f"TXN{uuid.uuid4().hex[:8].upper()}"
    roll = random.random()

    if roll < 0.60:
        status = "SUCCESS"
        merchant_received = "RECEIVED"
    elif roll < 0.85:
        status = "DEBITED"
        merchant_received = "NOT_RECEIVED"  # Money stuck!
    else:
        status = "FAILED"
        merchant_received = "NOT_RECEIVED"

    # Deduct balance only if money actually left the account
    if status in ("SUCCESS", "DEBITED"):
        user.balance -= amount

    # Track merchant-side status for the dispute agent
    MERCHANT_ORDER_STATUS[txn_id] = merchant_received

    # ── Create transaction record ──────────────────────────────────────────
    txn = Transaction(
        txn_id=txn_id,
        amount=amount,
        user_id=user_id,
        merchant_id=merchant_id,
        merchant_name=merchant.name,
        timestamp=datetime.now(timezone.utc),
        status=status,
    )
    db.session.add(txn)
    db.session.commit()

    # Send notification
    status_messages = {
        "SUCCESS": f"Payment of ₹{amount:,.2f} to {merchant.name} was successful.",
        "DEBITED": f"Payment of ₹{amount:,.2f} to {merchant.name} — money debited but merchant didn't receive. You can raise a dispute.",
        "FAILED": f"Payment of ₹{amount:,.2f} to {merchant.name} failed. No money was deducted.",
    }
    status_titles = {
        "SUCCESS": "✅ Payment Successful",
        "DEBITED": "⚠️ Payment Stuck",
        "FAILED": "❌ Payment Failed",
    }
    notify_user(
        user_id=user_id,
        title=status_titles.get(status, "Payment Update"),
        message=status_messages.get(status, f"Payment of ₹{amount:,.2f} processed."),
        notif_type="PAYMENT",
    )

    return jsonify({
        "message": "Payment processed",
        "transaction": txn.to_dict(),
        "new_balance": user.balance,
    }), 201


@app.route("/api/transactions/<user_id>", methods=["GET"])
def get_transactions(user_id):
    """GET /api/transactions/<user_id> — User's transaction history (newest first)."""
    txns = (
        Transaction.query
        .filter_by(user_id=user_id)
        .order_by(Transaction.timestamp.desc())
        .all()
    )
    return jsonify([t.to_dict() for t in txns])


# ═══════════════════════════════════════════════════════════════════════════
# MOCK ECOSYSTEM ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/mock-bank/verify/<txn_id>", methods=["GET"])
def mock_bank_verify(txn_id):
    """GET /mock-bank/verify/<txn_id> — Bank's view of the transaction status."""
    txn = db.session.get(Transaction, txn_id)
    if txn is None:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify({
        "txn_id": txn.txn_id,
        "bank_status": txn.status,
        "amount": txn.amount,
    })


@app.route("/mock-bank/refund", methods=["POST"])
def mock_bank_refund():
    """
    POST /mock-bank/refund
    Headers: Authorization: Bearer <MOCK_BANK_API_KEY>
    Body: {"txn_id": "...", "amount": ...}
    """
    auth_header = request.headers.get("Authorization", "")
    expected = f"Bearer {Config.MOCK_BANK_API_KEY}"
    if auth_header != expected:
        return jsonify({"error": "Unauthorized — invalid or missing API key"}), 401

    data = request.get_json(silent=True) or {}
    txn_id = data.get("txn_id")
    amount = data.get("amount")

    if not txn_id or amount is None:
        return jsonify({"error": "txn_id and amount are required"}), 400

    # Refund the user's balance
    txn = db.session.get(Transaction, txn_id)
    if txn:
        user = db.session.get(User, txn.user_id)
        if user:
            user.balance += float(amount)
            db.session.commit()

    return jsonify({
        "txn_id": txn_id,
        "amount": amount,
        "status": "REFUND_SUCCESS",
    })


@app.route("/mock-merchant/verify/<txn_id>", methods=["GET"])
def mock_merchant_verify(txn_id):
    """GET /mock-merchant/verify/<txn_id> — Merchant's view of the order."""
    status = MERCHANT_ORDER_STATUS.get(txn_id, "NOT_RECEIVED")
    return jsonify({
        "txn_id": txn_id,
        "merchant_status": status,
    })


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN / DISPUTE API ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/disputes/raise", methods=["POST"])
def raise_dispute():
    """POST /api/disputes/raise — Create a new PENDING dispute."""
    data = request.get_json(silent=True) or {}
    txn_id = data.get("txn_id")
    user_reason = data.get("reason", "")

    if not txn_id:
        return jsonify({"error": "txn_id is required"}), 400

    txn = db.session.get(Transaction, txn_id)
    if txn is None:
        return jsonify({"error": f"Transaction '{txn_id}' not found"}), 404

    existing = Dispute.query.filter_by(txn_id=txn_id, current_status="PENDING").first()
    if existing:
        return jsonify({
            "message": "A PENDING dispute already exists for this transaction",
            "dispute": existing.to_dict(),
        }), 409

    dispute = Dispute(txn_id=txn_id, current_status="PENDING", user_reason=user_reason)
    db.session.add(dispute)
    db.session.flush()

    log = AuditLog(
        dispute_id=dispute.dispute_id,
        state_change=f"Dispute created — status set to PENDING. Reason: {user_reason or 'Not provided'}",
    )
    db.session.add(log)
    db.session.commit()

    # Auto-trigger AI resolution agent
    try:
        resolution_result = run_agent(app)
    except Exception:
        resolution_result = None

    # Re-fetch dispute after agent may have resolved it
    db.session.refresh(dispute)

    # Notify user about dispute status
    txn = db.session.get(Transaction, txn_id)
    resolved_status = dispute.current_status
    if resolved_status == "RESOLVED":
        notify_user(
            user_id=txn.user_id if txn else "USER_A",
            title="🛡️ Dispute Auto-Resolved",
            message=f"Your dispute for TXN {txn_id} (₹{txn.amount:,.2f}) has been auto-resolved by our AI system.",
            notif_type="DISPUTE",
        )
    else:
        notify_user(
            user_id=txn.user_id if txn else "USER_A",
            title="🛡️ Dispute Filed",
            message=f"Your dispute for TXN {txn_id} has been filed and is being processed. Status: {resolved_status}",
            notif_type="DISPUTE",
        )

    return jsonify({
        "message": "Dispute raised and processed by AI",
        "dispute": dispute.to_dict(),
        "resolution": resolution_result,
    }), 201


# ═══════════════════════════════════════════════════════════════════════════
# NOTIFICATION API
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/notifications/<user_id>", methods=["GET"])
def get_notifications(user_id):
    """GET /api/notifications/<user_id> — Fetch all notifications (newest first)."""
    notifs = (
        Notification.query
        .filter_by(user_id=user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify({
        "notifications": [n.to_dict() for n in notifs],
        "unread_count": unread_count,
    })


@app.route("/api/notifications/<user_id>/read-all", methods=["POST"])
def mark_all_read(user_id):
    """POST /api/notifications/<user_id>/read-all — Mark all notifications as read."""
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"success": True})

@app.route("/api/disputes/status", methods=["GET"])
def disputes_status():
    """GET /api/disputes/status — All disputes with transaction info + audit trail."""
    disputes = Dispute.query.order_by(Dispute.created_at.desc()).all()
    result = []
    for d in disputes:
        txn = db.session.get(Transaction, d.txn_id)
        result.append({
            **d.to_dict(),
            "transaction": txn.to_dict() if txn else None,
        })
    return jsonify(result)


@app.route("/api/agent/run", methods=["POST"])
def trigger_agent():
    """POST /api/agent/run — Trigger the dispute resolution agent."""
    summary = run_agent(app)
    return jsonify(summary)


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN API (Custom Dashboard)
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/admin/disputes", methods=["GET"])
def get_admin_disputes():
    """Fetch all disputes with detailed user and transaction info for the Admin UI."""
    disputes = Dispute.query.order_by(Dispute.created_at.desc()).all()
    result = []
    for d in disputes:
        txn = db.session.get(Transaction, d.txn_id)
        user = None
        if txn:
            user_rec = db.session.get(User, txn.user_id)
            if user_rec:
                user = user_rec.to_dict()
        
        result.append({
            **d.to_dict(),
            "transaction": txn.to_dict() if txn else None,
            "user": user
        })
    return jsonify(result)

@app.route("/api/admin/disputes/<int:dispute_id>/resolve", methods=["POST"])
def admin_resolve_dispute(dispute_id):
    """Manually resolve a dispute (Approve/Reject). Credits user balance on approve."""
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    admin_reason = data.get("reason", "")
    
    if action not in ["APPROVE_REFUND", "REJECT"]:
        return jsonify({"error": "Invalid action. Must be APPROVE_REFUND or REJECT"}), 400
        
    dispute = db.session.get(Dispute, dispute_id)
    if not dispute:
        return jsonify({"error": "Dispute not found"}), 404
        
    if dispute.current_status == "RESOLVED":
        return jsonify({"error": "Dispute is already resolved"}), 400
        
    txn = db.session.get(Transaction, dispute.txn_id)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404
        
    user = db.session.get(User, txn.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Perform action
    if action == "APPROVE_REFUND":
        user.balance += txn.amount # Refund the user
        resolution = "ADMIN_APPROVED_REFUND"
    else:
        resolution = "ADMIN_REJECTED"

    dispute.current_status = "RESOLVED"
    dispute.resolved_at = datetime.now(timezone.utc)
    dispute.admin_reason = admin_reason
    
    # Create audit log
    log = AuditLog(
        dispute_id=dispute.dispute_id,
        state_change=f"RESOLVED — {resolution}. Reason: {admin_reason or 'Not provided'}"
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"success": True, "resolution": resolution, "new_balance": user.balance})

@app.route("/api/admin/reset", methods=["POST"])
def admin_reset_db():
    """Wipe transactions and disputes, restore initial seed balance for testing."""
    db.session.query(AuditLog).delete()
    db.session.query(Dispute).delete()
    db.session.query(Transaction).delete()
    
    # Restore Nayaneesh balance
    user = db.session.get(User, "USER_A")
    if user:
        user.balance = 25000.0
        
    db.session.commit()
    return jsonify({"success": True, "message": "Database reset to initial state."})

@app.route("/api/admin/transactions", methods=["GET"])
def get_admin_transactions():
    """Fetch all transactions for the Admin UI."""
    txns = Transaction.query.order_by(Transaction.timestamp.desc()).all()
    result = []
    for txn in txns:
        user = db.session.get(User, txn.user_id)
        result.append({
            **txn.to_dict(),
            "user": user.to_dict() if user else None
        })
    return jsonify(result)

@app.route("/api/admin/transactions/<txn_id>/status", methods=["POST"])
def update_transaction_status(txn_id):
    """Update a transaction's status and automatically adjust user balances if needed."""
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    
    if not new_status or new_status not in ["SUCCESS", "PENDING", "DEBITED", "FAILED", "REFUNDED"]:
        return jsonify({"error": "Invalid status"}), 400

    txn = db.session.get(Transaction, txn_id)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404

    old_status = txn.status
    if old_status == new_status:
        return jsonify({"message": "Status is unchanged", "transaction": txn.to_dict()}), 200

    user = db.session.get(User, txn.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Balance adjustment logic based on status transition
    # Money leaves account ONLY on SUCCESS or DEBITED.
    
    was_debited = old_status in ["SUCCESS", "DEBITED"]
    is_debited = new_status in ["SUCCESS", "DEBITED"]
    
    if was_debited and not is_debited:
        # e.g., DEBITED -> FAILED or REFUNDED = Refund user
        user.balance += txn.amount
    elif not was_debited and is_debited:
        # e.g., FAILED -> SUCCESS or DEBITED = Charge user
        if user.balance < txn.amount:
            return jsonify({"error": f"Insufficient user balance (₹{user.balance}) for this change"}), 400
        user.balance -= txn.amount

    txn.status = new_status
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Status updated from {old_status} to {new_status}",
        "transaction": txn.to_dict(),
        "new_balance": user.balance
    })

# ═══════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_db()

    # Changed port to 5001 because macOS AirPlay Receiver occupies 5000
    app.run(port=5001, debug=True)
