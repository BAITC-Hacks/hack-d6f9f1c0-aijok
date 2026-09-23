import sqlite3
from pathlib import Path

import pytest
from werkzeug.security import check_password_hash

from app import app


@pytest.fixture()
def client(tmp_path):
    app.config.update(TESTING=True, DATABASE=tmp_path / "users.db", SECRET_KEY="test-secret")
    from services.auth import init_database

    init_database(app.config["DATABASE"])
    return app.test_client()


def test_home_page_contains_form_and_categories(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "EventMatch AI" in response.text
    assert "Подарки и сувениры" in response.text


def test_post_renders_ranked_results_without_login(client):
    response = client.post(
        "/",
        data={"city": "Алматы", "event_date": "2026-09-23", "event_format": "свадьба", "category": "Банкетный зал", "budget": "10000000", "language": "русский"},
    )
    assert response.status_code == 200
    assert "Подходящие подрядчики" in response.text
    assert response.text.count("Почему подходит") == 3


def test_date_field_and_demo_features_are_rendered(client):
    response = client.get("/")
    assert 'placeholder="ДД.ММ.ГГГГ"' in response.text
    assert "EventMatch AI Assistant" in response.text
    assert "Демо-ассистент" in response.text
    assert "Что означает совпадение?" in response.text
    assert 'name="budget" type="number" min="1" step="1"' in response.text


def test_synthetic_badge_and_assistant_answers_exist():
    root = Path(__file__).parents[1]
    template = (root / "templates" / "index.html").read_text(encoding="utf-8")
    script = (root / "static" / "script.js").read_text(encoding="utf-8")
    assert "Синтетический профиль" in template
    assert "Я пока работаю в демонстрационном режиме" in script
    assert "busy_dates" in script
    assert "Случайные числа не используются" in script


@pytest.mark.parametrize("field,value", [("email", "user@example.com"), ("phone", "+7 700 000 00 00")])
def test_registration_login_and_logout(client, field, value):
    registration = {"name": "Алия", "password": "safe-password-123", field: value}
    response = client.post("/register", data=registration, follow_redirects=True)
    assert response.status_code == 200
    assert "Здравствуйте, <b>Алия</b>" in response.text

    with sqlite3.connect(app.config["DATABASE"]) as connection:
        stored_hash = connection.execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored_hash != registration["password"]
    assert check_password_hash(stored_hash, registration["password"])

    response = client.post("/logout", follow_redirects=True)
    assert "Войти" in response.text
    response = client.post("/login", data={"identifier": value, "password": registration["password"]}, follow_redirects=True)
    assert "Здравствуйте, <b>Алия</b>" in response.text
    response = client.post("/logout", follow_redirects=True)
    assert "Войти" in response.text
