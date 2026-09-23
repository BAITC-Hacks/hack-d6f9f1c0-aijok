from datetime import date, timedelta
from pathlib import Path

import pytest

from services.recommender import (
    DATE_MIN,
    categories_from,
    load_contractors,
    recommend,
    validate_request,
)


DATA_PATH = Path(__file__).parents[1] / "data" / "hackathon-dataset-anonymized.csv"


@pytest.fixture(scope="module")
def contractors():
    return load_contractors(DATA_PATH)


def query(**overrides):
    values = {
        "city": "Алматы",
        "event_date": date(2026, 9, 23),
        "event_format": "свадьба",
        "category": "Банкетный зал",
        "budget": 10_000_000,
        "duration": None,
        "language": "русский",
    }
    return values | overrides


def test_loads_all_66_profiles_and_dataset_categories(contractors):
    assert len(contractors) == 66
    assert len(categories_from(contractors)) == 17
    assert all(isinstance(item.busy_dates, frozenset) for item in contractors)


def test_returns_three_results_in_stable_order(contractors):
    first = recommend(contractors, query())
    second = recommend(contractors, query())
    expected = ["HK-50695", "HK-58236", "HK-69010"]
    assert [item["id"] for item in first["results"]] == expected
    assert [item["id"] for item in second["results"]] == expected
    assert all(item["explanation"] for item in first["results"])


def test_returns_one_or_two_and_reports_total(contractors):
    one = recommend(contractors, query(budget=2_000_000, duration=6.0))
    two = recommend(
        contractors,
        query(category="Ведущий", event_date=date(2026, 9, 24), budget=2_000_000, duration=6.0),
    )
    assert one["eligible_count"] == 1
    assert two["eligible_count"] == 2
    assert len(one["results"]) == 1
    assert len(two["results"]) == 2


def test_distinguishes_absent_category_from_filtered_results(contractors):
    absent = recommend(contractors, query(city="Астана", category="Декоратор"))
    filtered = recommend(
        contractors,
        query(event_date=date(2026, 9, 24), budget=2_000_000, duration=6.0),
    )
    assert absent["state"] == "no_category_in_city"
    assert filtered["state"] == "filtered_out"
    assert filtered["exclusions"] == {"busy": 4, "format": 1, "budget": 6, "duration": 0}


def test_busy_contractor_is_excluded_and_date_changes_results(contractors):
    first_day = recommend(contractors, query())
    next_day = recommend(contractors, query(event_date=DATE_MIN + timedelta(days=1)))
    assert [item["id"] for item in first_day["results"]] != [item["id"] for item in next_day["results"]]
    for item in next_day["results"]:
        contractor = next(c for c in contractors if c.id == item["id"])
        assert DATE_MIN + timedelta(days=1) not in contractor.busy_dates


def test_null_max_hours_does_not_filter_service(contractors):
    florist = next(c for c in contractors if c.max_hours is None and "Флорист" in c.categories)
    result = recommend(
        [florist],
        query(city=florist.city, category="Флорист", event_format=florist.event_formats[0], event_date=next(d for d in (DATE_MIN + timedelta(days=i) for i in range(100)) if d not in florist.busy_dates), budget=florist.price, duration=24.0),
    )
    assert result["state"] == "found"


def test_language_affects_ranking_without_becoming_a_hard_filter(contractors):
    base = query(category="Ведущий", event_format="корпоратив", event_date=date(2026, 10, 5), duration=4.0)
    english = recommend(contractors, base | {"language": "английский"})
    russian = recommend(contractors, base | {"language": "русский"})
    assert english["results"] != russian["results"]
    assert english["results"][0]["score_factors"]["language"] == 30


@pytest.mark.parametrize("event_date", ["2026-09-22", "2027-01-01", "not-a-date"])
def test_rejects_invalid_dates(contractors, event_date):
    raw = {"city": "Алматы", "event_date": event_date, "event_format": "свадьба", "category": "Фотограф", "budget": "1000000"}
    with pytest.raises(ValueError):
        validate_request(raw, categories_from(contractors))
