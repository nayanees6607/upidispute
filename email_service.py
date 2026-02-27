"""
email_service.py — Email & In-App Notification Service
-------------------------------------------------------
Provides helpers to create in-app notifications and optionally send emails.
Email is sent via Gmail SMTP if SMTP_EMAIL and SMTP_PASSWORD env vars are set.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()

logger = logging.getLogger(__name__)

SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

def send_email(to_email: str, subject: str, body_html: str) -> bool:
    """Send an HTML email via Gmail SMTP."""
    if not to_email:
        logger.info("Email skipped — no recipient")
        return False

    if not SMTP_EMAIL or not SMTP_PASSWORD:
        logger.warning(f"Failed to send real email to {to_email}. SMTP_EMAIL or SMTP_PASSWORD is not configured.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"PaySafe UPI <{SMTP_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        logger.info(f"Email sent successfully to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def _build_email_html(title: str, message: str, notif_type: str) -> str:
    """Build a premium, styled HTML email body."""
    type_colors = {
        "PAYMENT": "#4361ee",
        "DISPUTE": "#f59e0b",
        "REFUND": "#10b981",
        "INFO": "#818cf8",
    }
    color = type_colors.get(notif_type, "#818cf8")
    type_icons = {
        "PAYMENT": "💳",
        "DISPUTE": "🛡️",
        "REFUND": "💰",
        "INFO": "✨",
    }
    icon = type_icons.get(notif_type, "📢")

    # Extract dynamic action buttons based on event type
    action_text = "Launch PaySafe"
    if notif_type == "PAYMENT":
        action_text = "View Transaction Receipt"
    elif notif_type == "DISPUTE":
        action_text = "Track Dispute Status"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #020617; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
        <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background-color: #020617; padding: 40px 20px;">
            <tr>
                <td align="center">
                    <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="max-width: 500px; background-color: #0f172a; border-radius: 20px; border: 1px solid #1e293b; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
                        <!-- Header -->
                        <tr>
                            <td style="padding: 30px; text-align: center; border-bottom: 1px solid #1e293b;">
                                <div style="display: inline-block; width: 40px; height: 40px; background: linear-gradient(135deg, #818CF8 0%, #4361EE 100%); border-radius: 12px; line-height: 40px; text-align: center; color: white; font-weight: bold; font-size: 20px; margin-bottom: 12px; box-shadow: 0 4px 10px rgba(67, 97, 238, 0.3);">◈</div>
                                <h1 style="margin: 0; font-size: 20px; font-weight: 700; color: #f8fafc; letter-spacing: -0.5px;">PaySafe <span style="background: rgba(129, 140, 248, 0.15); color: #818CF8; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-left: 4px; vertical-align: middle; text-transform: uppercase;">UPI</span></h1>
                            </td>
                        </tr>
                        
                        <!-- Hero Icon & Title -->
                        <tr>
                            <td style="padding: 30px 30px 10px 30px; text-align: center;">
                                <div style="display: inline-block; width: 64px; height: 64px; background: rgba(255,255,255,0.03); border-radius: 50%; line-height: 64px; font-size: 32px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 16px;">
                                    {icon}
                                </div>
                                <h2 style="margin: 0; font-size: 22px; font-weight: 600; color: #f8fafc;">{title}</h2>
                            </td>
                        </tr>
                        
                        <!-- Message Body -->
                        <tr>
                            <td style="padding: 10px 30px 30px 30px; text-align: center;">
                                <div style="background: rgba(255,255,255,0.02); border-radius: 12px; padding: 20px; margin-bottom: 24px; border: 1px solid rgba(255,255,255,0.02);">
                                    <p style="margin: 0; font-size: 15px; line-height: 1.6; color: #cbd5e1;">
                                        {message}
                                    </p>
                                </div>
                                
                                <a href="#" style="display: inline-block; background: {color}; color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 10px; font-weight: 600; font-size: 14px; letter-spacing: 0.5px;">
                                    {action_text}
                                </a>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 30px; background-color: #0b1120; text-align: center; border-top: 1px solid #1e293b;">
                                <p style="margin: 0; font-size: 12px; color: #64748b; line-height: 1.5;">
                                    This is an automated notification from PaySafe.<br>
                                    Please do not reply directly to this email.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def notify_user(user_id: str, title: str, message: str, notif_type: str = "INFO", app=None):
    """
    Create an in-app notification and optionally send an email.
    Must be called within a Flask app context.
    """
    from models import db, Notification, User

    # Create in-app notification
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notif_type=notif_type,
    )
    db.session.add(notif)
    db.session.commit()

    # Send email if configured
    user = db.session.get(User, user_id)
    if user and user.email:
        html = _build_email_html(title, message, notif_type)
        send_email(user.email, f"PaySafe: {title}", html)

    return notif
