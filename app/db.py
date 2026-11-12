import sqlite3
from pathlib import Path

from app.config import DB_PATH


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TEXT
);

CREATE TABLE IF NOT EXISTS tenders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id TEXT UNIQUE NOT NULL,
    tender_reference TEXT,
    tender_title TEXT NOT NULL,
    client_name TEXT,
    project_name TEXT,
    country TEXT,
    business_sector TEXT,
    tender_description TEXT,
    tender_category TEXT,
    tender_owner_id INTEGER,
    department TEXT,
    tender_source TEXT,
    estimated_contract_value REAL,
    currency TEXT DEFAULT 'USD',
    bid_open_date TEXT,
    submission_deadline TEXT,
    actual_submission_date TEXT,
    bid_closure_date TEXT,
    current_status TEXT NOT NULL DEFAULT 'Not Started',
    important_notes TEXT,
    next_follow_up_date TEXT,
    next_action TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tender_owner_id) REFERENCES users(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    category TEXT,
    uploaded_by INTEGER,
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tender_id) REFERENCES tenders(id),
    FOREIGN KEY(uploaded_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id INTEGER,
    recipient_user_id INTEGER,
    notification_type TEXT,
    trigger_date TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    message TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TEXT,
    FOREIGN KEY(tender_id) REFERENCES tenders(id),
    FOREIGN KEY(recipient_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id INTEGER,
    tender_reference TEXT,
    username TEXT NOT NULL,
    user_role TEXT NOT NULL,
    action_performed TEXT NOT NULL,
    field_changed TEXT,
    previous_value TEXT,
    updated_value TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS followups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id INTEGER,
    user_id INTEGER,
    title TEXT NOT NULL,
    scheduled_for TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(tender_id) REFERENCES tenders(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            ("notification_intervals", "14,7,3,1"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            ("copy_admin", "true"),
        )
        conn.commit()
