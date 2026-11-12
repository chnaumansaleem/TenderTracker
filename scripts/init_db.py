from app.db import init_database
from app.services.user_service import ensure_default_admin


if __name__ == "__main__":
    init_database()
    ensure_default_admin()
    print("Database initialized and default admin account ensured.")
