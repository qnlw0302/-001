from __future__ import annotations

import sqlite3
from functools import wraps
from typing import Any, Callable, Optional

from flask import current_app, jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash

from crud import (
    create_user,
    get_password_hash,
    get_user_by_id,
    get_user_by_username,
)
from schemas import User


SESSION_USER_KEY = "user_id"


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="pbkdf2:sha256")


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def current_user(connection: sqlite3.Connection) -> Optional[User]:
    user_id = session.get(SESSION_USER_KEY)
    if not user_id:
        return None
    return get_user_by_id(connection, int(user_id))


def current_user_id() -> Optional[int]:
    user_id = session.get(SESSION_USER_KEY)
    if not user_id:
        return None
    return int(user_id)


def verify_current_password(connection: sqlite3.Connection, password: str) -> bool:
    user_id = session.get(SESSION_USER_KEY)
    if not user_id:
        return False
    stored = get_password_hash(connection, int(user_id))
    if stored is None:
        return False
    return verify_password(stored, password)


def login_user(user_id: int, remember: bool) -> None:
    session.clear()
    session[SESSION_USER_KEY] = int(user_id)
    session.permanent = bool(remember)


def logout_user() -> None:
    session.clear()


def login_required(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not session.get(SESSION_USER_KEY):
            return jsonify({"error": "Authentication required."}), 401
        return func(*args, **kwargs)

    return wrapper


def ensure_seed_admin(
    connection: sqlite3.Connection,
    username: str,
    password: str,
) -> Optional[int]:
    username = (username or "").strip()
    if not username or not password:
        return None
    existing = get_user_by_username(connection, username)
    if existing is not None:
        return int(existing["id"])
    user = create_user(connection, username, hash_password(password))
    current_app.logger.info("Seeded admin user %r.", username)
    return user.id
