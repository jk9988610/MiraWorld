from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Cookie, HTTPException, Response

JWT_SECRET = os.environ.get("MIRAWORLD_JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_EXP_HOURS = int(os.environ.get("MIRAWORLD_JWT_EXP_HOURS", "72"))
COOKIE_NAME = "miraworld_session"
COOKIE_PATH = os.environ.get("MIRAWORLD_COOKIE_PATH", "/miraworld/")


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def verify_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash)


def create_token(user_id: int, handle: str, *, hours: int | None = None) -> str:
    exp_hours = hours if hours is not None else JWT_EXP_HOURS
    exp = datetime.now(UTC) + timedelta(hours=exp_hours)
    return jwt.encode(
        {"sub": str(user_id), "handle": handle, "exp": exp},
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


def set_session_cookie(
    response: Response,
    token: str,
    *,
    max_age_seconds: int | None = None,
) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path=COOKIE_PATH,
        max_age=max_age_seconds if max_age_seconds is not None else JWT_EXP_HOURS * 3600,
        secure=os.environ.get("MIRAWORLD_COOKIE_SECURE", "").lower() == "true",
    )


REMEMBER_HOURS = int(os.environ.get("MIRAWORLD_JWT_REMEMBER_HOURS", str(30 * 24)))


def issue_session_cookie(response: Response, user_id: int, handle: str, remember: bool = False) -> None:
    hours = REMEMBER_HOURS if remember else JWT_EXP_HOURS
    set_session_cookie(
        response,
        create_token(user_id, handle, hours=hours),
        max_age_seconds=hours * 3600,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path=COOKIE_PATH)


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
