"""
ai_service.py — AI-Powered UPI Dispute Resolution Agent
-------------------------------------------------------
Integrates with:
  1. Groq (free tier, fast — tried first)
  2. Google Gemini (free tier)
  3. OpenAI (paid)

Output format (per user spec):
{
    "fraud_risk_score": 0-100,
    "risk_level": "LOW | MEDIUM | HIGH",
    "recommended_action": "APPROVE_REFUND | REJECT_DISPUTE | ESCALATE_TO_MANUAL_REVIEW",
    "explanation": "short explanation"
}

Falls back gracefully to None if AI is unavailable,
allowing the caller to use the rule-based engine instead.
"""

import json
import logging
import os

import requests as http_requests

logger = logging.getLogger(__name__)

# ── API Keys ─────────────────────────────────────────────────────────────

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


# ═════════════════════════════════════════════════════════════════════════
# PROMPT
# ═════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are a FULLY AUTONOMOUS AI-powered UPI Dispute Resolution Agent working for a digital payment platform.

You MUST make a final decision on every dispute. You CANNOT escalate to manual review.
Your ONLY two actions are: APPROVE_REFUND or REJECT_DISPUTE.

You will receive structured transaction data and (when available) history of past resolutions. Learn from those patterns to make better decisions.

Your tasks:
1. Verify if the transaction appears valid.
2. Calculate a Fraud Risk Score strictly using the point system below.
3. Classify risk as LOW, MEDIUM, or HIGH based on the final score.
4. Recommend APPROVE_REFUND or REJECT_DISPUTE based on the rules and patterns.
5. Provide a short explanation detailing the points added and the final decision.

---
🔴 SCORING ALGORITHM (Start at Base Score: 10) 🔴
You MUST calculate the score by adding the following points if the condition is true:

+40 points: Duplicate Transaction is YES
+30 points: User has > 2 previous disputes
+20 points: User has 1-2 previous disputes
+30 points: Amount is completely unusually high (> 10,000)
+15 points: Amount is moderately high (> 2,000)
+25 points: Time Since Transaction is less than 5 minutes (quick dispute)
+20 points: Status is SUCCESS, but user claims money debited & merchant not credited.
+0  points: Status is PENDING/DEBITED and merchant NOT credited (standard network issue).

Maximum score is 100. Minimum score is 0.
---
🟡 RISK LEVELS & ACTIONS 🟡
- Score 0-35 (LOW RISK):
  -> APPROVE_REFUND if merchant not credited.
  -> REJECT_DISPUTE if merchant confirmed received.
- Score 36-65 (MEDIUM RISK):
  -> APPROVE_REFUND if clear network error (DEBITED/FAILED + merchant NOT credited).
  -> REJECT_DISPUTE if Status=SUCCESS and Merchant Credited=YES.
- Score 66-100 (HIGH RISK):
  -> REJECT_DISPUTE if clearly fraudulent or a false alarm.
  -> APPROVE_REFUND only if bank confirms funds were debited and merchant never received money.

IMPORTANT: You MUST choose APPROVE_REFUND or REJECT_DISPUTE. Never escalate.

Respond strictly in JSON format:

{
  "fraud_risk_score": number,
  "risk_level": "LOW | MEDIUM | HIGH",
  "recommended_action": "APPROVE_REFUND | REJECT_DISPUTE",
  "explanation": "Calculation: Base(10) + [List of points added] = Total. Decision: [Reason action was chosen]"
}"""


def _build_transaction_data(
    txn_id, amount, bank_status, merchant_status, user_id,
    time_since="unknown", duplicate_count=0, previous_disputes=0,
    dispute_reason="User raised a dispute",
):
    """Build structured transaction data for the AI prompt."""
    merchant_credited = "YES" if merchant_status == "RECEIVED" else "NO"
    status_map = {"DEBITED": "PENDING", "SUCCESS": "SUCCESS", "FAILED": "FAILED", "REFUNDED": "REFUNDED"}
    display_status = status_map.get(bank_status, bank_status)

    return f"""Here is the transaction data:
Transaction ID: {txn_id}
Amount: {amount}
Status: {display_status}
Merchant Credited: {merchant_credited}
Time Since Transaction: {time_since}
Duplicate Transaction: {"YES" if duplicate_count > 0 else "NO"}
User Previous Disputes: {previous_disputes}
Dispute Reason: {dispute_reason}"""


def _strip_fences(text):
    """Remove markdown code fences from AI response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return text


# ═════════════════════════════════════════════════════════════════════════
# PROVIDERS
# ═════════════════════════════════════════════════════════════════════════

def _analyze_with_groq(transaction_data):
    """Call Groq API (free, fast, OpenAI-compatible)."""
    try:
        resp = http_requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": transaction_data},
                ],
                "temperature": 0.1,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        resp.raise_for_status()

        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = _strip_fences(raw)
        logger.info(f"Groq response: {raw}")
        return json.loads(raw)

    except json.JSONDecodeError as e:
        logger.error(f"Groq JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return None


def _analyze_with_gemini(transaction_data):
    """Call Google Gemini API."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash", system_instruction=SYSTEM_PROMPT)
        response = model.generate_content(
            transaction_data,
            generation_config=genai.types.GenerationConfig(temperature=0.1, max_output_tokens=300),
        )
        raw = _strip_fences(response.text)
        logger.info(f"Gemini response: {raw}")
        return json.loads(raw)
    except ImportError:
        logger.warning("google-generativeai package not installed.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Gemini JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None


def _analyze_with_openai(transaction_data):
    """Call OpenAI API."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=15)
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transaction_data},
            ],
            temperature=0.1, max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        logger.info(f"OpenAI response: {raw}")
        return json.loads(raw)
    except ImportError:
        logger.warning("openai package not installed.")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"OpenAI JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return None


# ═════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═════════════════════════════════════════════════════════════════════════

def analyze_dispute(
    txn_id, amount, bank_status, merchant_status, user_id,
    time_since="unknown", duplicate_count=0, previous_disputes=0,
    dispute_reason="Money debited but merchant did not receive",
    resolution_history="",
):
    """
    Analyze a dispute using AI. Tries: Groq (free) → Gemini → OpenAI.

    Returns dict with fraud_risk_score, risk_level, recommended_action,
    explanation, ai_provider — or None if all fail.
    """
    transaction_data = _build_transaction_data(
        txn_id=txn_id, amount=amount, bank_status=bank_status,
        merchant_status=merchant_status, user_id=user_id,
        time_since=time_since, duplicate_count=duplicate_count,
        previous_disputes=previous_disputes, dispute_reason=dispute_reason,
    )

    # Append resolution history for pattern learning
    if resolution_history:
        transaction_data += f"\n\n--- PREVIOUS RESOLUTION PATTERNS (Learn from these) ---\n{resolution_history}"

    result, provider = None, None

    # 1. Groq (free, fast)
    if GROQ_API_KEY and not GROQ_API_KEY.startswith("your-"):
        logger.info("🤖 Attempting AI analysis with Groq (free)...")
        result = _analyze_with_groq(transaction_data)
        if result:
            provider = "groq"

    # 2. Gemini (free tier)
    if result is None and GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your-"):
        logger.info("🤖 Attempting AI analysis with Gemini...")
        result = _analyze_with_gemini(transaction_data)
        if result:
            provider = "gemini"

    # 3. OpenAI (paid)
    if result is None and OPENAI_API_KEY and not OPENAI_API_KEY.startswith("sk-your"):
        logger.info("🤖 Attempting AI analysis with OpenAI...")
        result = _analyze_with_openai(transaction_data)
        if result:
            provider = "openai"

    if result is None:
        logger.warning("⚠️  AI analysis unavailable — will use rule-based engine.")
        return None

    # Validate and normalize
    try:
        fraud_risk_score = max(0, min(100, int(result.get("fraud_risk_score", 50))))
        risk_level = str(result.get("risk_level", "MEDIUM")).upper()
        if risk_level not in ("LOW", "MEDIUM", "HIGH"):
            risk_level = "MEDIUM"
        recommended_action = str(result.get("recommended_action", "APPROVE_REFUND")).upper()
        if recommended_action not in ("APPROVE_REFUND", "REJECT_DISPUTE"):
            recommended_action = "APPROVE_REFUND"

        return {
            "fraud_risk_score": fraud_risk_score,
            "risk_level": risk_level,
            "recommended_action": recommended_action,
            "explanation": str(result.get("explanation", "No explanation provided.")),
            "ai_provider": provider,
        }
    except (ValueError, TypeError) as e:
        logger.error(f"AI result validation error: {e}")
        return None
