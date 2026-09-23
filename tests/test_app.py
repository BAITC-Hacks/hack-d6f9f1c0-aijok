from app import app


def test_home_page_contains_form_and_categories():
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert "EventMatch AI" in response.text
    assert "Подарки и сувениры" in response.text


def test_post_renders_ranked_results():
    response = app.test_client().post(
        "/",
        data={"city": "Алматы", "event_date": "2026-09-23", "event_format": "свадьба", "category": "Банкетный зал", "budget": "10000000", "language": "русский"},
    )
    assert response.status_code == 200
    assert "Подходящие подрядчики" in response.text
    assert response.text.count("Почему подходит") == 3


def test_expanded_demo_sections_and_safe_contacts():
    response = app.test_client().get("/")
    assert response.status_code == 200
    for text in ("Как это работает", "О сервисе", "EventMatch AI Assistant", "Демо-ассистент", "HackAlem AI • Case #79-lite"):
        assert text in response.text
    assert '+7 (***) ***-**-**' not in response.text  # contacts only appear on result cards
    assert 'step="1"' in response.text


def test_registration_login_and_logout(tmp_path):
    original = app.config["DATABASE"]
    from services.auth import init_db
    database = tmp_path / "eventmatch.db"
    init_db(database)
    app.config.update(TESTING=True, DATABASE=database, SECRET_KEY="test")
    client = app.test_client()
    registered = client.post("/auth", data={"mode": "register", "name": "Алия", "identity": "aliya@example.kz", "password": "safe-pass-123"}, follow_redirects=True)
    assert "Алия" in registered.text
    assert client.post("/logout", follow_redirects=True).status_code == 200
    logged_in = client.post("/auth", data={"mode": "login", "identity": "aliya@example.kz", "password": "safe-pass-123"}, follow_redirects=True)
    assert "Алия" in logged_in.text
    app.config["DATABASE"] = original


def test_invalid_login_is_rejected(tmp_path):
    from services.auth import init_db
    database = tmp_path / "eventmatch.db"
    init_db(database)
    app.config.update(TESTING=True, DATABASE=database)
    response = app.test_client().post("/auth", data={"mode": "login", "identity": "nobody@example.kz", "password": "wrong-pass"})
    assert "Неверный email, телефон или пароль" in response.text
