from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.services.tender_service import list_tenders


def get_dashboard_stats(user=None, is_admin=False, filters=None):
    tenders = list_tenders(user=user, is_admin=is_admin, filters=filters)
    df = pd.DataFrame(tenders)
    if df.empty:
        stats = {
            "total_tenders": 0,
            "active_tenders": 0,
            "in_progress": 0,
            "under_evaluation": 0,
            "won_bids": 0,
            "lost_bids": 0,
            "cancelled_bids": 0,
            "upcoming_submissions": 0,
            "overdue_submissions": 0,
            "win_rate": 0.0,
        }
        return {
            "stats": stats,
            "status_distribution": [],
            "monthly_submissions": [],
            "monthly_performance": [],
            "customer_distribution": [],
            "country_distribution": [],
            "sector_distribution": [],
            "user_workload": [],
            "table": [],
        }

    df["submission_deadline"] = pd.to_datetime(df["submission_deadline"], errors="coerce")
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    df["current_status"] = df["current_status"].fillna("Not Started")

    today = pd.Timestamp.utcnow().normalize()
    status_counts = df["current_status"].value_counts().to_dict()

    total_tenders = len(df)
    active_tenders = int(df[df["current_status"].isin(["Not Started", "In Progress", "Under Evaluation", "On Hold"])].shape[0])
    in_progress = int(status_counts.get("In Progress", 0))
    under_evaluation = int(status_counts.get("Under Evaluation", 0))
    won_bids = int(status_counts.get("Won", 0))
    lost_bids = int(status_counts.get("Lost", 0))
    cancelled_bids = int(status_counts.get("Cancelled", 0))
    upcoming_submissions = int(df[(df["submission_deadline"].notna()) & (df["submission_deadline"] >= today)].shape[0])
    overdue_submissions = int(df[(df["submission_deadline"].notna()) & (df["submission_deadline"] < today) & (~df["current_status"].isin(["Won", "Lost", "Cancelled"]))].shape[0])
    completed_bids = won_bids + lost_bids
    win_rate = round((won_bids / completed_bids * 100), 2) if completed_bids else 0.0

    status_distribution = [
        {"status": key, "count": int(value)}
        for key, value in sorted(status_counts.items(), key=lambda x: x[0])
    ]

    monthly_df = df.groupby(df["created_at"].dt.to_period("M").astype(str)).size().reset_index()
    monthly_submissions = [
        {"month": row[0], "count": int(row[1])}
        for row in monthly_df.itertuples(index=False, name=None)
    ]

    monthly_performance = []
    summary = df.groupby([df["created_at"].dt.to_period("M").astype(str), "current_status"]).size().reset_index()
    for month, group in summary.groupby(0):
        wins = int(group[group[1] == "Won"][2].sum()) if not group[group[1] == "Won"].empty else 0
        losses = int(group[group[1] == "Lost"][2].sum()) if not group[group[1] == "Lost"].empty else 0
        monthly_performance.append({"month": month, "wins": wins, "losses": losses})

    customer_distribution = [
        {"client_name": key, "count": int(value)}
        for key, value in df["client_name"].fillna("Unknown").value_counts().head(10).items()
    ]
    country_distribution = [
        {"country": key, "count": int(value)}
        for key, value in df["country"].fillna("Unknown").value_counts().head(10).items()
    ]
    sector_distribution = [
        {"sector": key, "count": int(value)}
        for key, value in df["business_sector"].fillna("Unknown").value_counts().head(10).items()
    ]
    user_workload = [
        {"owner": key, "count": int(value)}
        for key, value in df["owner_name"].fillna("Unassigned").value_counts().head(10).items()
    ]

    stats = {
        "total_tenders": total_tenders,
        "active_tenders": active_tenders,
        "in_progress": in_progress,
        "under_evaluation": under_evaluation,
        "won_bids": won_bids,
        "lost_bids": lost_bids,
        "cancelled_bids": cancelled_bids,
        "upcoming_submissions": upcoming_submissions,
        "overdue_submissions": overdue_submissions,
        "win_rate": win_rate,
    }

    return {
        "stats": stats,
        "status_distribution": status_distribution,
        "monthly_submissions": monthly_submissions,
        "monthly_performance": monthly_performance,
        "customer_distribution": customer_distribution,
        "country_distribution": country_distribution,
        "sector_distribution": sector_distribution,
        "user_workload": user_workload,
        "table": tenders,
    }
