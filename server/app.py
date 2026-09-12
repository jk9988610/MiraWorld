"""MiraWorld account API: register, login, session."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import bcrypt
import jwt
from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

DATABASE = Path(
    os.environ.get("MIRAWORLD_AUTH_DB", "/var/lib/miraworld/auth.db")
)
JWT_SECRET = os.environ.get("MIRAWORLD_JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_EXP_HOURS = int(os.environ.get("MIRAWORLD_JWT_EXP_HOURS", "72"))
COOKIE_NAME = "miraworld_session"
COOKIE_PATH = "/miraworld/"

app = FastAPI(title="MiraWorld Auth", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=64)


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserPublic(BaseModel):
    id: int
    email: str
    display_name: str
    created_at: str


def _connect() -> sqlite3.Connection:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                display_name TEXT NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def verify_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash)


def create_token(user_id: int, email: str) -> str:
    exp = datetime.now(UTC) + timedelta(hours=JWT_EXP_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "exp": exp},
        JWT_SECRET,
        algorithm=JWT_ALG,
    )


def row_to_user(row: sqlite3.Row) -> UserPublic:
    return UserPublic(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
        created_at=row["created_at"],
    )


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path=COOKIE_PATH,
        max_age=JWT_EXP_HOURS * 3600,
        secure=os.environ.get("MIRAWORLD_COOKIE_SECURE", "").lower() == "true",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path=COOKIE_PATH)


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")


def get_current_user(
    miraworld_session: str | None = Cookie(default=None),
) -> UserPublic:
    if not miraworld_session:
        raise HTTPException(status_code=401, detail="未登录")
    user_id = decode_token(miraworld_session)
    with db() as conn:
        row = conn.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return row_to_user(row)


@app.on_event("startup")
def on_startup() -> None:
    if JWT_SECRET == "dev-secret-change-me" and os.environ.get("MIRAWORLD_ENV") == "production":
        raise RuntimeError("Set MIRAWORLD_JWT_SECRET in production")
    init_db()


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/auth/register", response_model=UserPublic)
def register(body: RegisterBody, response: Response) -> UserPublic:
    created_at = datetime.now(UTC).isoformat()
    password_hash = hash_password(body.password)
    try:
        with db() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (email, display_name, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    body.email.strip().lower(),
                    body.display_name.strip(),
                    password_hash,
                    created_at,
                ),
            )
            user_id = int(cur.lastrowid)
            row = conn.execute(
                "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="该邮箱已注册")

    assert row is not None
    user = row_to_user(row)
    set_session_cookie(response, create_token(user.id, user.email))
    return user


@app.post("/auth/login", response_model=UserPublic)
def login(body: LoginBody, response: Response) -> UserPublic:
    email = body.email.strip().lower()
    with db() as conn:
        row = conn.execute(
            "SELECT id, email, display_name, created_at, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    user = row_to_user(row)
    set_session_cookie(response, create_token(user.id, user.email))
    return user


@app.post("/auth/logout")
def logout(response: Response) -> dict[str, bool]:
    clear_session_cookie(response)
    return {"ok": True}


@app.get("/auth/me", response_model=UserPublic)
def me(user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return user
