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
