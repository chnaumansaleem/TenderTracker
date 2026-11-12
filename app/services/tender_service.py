import sqlite3
from datetime import datetime, timezone

from app.db import get_connection


def _row_to_dict(row):
    return dict(row) if row else None


def generate_tender_id():
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0] + 1
    return f"TND-{today}-{count:04d}"


def list_tenders(user=None, is_admin=False, filters=None):
    query = """
        SELECT
            t.*,
            o.full_name as owner_name,
            c.full_name as created_by_name
        FROM tenders t
        LEFT JOIN users o ON t.tender_owner_id = o.id
        LEFT JOIN users c ON t.created_by = c.id
        WHERE 1=1
    """
    params = []
    if user and not is_admin:
        query += " AND (t.tender_owner_id = ? OR t.created_by = ?)"
        params.extend([user["id"], user["id"]])

    if filters:
        if filters.get("status"):
            query += " AND t.current_status = ?"
            params.append(filters["status"])
        if filters.get("country"):
            query += " AND t.country = ?"
            params.append(filters["country"])
        if filters.get("business_sector"):
            query += " AND t.business_sector = ?"
            params.append(filters["business_sector"])
        if filters.get("assigned_user"):
            query += " AND t.tender_owner_id = ?"
            params.append(filters["assigned_user"])
        if filters.get("search"):
            keyword = f"%{filters['search']}%"
            query += " AND (LOWER(t.tender_id) LIKE LOWER(?) OR LOWER(t.tender_reference) LIKE LOWER(?) OR LOWER(t.tender_title) LIKE LOWER(?) OR LOWER(t.client_name) LIKE LOWER(?) OR LOWER(t.project_name) LIKE LOWER(?) OR LOWER(t.country) LIKE LOWER(?))"
            params.extend([keyword] * 6)

    query += " ORDER BY t.submission_deadline ASC, t.created_at DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(row) for row in rows]


def create_tender(data, created_by_user_id):
    required = [
        "tender_title",
        "client_name",
        "project_name",
        "country",
        "tender_category",
        "current_status",
    ]
    for field in required:
        if not data.get(field):
            raise ValueError(f"Missing required field: {field}")

    inserted = {
        "tender_id": generate_tender_id(),
        "tender_reference": data.get("tender_reference") or "",
        "tender_title": data.get("tender_title"),
        "client_name": data.get("client_name"),
        "project_name": data.get("project_name"),
        "country": data.get("country"),
        "business_sector": data.get("business_sector") or "",
        "tender_description": data.get("tender_description") or "",
        "tender_category": data.get("tender_category"),
        "tender_owner_id": data.get("tender_owner_id"),
        "department": data.get("department") or "",
        "tender_source": data.get("tender_source") or "",
        "estimated_contract_value": data.get("estimated_contract_value") or 0,
        "currency": data.get("currency") or "USD",
        "bid_open_date": data.get("bid_open_date") or "",
        "submission_deadline": data.get("submission_deadline") or "",
        "actual_submission_date": data.get("actual_submission_date") or "",
        "bid_closure_date": data.get("bid_closure_date") or "",
        "current_status": data.get("current_status") or "Not Started",
        "important_notes": data.get("important_notes") or "",
        "next_follow_up_date": data.get("next_follow_up_date") or "",
        "next_action": data.get("next_action") or "",
        "created_by": created_by_user_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tenders (
                tender_id, tender_reference, tender_title, client_name, project_name, country,
                business_sector, tender_description, tender_category, tender_owner_id, department,
                tender_source, estimated_contract_value, currency, bid_open_date, submission_deadline,
                actual_submission_date, bid_closure_date, current_status, important_notes,
                next_follow_up_date, next_action, created_by, created_at, updated_at
            ) VALUES (
                :tender_id, :tender_reference, :tender_title, :client_name, :project_name, :country,
                :business_sector, :tender_description, :tender_category, :tender_owner_id, :department,
                :tender_source, :estimated_contract_value, :currency, :bid_open_date, :submission_deadline,
                :actual_submission_date, :bid_closure_date, :current_status, :important_notes,
                :next_follow_up_date, :next_action, :created_by, :created_at, :updated_at
            )
            """,
            inserted,
        )
        tender_id = cursor.lastrowid
        record_audit(
            tender_id=tender_id,
            tender_reference=inserted["tender_reference"],
            username="system",
            role="system",
            action_performed="create",
            field_changed="record",
            previous_value="",
            updated_value="Created tender record",
        )
        conn.commit()
        return tender_id


def get_tender_by_id(tender_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT t.*, o.full_name as owner_name FROM tenders t LEFT JOIN users o ON t.tender_owner_id = o.id WHERE t.id = ?",
            (tender_id,),
        ).fetchone()
        return _row_to_dict(row)


def update_tender(tender_id, changes, actor_user):
    with get_connection() as conn:
        current = conn.execute("SELECT * FROM tenders WHERE id = ?", (tender_id,)).fetchone()
        if not current:
            return False
        for key, value in changes.items():
            if key in {"id", "created_at", "created_by", "tender_id"}:
                continue
            if key == "updated_at":
                continue
            old_value = current[key]
            if old_value != value:
                conn.execute(
                    f"UPDATE tenders SET {key} = ? WHERE id = ?",
                    (value, tender_id),
                )
                record_audit(
                    tender_id=tender_id,
                    tender_reference=current["tender_reference"],
                    username=actor_user["username"],
                    role=actor_user["role"],
                    action_performed="update",
                    field_changed=key,
                    previous_value=str(old_value),
                    updated_value=str(value),
                )
        conn.execute(
            "UPDATE tenders SET updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), tender_id),
        )
        conn.commit()
        return True


def delete_tender(tender_id, actor_user):
    with get_connection() as conn:
        current = conn.execute("SELECT * FROM tenders WHERE id = ?", (tender_id,)).fetchone()
        if not current:
            return False
        record_audit(
            tender_id=tender_id,
            tender_reference=current["tender_reference"],
            username=actor_user["username"],
            role=actor_user["role"],
            action_performed="delete",
            field_changed="record",
            previous_value=str(dict(current)),
            updated_value="Deleted tender record",
        )
        conn.execute("DELETE FROM tenders WHERE id = ?", (tender_id,))
        conn.commit()
        return True


def record_audit(tender_id, tender_reference, username, role, action_performed, field_changed, previous_value, updated_value):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (
                tender_id, tender_reference, username, user_role, action_performed,
                field_changed, previous_value, updated_value, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                tender_id,
                tender_reference,
                username,
                role,
                action_performed,
                field_changed,
                previous_value,
                updated_value,
            ),
        )
        conn.commit()


def get_audit_logs():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
        return [dict(row) for row in rows]


def get_tender_activity(tender_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_logs WHERE tender_id = ? ORDER BY created_at DESC",
            (tender_id,),
        ).fetchall()
        return [dict(row) for row in rows]
