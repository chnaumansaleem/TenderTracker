from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from app.db import get_connection, init_database
from app.services.dashboard_service import get_dashboard_stats
from app.services.notification_service import (
    create_followup,
    get_setting,
    list_notifications,
    process_due_notifications,
    set_setting,
)
from app.services.tender_service import (
    create_tender,
    delete_tender,
    get_audit_logs,
    get_tender_activity,
    get_tender_by_id,
    list_tenders,
    update_tender,
)
from app.services.user_service import (
    authenticate_user,
    create_user,
    ensure_default_admin,
    list_users,
    reset_password,
    update_user,
)


PAGE_LABELS = [
    "Main Dashboard",
    "My Dashboard",
    "Tender Register",
    "Add New Tender",
    "Tender Calendar",
    "Follow-up & Reminders",
    "Reports & Analytics",
    "User Management",
    "Audit Logs",
    "System Settings",
]


def init_app():
    init_database()
    ensure_default_admin()
    if "user" not in st.session_state:
        st.session_state.user = None
    if "page" not in st.session_state:
        st.session_state.page = "Main Dashboard"


def current_user():
    return st.session_state.get("user")


def require_login():
    if not current_user():
        st.switch_page("app.py")


def get_allowed_pages(user):
    if not user:
        return ["Login"]
    if user["role"] == "admin":
        return PAGE_LABELS
    return [
        "My Dashboard",
        "Tender Register",
        "Add New Tender",
        "Tender Calendar",
        "Follow-up & Reminders",
        "Reports & Analytics",
    ]


def render_login():
    st.title("Tender & Bidding Management Tracker")
    st.caption("Secure tender management platform for business development teams")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        user = authenticate_user(username, password)
        if user:
            st.session_state.user = user
            st.session_state.page = "Main Dashboard" if user["role"] == "admin" else "My Dashboard"
            st.rerun()
        else:
            st.error("Invalid username or password.")


def render_logout_button():
    if st.button("Logout"):
        st.session_state.user = None
        st.session_state.page = "Main Dashboard"
        st.rerun()


def render_kpis(stats):
    metric_cols = st.columns(5)
    metric_vals = [
        ("Total Tenders", stats.get("total_tenders", 0)),
        ("Active", stats.get("active_tenders", 0)),
        ("In Progress", stats.get("in_progress", 0)),
        ("Under Eval", stats.get("under_evaluation", 0)),
        ("Win Rate", f"{stats.get('win_rate', 0):.1f}%"),
    ]
    for col, (label, value) in zip(metric_cols, metric_vals):
        col.metric(label, value)


def render_dashboard_page(user):
    is_admin = user["role"] == "admin"
    st.title("Main Admin Dashboard" if is_admin else "My Dashboard")
    filters = {}
    if not is_admin:
        filters["assigned_user"] = user["id"]
    dashboard = get_dashboard_stats(user=user if not is_admin else None, is_admin=is_admin, filters=filters)
    stats = dashboard["stats"]
    render_kpis(stats)

    left, right = st.columns(2)
    if dashboard["status_distribution"]:
        status_df = pd.DataFrame(dashboard["status_distribution"])
        fig = px.bar(status_df, x="status", y="count", title="Tender distribution by status")
        left.plotly_chart(fig, use_container_width=True)
    else:
        left.info("No tender status data available yet.")

    if dashboard["monthly_submissions"]:
        monthly_df = pd.DataFrame(dashboard["monthly_submissions"])
        fig2 = px.line(monthly_df, x="month", y="count", title="Monthly tender submissions")
        right.plotly_chart(fig2, use_container_width=True)
    else:
        right.info("No submission history available yet.")

    st.subheader("Recent tender portfolio")
    if dashboard["table"]:
        table_df = pd.DataFrame(dashboard["table"])[[
            "tender_id",
            "tender_title",
            "client_name",
            "country",
            "current_status",
            "submission_deadline",
            "owner_name",
        ]]
        st.dataframe(table_df, use_container_width=True)
    else:
        st.info("No tender records available.")


def render_tender_register(user):
    is_admin = user["role"] == "admin"
    st.title("Tender Register")
    filters = {}
    with st.sidebar:
        st.subheader("Filters")
        search = st.text_input("Search")
        status_filter = st.selectbox("Status", ["", "Not Started", "In Progress", "Under Evaluation", "Won", "Lost", "Cancelled", "On Hold"])
        country_filter = st.text_input("Country")
        sector_filter = st.text_input("Business Sector")
        if is_admin:
            users = list_users()
            user_map = {f"{item['full_name']} ({item['username']})": item["id"] for item in users}
            assigned_user = st.selectbox("Assigned user", ["", *list(user_map.keys())])
            filters["assigned_user"] = user_map.get(assigned_user)
        filters["search"] = search
        filters["status"] = status_filter
        filters["country"] = country_filter or None
        filters["business_sector"] = sector_filter or None

    items = list_tenders(user=user if not is_admin else None, is_admin=is_admin, filters={k: v for k, v in filters.items() if v not in (None, "")})
    if not items:
        st.info("No tenders found for the selected filters.")
        return

    tender_display = {f"{item['tender_id']} - {item['tender_title']}": item["id"] for item in items}
    selected_label = st.selectbox("Open a tender record", list(tender_display.keys()))
    selected_id = tender_display[selected_label]
    tender = get_tender_by_id(selected_id)

    if tender:
        st.subheader(f"{tender['tender_id']} - {tender['tender_title']}")
        overview = st.columns(3)
        overview[0].write(f"Client: {tender['client_name']}")
        overview[1].write(f"Project: {tender['project_name']}")
        overview[2].write(f"Status: {tender['current_status']}")

        with st.expander("Edit tender"):
            form = st.form("edit_tender_form")
            values = {
                "tender_title": form.text_input("Tender Title", value=tender["tender_title"]),
                "client_name": form.text_input("Client/Customer Name", value=tender["client_name"]),
                "project_name": form.text_input("Project Name", value=tender["project_name"]),
                "country": form.text_input("Country", value=tender["country"]),
                "business_sector": form.text_input("Business Sector", value=tender["business_sector"]),
                "tender_category": form.text_input("Tender Category", value=tender["tender_category"]),
                "department": form.text_input("Department", value=tender["department"]),
                "current_status": form.selectbox("Current Bid Status", ["Not Started", "In Progress", "Under Evaluation", "Won", "Lost", "Cancelled", "On Hold"], index=["Not Started", "In Progress", "Under Evaluation", "Won", "Lost", "Cancelled", "On Hold"].index(tender["current_status"] if tender["current_status"] in ["Not Started", "In Progress", "Under Evaluation", "Won", "Lost", "Cancelled", "On Hold"] else "Not Started")),
                "submission_deadline": form.date_input("Submission Deadline", pd.to_datetime(tender["submission_deadline"]).date() if tender.get("submission_deadline") else None),
                "next_action": form.text_area("Next Action", value=tender["next_action"] or ""),
                "important_notes": form.text_area("Important Notes", value=tender["important_notes"] or ""),
            }
            if form.form_submit_button("Save changes"):
                payload = {k: v for k, v in values.items() if v is not None}
                payload["submission_deadline"] = str(payload["submission_deadline"])
                update_tender(selected_id, payload, user)
                st.success("Tender updated successfully.")
                st.rerun()

        tabs = st.tabs(["Activity", "Audit History", "Attachments"])
        with tabs[0]:
            for item in get_tender_activity(selected_id):
                st.write(f"{item['created_at']} | {item['username']} | {item['action_performed']} | {item['field_changed']}")
        with tabs[1]:
            audit_rows = get_audit_logs()
            tender_audit = [r for r in audit_rows if str(r.get("tender_id")) == str(selected_id)]
            st.dataframe(pd.DataFrame(tender_audit), use_container_width=True)
        with tabs[2]:
            uploaded = st.file_uploader("Upload document", type=["pdf", "docx", "xlsx", "csv", "png", "jpg"], accept_multiple_files=True)
            if uploaded:
                import hashlib
                from pathlib import Path
                target_dir = Path("storage") / str(selected_id)
                target_dir.mkdir(parents=True, exist_ok=True)
                for file in uploaded:
                    safe_name = f"{hashlib.sha256(file.name.encode()).hexdigest()}_{file.name}"
                    with open(target_dir / safe_name, "wb") as fh:
                        fh.write(file.getvalue())
                    with get_connection() as conn:
                        conn.execute(
                            "INSERT INTO attachments (tender_id, file_name, stored_name, file_path, category, uploaded_by, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                            (selected_id, file.name, safe_name, str(target_dir / safe_name), "general", user["id"]),
                        )
                        conn.commit()
                st.success("Attachment uploaded.")

        if st.button("Delete tender", type="primary"):
            delete_tender(selected_id, user)
            st.success("Tender deleted.")
            st.rerun()


def render_add_tender(user):
    st.title("Add New Tender")
    with st.form("create_tender_form"):
        title = st.text_input("Tender Title")
        ref = st.text_input("Tender Reference Number")
        client = st.text_input("Client/Customer Name")
        project = st.text_input("Project Name")
        country = st.text_input("Country")
        sector = st.text_input("Business Sector")
        category = st.text_input("Tender Category")
        department = st.text_input("Department")
        owner_id = st.selectbox("Tender Owner", [
            (item["full_name"], item["id"]) for item in list_users()
        ])
        status = st.selectbox("Bid Status", ["Not Started", "In Progress", "Under Evaluation", "Won", "Lost", "Cancelled", "On Hold"])
        value = st.number_input("Estimated Contract Value", min_value=0.0, step=1000.0)
        currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "SAR", "AED", "PKR"])
        deadline = st.date_input("Submission Deadline")
        notes = st.text_area("Important Notes")
        next_action = st.text_area("Next Action")
        submit = st.form_submit_button("Create Tender")

    if submit:
        payload = {
            "tender_reference": ref,
            "tender_title": title,
            "client_name": client,
            "project_name": project,
            "country": country,
            "business_sector": sector,
            "tender_description": "",
            "tender_category": category,
            "tender_owner_id": owner_id[1],
            "department": department,
            "tender_source": "Manual Entry",
            "estimated_contract_value": value,
            "currency": currency,
            "submission_deadline": str(deadline),
            "current_status": status,
            "important_notes": notes,
            "next_action": next_action,
        }
        create_tender(payload, user["id"])
        st.success("Tender created successfully.")


def render_calendar_page(user):
    st.title("Tender Calendar")
    records = list_tenders(user=user if user["role"] != "admin" else None, is_admin=user["role"] == "admin")
    events = []
    for item in records:
        for event_name, field in [
            ("Bid Open Date", item.get("bid_open_date")),
            ("Submission Deadline", item.get("submission_deadline")),
            ("Actual Submission Date", item.get("actual_submission_date")),
            ("Bid Closure Date", item.get("bid_closure_date")),
            ("Follow-up", item.get("next_follow_up_date")),
        ]:
            if field:
                events.append({
                    "date": field,
                    "event": event_name,
                    "tender": item["tender_id"],
                    "status": item["current_status"],
                    "owner": item.get("owner_name") or "Unassigned",
                })
    if events:
        event_df = pd.DataFrame(events)
        st.dataframe(event_df, use_container_width=True)
    else:
        st.info("No calendar events available.")

    with st.form("followup_form"):
        tender_id = st.selectbox("Tender", [f"{item['tender_id']} - {item['tender_title']}" for item in records])
        title = st.text_input("Follow-up title")
        scheduled_for = st.date_input("Scheduled date")
        notes = st.text_area("Notes")
        if st.form_submit_button("Add reminder"):
            right_id = next(item["id"] for item in records if f"{item['tender_id']} - {item['tender_title']}" == tender_id)
            create_followup(right_id, user["id"], title, str(scheduled_for), notes)
            st.success("Follow-up created.")


def render_followup_page(user):
    st.title("Follow-up & Reminders")
    if st.button("Run reminder check"):
        process_due_notifications()
        st.success("Reminder processing completed.")
    db_notifications = list_notifications()
    if db_notifications:
        st.dataframe(pd.DataFrame(db_notifications), use_container_width=True)
    else:
        st.info("No reminder history available.")


def render_reports_page(user):
    st.title("Reports & Analytics")
    dashboard = get_dashboard_stats(user=user if user["role"] != "admin" else None, is_admin=user["role"] == "admin")
    if dashboard["status_distribution"]:
        status_df = pd.DataFrame(dashboard["status_distribution"])
        fig = px.pie(status_df, names="status", values="count", title="Tender status distribution")
        st.plotly_chart(fig, use_container_width=True)
    if dashboard["customer_distribution"]:
        customer_df = pd.DataFrame(dashboard["customer_distribution"])
        st.bar_chart(customer_df.set_index("client_name")["count"]) if not customer_df.empty else None
    st.dataframe(pd.DataFrame(dashboard["table"]), use_container_width=True)


def render_user_management(user):
    if user["role"] != "admin":
        st.error("Access denied.")
        return
    st.title("User Management")
    users = list_users()
    st.dataframe(pd.DataFrame(users), use_container_width=True)
    with st.form("user_creation"):
        full_name = st.text_input("Full Name")
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        submit = st.form_submit_button("Create user")
    if submit:
        create_user(full_name, username, password, email, role)
        st.success("User created.")


def render_audit_logs(user):
    if user["role"] != "admin":
        st.error("Access denied.")
        return
    st.title("Audit Logs")
    logs = get_audit_logs()
    st.dataframe(pd.DataFrame(logs), use_container_width=True)


def render_system_settings(user):
    if user["role"] != "admin":
        st.error("Access denied.")
        return
    st.title("System Settings")
    st.write("SMTP and reminder configuration")
    smtp_host = st.text_input("SMTP Host", value=get_setting("smtp_host", ""))
    smtp_port = st.text_input("SMTP Port", value=get_setting("smtp_port", "587"))
    smtp_user = st.text_input("SMTP User", value=get_setting("smtp_user", ""))
    smtp_password = st.text_input("SMTP Password", value=get_setting("smtp_password", ""), type="password")
    from_email = st.text_input("From Email", value=get_setting("smtp_from_email", ""))
    if st.button("Save settings"):
        set_setting("smtp_host", smtp_host)
        set_setting("smtp_port", smtp_port)
        set_setting("smtp_user", smtp_user)
        set_setting("smtp_password", smtp_password)
        set_setting("smtp_from_email", from_email)
        st.success("Settings saved.")


def main():
    st.set_page_config(page_title="Tender Tracker", layout="wide")
    init_app()
    user = current_user()
    if not user:
        render_login()
        return

    st.sidebar.title("Navigation")
    for page in get_allowed_pages(user):
        if page == "Login":
            continue
        if st.sidebar.button(page):
            st.session_state.page = page

    render_logout_button()
    selected = st.session_state.page
    if selected == "Main Dashboard":
        render_dashboard_page(user)
    elif selected == "My Dashboard":
        render_dashboard_page(user)
    elif selected == "Tender Register":
        render_tender_register(user)
    elif selected == "Add New Tender":
        render_add_tender(user)
    elif selected == "Tender Calendar":
        render_calendar_page(user)
    elif selected == "Follow-up & Reminders":
        render_followup_page(user)
    elif selected == "Reports & Analytics":
        render_reports_page(user)
    elif selected == "User Management":
        render_user_management(user)
    elif selected == "Audit Logs":
        render_audit_logs(user)
    elif selected == "System Settings":
        render_system_settings(user)


if __name__ == "__main__":
    main()
