"""Local SQLite-backed authentication helpers for the demo application."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9 ()-]{7,19}$")


def connect(database: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    return connection


def init_database(database: str | Path) -> None:
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    with connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (email IS NOT NULL OR phone IS NOT NULL)
            )
            """
        )


def normalize_phone(phone: str) -> str:
    phone = phone.strip()
    if not phone:
        return ""
    prefix = "+" if phone.startswith("+") else ""
    return prefix + "".join(character for character in phone if character.isdigit())


def register_user(database: str | Path, name: str, password: str, email: str = "", phone: str = "") -> int:
    name = name.strip()
    email = email.strip().lower()
    raw_phone = phone.strip()
    phone = normalize_phone(raw_phone)
    if len(name) < 2:
        raise ValueError("Укажите имя длиной не менее двух символов.")
    if not email and not phone:
        raise ValueError("Укажите email или номер телефона.")
    if email and not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Укажите корректный email.")
    if raw_phone and not PHONE_PATTERN.fullmatch(raw_phone):
        raise ValueError("Укажите корректный номер телефона.")
    if len(password) < 8:
        raise ValueError("Пароль должен содержать не менее 8 символов.")

    try:
        with connect(database) as connection:
            cursor = connection.execute(
                "INSERT INTO users (name, email, phone, password_hash) VALUES (?, ?, ?, ?)",
                (name, email or None, phone or None, generate_password_hash(password)),
            )
            return int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError("Пользователь с таким email или телефоном уже зарегистрирован.") from exc


def authenticate(database: str | Path, identifier: str, password: str) -> sqlite3.Row | None:
    identifier = identifier.strip()
    normalized = normalize_phone(identifier)
    with connect(database) as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE lower(email) = ? OR phone = ?",
            (identifier.lower(), normalized),
        ).fetchone()
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def get_user(database: str | Path, user_id: int) -> sqlite3.Row | None:
    with connect(database) as connection:
        return connection.execute("SELECT id, name, email, phone FROM users WHERE id = ?", (user_id,)).fetchone()
