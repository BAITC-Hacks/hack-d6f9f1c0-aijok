"""Deterministic contractor selection based on the hackathon dataset."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


DATE_MIN = date(2026, 9, 23)
DATE_MAX = date(2026, 12, 31)
ALLOWED_CITIES = ("Алматы", "Астана", "Зарубежье")
ALLOWED_FORMATS = (
    "свадьба",
    "той",
    "корпоратив",
    "конференция",
    "юбилей",
    "день рождения",
)
ALLOWED_LANGUAGES = ("русский", "казахский", "английский")


def _split(value: str) -> tuple[str, ...]:
    """Split the pipe-delimited multi-value fields used by the CSV."""
    return tuple(part.strip() for part in (value or "").split("|") if part.strip())


def _boolean(value: str) -> bool:
    return value.strip().lower() == "true"


@dataclass(frozen=True)
class Contractor:
    id: str
    name: str
    categories: tuple[str, ...]
    city: str
    synthetic: bool
    price: int
    event_formats: tuple[str, ...]
    languages: tuple[str, ...]
    max_hours: float | None
    busy_dates: frozenset[date]
    description: str

    def public_data(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "categories": self.categories,
            "city": self.city,
            "synthetic": self.synthetic,
            "price": self.price,
            "event_formats": self.event_formats,
            "languages": self.languages,
            "max_hours": self.max_hours,
        }


def load_contractors(csv_path: str | Path) -> list[Contractor]:
    """Load all contractor profiles, parsing nullable and multi-value fields."""
    contractors: list[Contractor] = []
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            max_hours = float(row["max_hours"]) if row["max_hours"].strip() else None
            contractors.append(
                Contractor(
                    id=row["id"].strip(),
                    name=row["anon_name"].strip(),
                    categories=_split(row["categories"]),
                    city=row["city"].strip(),
                    synthetic=_boolean(row["synthetic"]),
                    price=int(row["price_from_kzt"]),
                    event_formats=_split(row["event_formats"]),
                    languages=_split(row["languages"]),
                    max_hours=max_hours,
                    busy_dates=frozenset(date.fromisoformat(item) for item in _split(row["busy_dates"])),
                    description=" ".join(row["description"].split()),
                )
            )
    return contractors


def categories_from(contractors: list[Contractor]) -> list[str]:
    return sorted({category for contractor in contractors for category in contractor.categories})


def validate_request(params: dict[str, Any], categories: list[str]) -> dict[str, Any]:
    """Validate and normalize form values or raise ValueError with a user-facing message."""
    required = {"city": "город", "event_date": "дату", "event_format": "тип мероприятия", "category": "категорию", "budget": "бюджет"}
    for key, label in required.items():
        if str(params.get(key, "")).strip() == "":
            raise ValueError(f"Укажите {label}.")

    city = str(params["city"]).strip()
    event_format = str(params["event_format"]).strip().lower()
    category = str(params["category"]).strip()
    language = str(params.get("language", "")).strip().lower() or None
    if city not in ALLOWED_CITIES:
        raise ValueError("Выберите город из списка.")
    if event_format not in ALLOWED_FORMATS:
        raise ValueError("Выберите тип мероприятия из списка.")
    if category not in categories:
        raise ValueError("Выберите категорию из датасета.")
    if language and language not in ALLOWED_LANGUAGES:
        raise ValueError("Выберите язык из списка.")
    try:
        event_date = date.fromisoformat(str(params["event_date"]))
    except ValueError as exc:
        raise ValueError("Укажите корректную дату мероприятия.") from exc
    if not DATE_MIN <= event_date <= DATE_MAX:
        raise ValueError("Дата должна быть в диапазоне 23.09.2026–31.12.2026.")
    try:
        budget = int(str(params["budget"]).replace(" ", ""))
    except ValueError as exc:
        raise ValueError("Бюджет должен быть целым числом.") from exc
    if budget <= 0:
        raise ValueError("Бюджет должен быть больше нуля.")
    duration_raw = str(params.get("duration", "")).strip()
    try:
        duration = float(duration_raw) if duration_raw else None
    except ValueError as exc:
        raise ValueError("Длительность должна быть числом.") from exc
    if duration is not None and not 0 < duration <= 24:
        raise ValueError("Длительность должна быть от 0 до 24 часов.")
    return {"city": city, "event_date": event_date, "event_format": event_format, "category": category, "budget": budget, "duration": duration, "language": language}


def _score(contractor: Contractor, query: dict[str, Any]) -> tuple[float, dict[str, float]]:
    budget_room = max(0.0, (query["budget"] - contractor.price) / query["budget"])
    budget_score = round(30 * budget_room, 2)
    language_score = 30.0 if query["language"] and query["language"] in contractor.languages else (10.0 if not query["language"] else 0.0)
    if query["duration"] is None or contractor.max_hours is None:
        duration_score = 15.0
    else:
        spare_hours = contractor.max_hours - query["duration"]
        duration_score = round(10 + 5 * min(spare_hours / max(contractor.max_hours, 1), 1), 2)
    profile_score = 15.0 + min(len(contractor.event_formats), 5) * 2
    factors = {"language": language_score, "budget": budget_score, "duration": duration_score, "profile": profile_score}
    return round(sum(factors.values()), 2), factors


def _explanation(contractor: Contractor, query: dict[str, Any]) -> str:
    budget_left = query["budget"] - contractor.price
    price = f"{contractor.price:,}".replace(",", " ")
    reserve = f"{budget_left:,}".replace(",", " ")
    sentences = [f"Стоимость от {price} ₸ укладывается в бюджет, запас составляет {reserve} ₸."]
    fit = f"Подрядчик работает с форматом «{query['event_format']}»"
    if query["language"]:
        if query["language"] in contractor.languages:
            fit += f" и поддерживает {query['language']} язык"
        else:
            fit += f"; выбранный {query['language']} язык не указан, в профиле доступны: {', '.join(contractor.languages)}"
    else:
        fit += f"; языки профиля: {', '.join(contractor.languages)}"
    sentences.append(fit + ".")
    if query["duration"] is not None:
        if contractor.max_hours is None:
            sentences.append(f"Запрошенная длительность — {query['duration']:g} ч, а ограничение длительности для этой услуги не применяется.")
        else:
            sentences.append(f"Лимит профиля {contractor.max_hours:g} ч покрывает запрошенные {query['duration']:g} ч.")
    # Pick actual profile information, skipping empty introductions and greetings.
    fragments = [part.strip(" -—") for part in re.split(r"(?<=[.!?])\s+", contractor.description)]
    meaningless = re.compile(r"^(меня зовут\b|приветствую\b|здравствуйте\b|привет\b)", re.IGNORECASE)
    detail = next((part for part in fragments if len(part) >= 20 and not meaningless.search(part)), "")
    if detail:
        detail = detail[:180].rstrip(" .") + ("…" if len(detail) > 180 else ".")
        sentences.append(f"Из описания профиля: {detail}")
    return " ".join(sentences[:4])


def recommend(contractors: list[Contractor], query: dict[str, Any], limit: int = 3) -> dict[str, Any]:
    """Filter candidates, explain exclusions, then deterministically rank up to ``limit``."""
    local = [c for c in contractors if c.city == query["city"] and query["category"] in c.categories]
    if not local:
        return {"state": "no_category_in_city", "results": [], "local_count": 0, "exclusions": {}}

    exclusions = {"busy": 0, "format": 0, "budget": 0, "duration": 0}
    eligible: list[Contractor] = []
    for contractor in local:
        failed = False
        if query["event_date"] in contractor.busy_dates:
            exclusions["busy"] += 1
            failed = True
        if query["event_format"] not in contractor.event_formats:
            exclusions["format"] += 1
            failed = True
        if contractor.price > query["budget"]:
            exclusions["budget"] += 1
            failed = True
        if query["duration"] is not None and contractor.max_hours is not None and query["duration"] > contractor.max_hours:
            exclusions["duration"] += 1
            failed = True
        if not failed:
            eligible.append(contractor)

    ranked = []
    for contractor in eligible:
        score, factors = _score(contractor, query)
        item = contractor.public_data()
        item.update(score=score, score_factors=factors, explanation=_explanation(contractor, query))
        ranked.append(item)
    ranked.sort(key=lambda item: (-item["score"], item["id"]))
    return {
        "state": "found" if ranked else "filtered_out",
        "results": ranked[:limit],
        "eligible_count": len(ranked),
        "local_count": len(local),
        "exclusions": exclusions,
        "event_date_display": query["event_date"].strftime("%d.%m.%Y"),
    }
