"""
models.py — Database Models (Flask-SQLAlchemy)
----------------------------------------------
Defines six tables:
  • User         — registered UPI users with balances
  • Merchant     — merchants who accept UPI payments
  • Transaction  — records of UPI payments
  • Dispute      — dispute tickets raised against transactions
  • AuditLog     — immutable log of every state change for a dispute
  • Notification — in-app notifications for users
"""

from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(db.Model):
    """
    Represents a registered UPI user.
    balance tracks the current wallet/bank balance available for payments.
    """

    __tablename__ = "users"

    user_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    upi_id = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(200), nullable=True)  # For email notifications
    balance = db.Column(db.Float, nullable=False, default=0.0)
    pin = db.Column(db.String(10), nullable=False, default="1234")
    avatar_color = db.Column(db.String(7), nullable=False, default="#4361ee")

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "phone": self.phone,
            "upi_id": self.upi_id,
            "balance": self.balance,
            "avatar_color": self.avatar_color,
        }


# ---------------------------------------------------------------------------
# Merchant
# ---------------------------------------------------------------------------
class Merchant(db.Model):
    """
    Represents a merchant that accepts UPI payments.
    """

    __tablename__ = "merchants"

    merchant_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    upi_id = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(10), nullable=False, default="🏪")
    color = db.Column(db.String(7), nullable=False, default="#4361ee")

    def to_dict(self):
        return {
            "merchant_id": self.merchant_id,
            "name": self.name,
            "category": self.category,
            "upi_id": self.upi_id,
            "icon": self.icon,
            "color": self.color,
        }


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------
class Transaction(db.Model):
    """
    Represents a single UPI transaction.

    status can be one of: SUCCESS, FAILED, DEBITED, REFUNDED
      - DEBITED means money left the user's account but the final
        settlement is uncertain.
    """

    __tablename__ = "transactions"

    txn_id = db.Column(db.String(50), primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.String(50), db.ForeignKey("users.user_id"), nullable=False)
    merchant_id = db.Column(db.String(50), db.ForeignKey("merchants.merchant_id"), nullable=False)
    merchant_name = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    status = db.Column(db.String(20), nullable=False)  # SUCCESS | FAILED | DEBITED | REFUNDED

    # Relationship to disputes raised on this transaction
    disputes = db.relationship("Dispute", backref="transaction", lazy=True)

    def to_dict(self):
        return {
            "txn_id": self.txn_id,
            "amount": self.amount,
            "user_id": self.user_id,
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# Dispute
# ---------------------------------------------------------------------------
class Dispute(db.Model):
    """
    A dispute ticket linked to a transaction.

    current_status flow:
        PENDING → INVESTIGATING → REFUND_INITIATED (optional) → RESOLVED
    """

    __tablename__ = "disputes"

    dispute_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    txn_id = db.Column(
        db.String(50), db.ForeignKey("transactions.txn_id"), nullable=False
    )
    current_status = db.Column(
        db.String(30), nullable=False, default="PENDING"
    )  # PENDING | INVESTIGATING | REFUND_INITIATED | RESOLVED
    user_reason = db.Column(db.String(500), nullable=True)  # Reason provided by user
    admin_reason = db.Column(db.String(500), nullable=True)  # Reason provided by admin on resolution
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    resolved_at = db.Column(db.DateTime, nullable=True)

    # Relationship to audit log entries
    audit_logs = db.relationship("AuditLog", backref="dispute", lazy=True)

    def to_dict(self):
        return {
            "dispute_id": self.dispute_id,
            "txn_id": self.txn_id,
            "current_status": self.current_status,
            "user_reason": self.user_reason,
            "admin_reason": self.admin_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "audit_logs": [log.to_dict() for log in self.audit_logs],
        }


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------
class AuditLog(db.Model):
    """
    Immutable record of every state change that occurs on a dispute.
    Useful for compliance auditing and debugging the agent's decisions.
    """

    __tablename__ = "audit_logs"

    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dispute_id = db.Column(
        db.Integer, db.ForeignKey("disputes.dispute_id"), nullable=False
    )
    state_change = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "log_id": self.log_id,
            "dispute_id": self.dispute_id,
            "state_change": self.state_change,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
class Notification(db.Model):
    """
    In-app notifications for users.
    Tracks payment events, dispute updates, and AI resolutions.
    """

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.String(50), db.ForeignKey("users.user_id"), nullable=False
    )
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    notif_type = db.Column(
        db.String(30), nullable=False, default="INFO"
    )  # PAYMENT | DISPUTE | REFUND | INFO
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "notif_type": self.notif_type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
