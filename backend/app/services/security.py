import base64
import hashlib
import secrets

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Header, HTTPException, status

from app.config import get_settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().app_secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str:
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def require_admin(x_admin_password: str = Header(default="")) -> None:
    expected = get_settings().admin_password
    if not expected or not secrets.compare_digest(x_admin_password, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )
