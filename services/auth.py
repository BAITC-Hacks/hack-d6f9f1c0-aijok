"""Small local SQLite authentication store for the demo."""

import re
import sqlite3
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


def _connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as database:
        database.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                identity TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )


def normalize_identity(value: str) -> str:
    value = value.strip().lower()
    if "@" in value:
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Укажите корректный email или телефон.")
        return value
    phone = re.sub(r"[\s()+-]", "", value)
    if not phone.isdigit() or len(phone) < 10:
        raise ValueError("Укажите корректный email или телефон.")
    return phone


def create_user(path: str | Path, name: str, identity: str, password: str) -> dict:
    if len(name.strip()) < 2:
        raise ValueError("Имя должно содержать не менее двух символов.")
    normalized = normalize_identity(identity)
    if len(password) < 8:
        raise ValueError("Пароль должен содержать не менее 8 символов.")
    try:
        with _connect(path) as database:
            cursor = database.execute(
                "INSERT INTO users (name, identity, password_hash) VALUES (?, ?, ?)",
                (name.strip(), normalized, generate_password_hash(password)),
            )
            return {"id": cursor.lastrowid, "name": name.strip()}
    except sqlite3.IntegrityError as exc:
        raise ValueError("Аккаунт с таким email или телефоном уже существует.") from exc


def authenticate_user(path: str | Path, identity: str, password: str) -> dict | None:
    try:
        normalized = normalize_identity(identity)
    except ValueError:
        return None
    with _connect(path) as database:
        row = database.execute("SELECT * FROM users WHERE identity = ?", (normalized,)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], password):
        return None
    return {"id": row["id"], "name": row["name"]}
