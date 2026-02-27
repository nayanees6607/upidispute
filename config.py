"""
config.py — Application Configuration
--------------------------------------
Centralises all configuration constants: database URI, secret keys,
and the hardcoded API key used by the Mock Bank refund endpoint.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Flask application configuration."""

    # ---------- Flask core ----------
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-dev-key")

    # ---------- SQLAlchemy ----------
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or f"sqlite:///{os.path.join(BASE_DIR, 'upi_disputes.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---------- Mock Bank API Key ----------
    # The refund endpoint requires this key in the Authorization header.
    MOCK_BANK_API_KEY = "MOCK-BANK-SECRET-KEY-12345"

    # ---------- Internal base URL ----------
    # Used by the agent to call mock endpoints on the same Flask server.
    BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

    # ---------- AI Service ----------
    # Set one (or both) of these to enable AI-powered dispute analysis.
    # Gemini is tried first (free tier), then OpenAI as fallback.
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
