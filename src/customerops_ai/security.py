import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, HTTPException, Request
from sqlalchemy import delete, select

from .config import get_settings
from .db import session_scope
from .models import LoginSession, User, now


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    result = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
    return f"{salt}${result.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    parts = encoded.split("$")
    if len(parts) != 2:
        return False
    salt, expected = parts
    if len(salt) != 32 or len(expected) != 64:
        return False
    try:
        bytes.fromhex(salt)
        bytes.fromhex(expected)
    except ValueError:
        return False
    result = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
    return hmac.compare_digest(result.hex(), expected)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    role: str
    email: str


def authenticate_token(token: str) -> Principal:
    with session_scope() as db:
        row = db.execute(
            select(User, LoginSession)
            .join(LoginSession)
            .where(
                LoginSession.token_hash == token_hash(token),
                LoginSession.expires_at > now(),
            )
        ).first()
        if not row:
            raise HTTPException(401, "Session expired or invalid")
        user = row[0]
        return Principal(user.id, user.tenant_id, user.role, user.email)


def current_user(request: Request) -> Principal:
    token = request.cookies.get("customerops_session", "")
    authorization = request.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    elif request.method not in {"GET", "HEAD", "OPTIONS"}:
        if request.headers.get("Origin") != get_settings().allowed_origin:
            raise HTTPException(403, "Invalid origin")
    return authenticate_token(token)


def require_admin(user: Principal = Depends(current_user)) -> Principal:
    if user.role != "admin":
        raise HTTPException(403, "This action requires an administrator")
    return user


def login(tenant_id: str, email: str, password: str) -> tuple[str, Principal] | None:
    with session_scope() as db:
        user = db.scalar(
            select(User).where(User.tenant_id == tenant_id, User.email == email.lower())
        )

        dummy = "0" * 32 + "$" + "0" * 64
        valid = verify_password(password, user.password_hash if user else dummy)
        if not user or not valid:
            return None
        token = secrets.token_urlsafe(48)
        db.execute(delete(LoginSession).where(LoginSession.expires_at <= now()))
        db.add(
            LoginSession(
                token_hash=token_hash(token),
                user_id=user.id,
                expires_at=now() + timedelta(hours=get_settings().session_hours),
            )
        )
        return token, Principal(user.id, user.tenant_id, user.role, user.email)
