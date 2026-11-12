import os

from app.db import init_database
from app.security import hash_password, verify_password
from app.services.user_service import authenticate_user, ensure_default_admin


def test_password_hash_round_trip():
    secret = "SuperSecurePassword!"
    hashed = hash_password(secret)
    assert verify_password(secret, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_default_admin_setup():
    init_database()
    ensure_default_admin()
    user = authenticate_user("admin", "Admin@123")
    assert user is not None
    assert user["role"] == "admin"
