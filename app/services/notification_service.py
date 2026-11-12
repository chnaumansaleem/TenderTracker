import os
import smtplib
from email.message import EmailMessage
from datetime import datetime

from app.db import get_connection


def set_setting(key: str, value: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings(key, value, updated_at) VALUES (?, ?, datetime('now')) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
            (key, value),
        )
        conn.commit()


def get_setting(key: str, default: str = "") -> str:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def list_notifications():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
        return [dict(row) for row in rows]


def create_followup(tender_id, user_id, title, scheduled_for, notes=""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO followups (tender_id, user_id, title, scheduled_for, status, notes, created_at) VALUES (?, ?, ?, ?, 'pending', ?, datetime('now'))",
            (tender_id, user_id, title, scheduled_for, notes),
        )
        conn.commit()


def process_due_notifications():
    smtp_host = os.getenv("SMTP_HOST") or get_setting("smtp_host", "")
    smtp_port = int(os.getenv("SMTP_PORT") or get_setting("smtp_port", "587"))
    smtp_user = os.getenv("SMTP_USER") or get_setting("smtp_user", "")
    smtp_password = os.getenv("SMTP_PASSWORD") or get_setting("smtp_password", "")
    from_email = os.getenv("SMTP_FROM_EMAIL") or get_setting("smtp_from_email", smtp_user)

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT n.*, t.tender_title, u.email, u.full_name FROM notifications n LEFT JOIN tenders t ON n.tender_id = t.id LEFT JOIN users u ON n.recipient_user_id = u.id WHERE n.status = 'pending' ORDER BY n.trigger_date ASC"
        ).fetchall()

        for row in rows:
            try:
                if smtp_host and smtp_user and smtp_password:
                    msg = EmailMessage()
                    msg["Subject"] = f"Tender reminder: {row['tender_title']}"
                    msg["From"] = from_email
                    msg["To"] = row["email"]
                    msg.set_content(row["message"] or "This is a system-generated tender reminder.")
                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_password)
                        server.send_message(msg)
                    status = "sent"
                else:
                    status = "logged_only"
                conn.execute(
                    "UPDATE notifications SET status = ?, sent_at = datetime('now') WHERE id = ?",
                    (status, row["id"]),
                )
            except Exception:
                conn.execute(
                    "UPDATE notifications SET status = 'failed', sent_at = datetime('now') WHERE id = ?",
                    (row["id"],),
                )
        conn.commit()


def enqueue_notification(tender_id, recipient_user_id, notification_type, trigger_date, message):
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM notifications WHERE tender_id = ? AND recipient_user_id = ? AND notification_type = ? AND trigger_date = ? AND status != 'failed'",
            (tender_id, recipient_user_id, notification_type, trigger_date),
        ).fetchone()
        if exists:
            return
        conn.execute(
            "INSERT INTO notifications (tender_id, recipient_user_id, notification_type, trigger_date, status, message, created_at) VALUES (?, ?, ?, ?, 'pending', ?, datetime('now'))",
            (tender_id, recipient_user_id, notification_type, trigger_date, message),
        )
        conn.commit()
