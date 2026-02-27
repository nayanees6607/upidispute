"""
seed.py — Seed Data
--------------------
Populates the database with:
  - 1 user (Nayaneesh) with ₹25,000 balance
  - 6 merchants across categories
  - 5 historical transactions in various states for dispute testing
"""

from datetime import datetime, timezone

from models import Merchant, Transaction, User, db


def seed_db():
    """Insert seed data if the database is empty."""

    # Only seed once
    if User.query.first() is not None:
        return

    # ── Users ──────────────────────────────────────────────────────────────
    user = User(
        user_id="USER_A",
        name="Nayaneesh",
        phone="9876543210",
        upi_id="nayaneesh@upi",
        email="",  # Set your email here for email notifications
        balance=25000.00,
        pin="1234",
        avatar_color="#7209b7",
    )
    db.session.add(user)

    # ── Merchants ──────────────────────────────────────────────────────────
    merchants = [
        Merchant(
            merchant_id="MERCHANT_FLIPKART",
            name="Flipkart",
            category="Shopping",
            upi_id="flipkart@upi",
            icon="🛒",
            color="#F7D716",
        ),
        Merchant(
            merchant_id="MERCHANT_AMAZON",
            name="Amazon",
            category="Shopping",
            upi_id="amazon@upi",
            icon="📦",
            color="#FF9900",
        ),
        Merchant(
            merchant_id="MERCHANT_SWIGGY",
            name="Swiggy",
            category="Food",
            upi_id="swiggy@upi",
            icon="🍔",
            color="#FC8019",
        ),
        Merchant(
            merchant_id="MERCHANT_ZOMATO",
            name="Zomato",
            category="Food",
            upi_id="zomato@upi",
            icon="🍕",
            color="#E23744",
        ),
        Merchant(
            merchant_id="MERCHANT_JIO",
            name="Jio Recharge",
            category="Recharge",
            upi_id="jio@upi",
            icon="📱",
            color="#0A59A0",
        ),
        Merchant(
            merchant_id="MERCHANT_ELECTRICITY",
            name="Electricity Bill",
            category="Bills",
            upi_id="electricity@upi",
            icon="⚡",
            color="#00C853",
        ),
    ]
    db.session.add_all(merchants)
    db.session.flush()

    # ── Historical Transactions (for dispute testing) ──────────────────────
    seed_transactions = [
        Transaction(
            txn_id="TXN001",
            amount=1500.00,
            user_id="USER_A",
            merchant_id="MERCHANT_FLIPKART",
            merchant_name="Flipkart",
            timestamp=datetime(2026, 2, 27, 10, 0, 0, tzinfo=timezone.utc),
            status="DEBITED",
        ),
        Transaction(
            txn_id="TXN002",
            amount=250.00,
            user_id="USER_A",
            merchant_id="MERCHANT_SWIGGY",
            merchant_name="Swiggy",
            timestamp=datetime(2026, 2, 27, 10, 5, 0, tzinfo=timezone.utc),
            status="DEBITED",
        ),
        Transaction(
            txn_id="TXN003",
            amount=800.00,
            user_id="USER_A",
            merchant_id="MERCHANT_AMAZON",
            merchant_name="Amazon",
            timestamp=datetime(2026, 2, 27, 10, 10, 0, tzinfo=timezone.utc),
            status="FAILED",
        ),
        Transaction(
            txn_id="TXN004",
            amount=3200.00,
            user_id="USER_A",
            merchant_id="MERCHANT_FLIPKART",
            merchant_name="Flipkart",
            timestamp=datetime(2026, 2, 27, 10, 15, 0, tzinfo=timezone.utc),
            status="SUCCESS",
        ),
        Transaction(
            txn_id="TXN005",
            amount=999.99,
            user_id="USER_A",
            merchant_id="MERCHANT_JIO",
            merchant_name="Jio Recharge",
            timestamp=datetime(2026, 2, 27, 10, 20, 0, tzinfo=timezone.utc),
            status="DEBITED",
        ),
    ]
    db.session.add_all(seed_transactions)
    db.session.commit()
