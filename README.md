# Tender & Bidding Management Tracker

A secure, modular Streamlit application for managing tenders, awards, follow-ups, reminders, dashboards, and audit history in a centralized data store.

## Architecture

The project follows a layered design to keep the app maintainable and deployment-ready:

- Presentation layer: Streamlit pages and UI components in `app.py`
- Service layer: business logic for users, tenders, dashboards, notifications, and attachments in `app/services/`
- Data layer: SQLite in `app/db.py`
- Security layer: hashed passwords, role checks, and access validation in `app/security.py`

### Database schema

Core tables include:

- `users`: system users, roles, and login state
- `tenders`: tender lifecycle records and metadata
- `attachments`: linked tender documents and uploads
- `notifications`: reminders and outbound email events
- `audit_logs`: user actions and field-level history
- `settings`: app configuration values
- `followups`: internal reminder tasks and deadlines

### Deployment approach

- Local development and the current app implementation use SQLite at `data/tender_tracker.db`.
- Hosting: GitHub + Streamlit Community Cloud
- The database and uploaded files are stored on the app's local filesystem. Streamlit Community Cloud does not guarantee that these files persist across restarts or redeployments, and separate app replicas do not share them. Use this setup for a demo or single-instance trial, not as durable production storage.
- PostgreSQL and persistent cloud file storage are not currently implemented; `DATABASE_URL` and the `[database].url` sample setting do not switch the app away from SQLite.

## Project structure

```text
TenderTracker/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── security.py
│   └── services/
│       ├── __init__.py
│       ├── dashboard_service.py
│       ├── notification_service.py
│       ├── tender_service.py
│       └── user_service.py
├── scripts/
│   └── init_db.py
├── storage/
├── tests/
│   └── test_basic.py
├── .gitignore
├── app.py
├── example.secrets.toml
├── README.md
├── requirements.txt
└── data/
```

## Quick start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Initialize the database and create the default admin user:

```bash
python scripts/init_db.py
```

3. Run the application:

```bash
streamlit run app.py
```

4. Sign in with the generated default admin account. The local defaults are `admin` / `Admin@123`; set your own credentials before exposing the app.

## Security notes

- Passwords are never stored in plain text.
- Role-based access is enforced at the UI and service level.
- Sensitive settings should live in Streamlit secrets or environment variables.
- Do not commit real credentials to GitHub.

## Deploy to Streamlit Community Cloud

1. Push this project to a GitHub repository. Do not commit credentials, a real `secrets.toml`, the local database, or uploaded files.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app from that repository, select the branch, and set the main file to `app.py`.
3. In the app's **Settings → Secrets**, add the `[app]` section from `example.secrets.toml` and choose a unique admin password, for example:

   ```toml
   [app]
   admin_username = "admin"
   admin_password = "replace-with-a-long-unique-password"
   ```

   These credentials are used when the app creates the initial admin. Existing users are not overwritten on later starts.
4. Deploy. The app initializes its SQLite schema and creates the admin account on first startup; no separate database initialization command is needed.
5. To retain data across restarts or redeployments, first migrate the database and uploaded-file handling to persistent services. The current app uses local SQLite and local disk for both.

## Testing

```bash
python -m pytest tests/test_basic.py
```

## Sample credentials

The system uses a secure admin bootstrap. After the first login, update the password from the user management screen and create role-based accounts for your team.
