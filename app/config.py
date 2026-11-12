import os
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = DATA_DIR / "tender_tracker.db"


def _read_secrets_file() -> dict:
    secrets_path = Path.home() / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return {}
    try:
        with secrets_path.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


def get_setting(section: str, key: str, default=None):
    secrets = _read_secrets_file()
    if section in secrets and key in secrets[section]:
        return secrets[section][key]
    env_key = f"{section.upper()}_{key.upper()}"
    return os.getenv(env_key, default)


def get_database_url() -> str:
    url = get_setting("database", "url", f"sqlite:///{DB_PATH}")
    if url.startswith("sqlite://"):
        if url.startswith("sqlite:///"):
            return url
        if url.startswith("sqlite://") and not url.startswith("sqlite:///"):
            return f"sqlite:///{url.split('sqlite://', 1)[1]}"
    return url


DATA_DIR.mkdir(exist_ok=True)
STORAGE_DIR.mkdir(exist_ok=True)
