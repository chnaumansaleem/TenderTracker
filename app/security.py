import hashlib
import os
import re
from typing import Any


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return salt.hex() + ':' + dk.hex()


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash or ':' not in password_hash:
        return False
    salt_hex, digest_hex = password_hash.split(':', 1)
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
    return dk.hex() == digest_hex


def clean_string(value: Any, default: str = '') -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def slugify(value: Any) -> str:
    text = clean_string(value)
    return re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').lower() or 'record'
