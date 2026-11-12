import os
from datetime import datetime, timezone

from app.config import get_setting
from app.db import get_connection
from app.security import hash_password, verify_password


DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME") or get_setting(
    "app", "admin_username", "admin"
)
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or get_setting(
    "app", "admin_password", "Admin@123"
)


def ensure_default_admin():
    with get_connection() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (DEFAULT_ADMIN_USERNAME,),
        ).fetchone()
        if user is None:
            conn.execute(
                "INSERT INTO users (username, password_hash, full_name, email, role, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    DEFAULT_ADMIN_USERNAME,
                    hash_password(DEFAULT_ADMIN_PASSWORD),
                    "System Administrator",
                    "admin@example.com",
                    "admin",
                    1,
                ),
            )
            conn.commit()


def authenticate_user(username: str, password: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,),
        ).fetchone()
        if row is None:
            return None
        if not verify_password(password, row["password_hash"]):
            return None
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), row["id"]),
        )
        conn.commit()
        return dict(row)


def list_users():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_user_by_id(user_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def create_user(full_name: str, username: str, password: str, email: str, role: str = "user"):
    with get_connection() as conn:
        existing = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            raise ValueError("Username already exists")
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, full_name, email, role, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (username, hash_password(password), full_name, email, role, 1),
        )
        conn.commit()
        return cursor.lastrowid


def update_user(user_id: int, **kwargs):
    allowed_fields = {"full_name", "email", "role", "is_active"}
    payload = []
    for key, value in kwargs.items():
        if key in allowed_fields:
            payload.append((key, value))
    if not payload:
        return False
    with get_connection() as conn:
        for field, value in payload:
            conn.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
        conn.commit()
        return True


def reset_password(user_id: int, new_password: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id),
        )
        conn.commit()
        return True
