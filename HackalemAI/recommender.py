import csv


def split_values(value):
    """Превращает 'русский|казахский' в список."""
    if not value:
        return []

    return [item.strip() for item in value.split("|") if item.strip()]


def load_data(filename):
    contractors = []

    with open(filename, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            # Превращаем строки с | в списки
            row["categories"] = split_values(row["categories"])
            row["event_formats"] = split_values(row["event_formats"])
            row["languages"] = split_values(row["languages"])
            row["busy_dates"] = split_values(row["busy_dates"])

            # Цена -> число
            if row["price_from_kzt"]:
                row["price_from_kzt"] = int(float(row["price_from_kzt"]))
            else:
                row["price_from_kzt"] = None

            # Максимальные часы -> число или None
            if row["max_hours"]:
                row["max_hours"] = float(row["max_hours"])
            else:
                row["max_hours"] = None

            # synthetic -> True / False
            row["synthetic"] = (
                row["synthetic"].strip().lower() == "true"
            )

            contractors.append(row)

    return contractors
    contractors = []

    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                contractors.append(json.loads(line))

    return contractors


def normalize(text):
    return str(text).strip().lower()


def has_value(values, target):
    if not values:
        return False

    return any(normalize(x) == normalize(target) for x in values)


def find_contractors(
    contractors,
    city,
    date,
    event_type,
    category,
    budget,
    duration=None,
    language=None
):
    # Сначала ищем всех подрядчиков этой категории в городе
    category_contractors = []

    for contractor in contractors:
        if (
            normalize(contractor.get("city")) == normalize(city)
            and has_value(contractor.get("categories", []), category)
        ):
            category_contractors.append(contractor)

    # В городе вообще нет такой категории
    if not category_contractors:
        return {
            "status": "CATEGORY_NOT_FOUND",
            "message": f"В городе {city} нет категории «{category}».",
            "results": []
        }

    suitable = []

    busy_count = 0
    budget_count = 0
    format_count = 0
    duration_count = 0
    language_count = 0

    for contractor in category_contractors:

        # Проверяем дату
        if date in contractor.get("busy_dates", []):
            busy_count += 1
            continue

        # Проверяем бюджет
        price = contractor.get("price_from_kzt")

        if price is not None and price > budget:
            budget_count += 1
            continue

        # Проверяем формат мероприятия
        formats = contractor.get("event_formats", [])

        if formats and not has_value(formats, event_type):
            format_count += 1
            continue

        # Проверяем длительность
        max_hours = contractor.get("max_hours")

        if (
            duration is not None
            and max_hours is not None
            and max_hours < duration
        ):
            duration_count += 1
            continue

        # Проверяем язык
        languages = contractor.get("languages", [])

        if language and languages and not has_value(languages, language):
            language_count += 1
            continue

        # Если всё прошло — считаем рейтинг
        score = calculate_score(
            contractor,
            budget,
            duration,
            language
        )

        suitable.append((score, contractor))

    # Подрядчики есть, но никто не прошёл условия
    if not suitable:
        reasons = []

        if busy_count:
            reasons.append(f"заняты на дату: {busy_count}")

        if budget_count:
            reasons.append(f"выше бюджета: {budget_count}")

        if format_count:
            reasons.append(f"не берут этот формат: {format_count}")

        if duration_count:
            reasons.append(f"не подходят по длительности: {duration_count}")

        if language_count:
            reasons.append(f"не работают на нужном языке: {language_count}")

        return {
            "status": "NO_MATCHES",
            "message": "Подрядчики есть, но никто не подошёл. "
                       + "; ".join(reasons),
            "results": []
        }

    # Стабильная сортировка
    suitable.sort(
        key=lambda x: (
            -x[0],
            x[1].get("price_from_kzt") or 0,
            str(x[1].get("id", ""))
        )
    )

    # Берём максимум 3
    top_three = suitable[:3]

    results = []

    for score, contractor in top_three:
        results.append({
            "name": contractor.get("anon_name", "Без имени"),
            "category": category,
            "city": contractor.get("city"),
            "price": contractor.get("price_from_kzt"),
            "synthetic": contractor.get("synthetic", False),
            "explanation": make_explanation(
                contractor,
                budget,
                event_type,
                duration,
                language
            )
        })

    message = f"Подобрано подрядчиков: {len(results)}."

    if len(results) < 3:
        message += (
            f" Больше подходящих под все условия кандидатов нет."
        )

    return {
        "status": "MATCHED",
        "message": message,
        "results": results
    }


def calculate_score(contractor, budget, duration, language):
    score = 0

    # Цена
    price = contractor.get("price_from_kzt")

    if price is not None and price <= budget:
        saving = budget - price

        if saving >= budget * 0.25:
            score += 30
        elif saving >= budget * 0.10:
            score += 25
        else:
            score += 20

    # Язык
    if language and has_value(
        contractor.get("languages", []),
        language
    ):
        score += 20

    # Длительность
    max_hours = contractor.get("max_hours")

    if duration is not None:
        if max_hours is None or max_hours >= duration:
            score += 20

    # Описание
    description = contractor.get("description", "")

    if len(description) >= 150:
        score += 30
    elif len(description) >= 70:
        score += 20
    elif description:
        score += 10

    return score


def make_explanation(
    contractor,
    budget,
    event_type,
    duration,
    language
):
    reasons = []

    price = contractor.get("price_from_kzt")

    if price is not None:
        saving = budget - price

        if saving > 0:
            reasons.append(
                f"Укладывается в бюджет с запасом "
                f"{saving:,} ₸".replace(",", " ")
            )

    if has_value(
        contractor.get("event_formats", []),
        event_type
    ):
        reasons.append(f"работает с форматом «{event_type}»")

    if language and has_value(
        contractor.get("languages", []),
        language
    ):
        reasons.append(f"работает на языке «{language}»")

    max_hours = contractor.get("max_hours")

    if duration is not None and max_hours is not None:
        reasons.append(
            f"может работать до {max_hours} ч."
        )

    # Берём разные конкретные причины
    return ". ".join(reasons[:3]) + "." 