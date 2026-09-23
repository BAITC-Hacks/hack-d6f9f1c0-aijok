"""Flask entry point for EventMatch AI."""

from pathlib import Path

from flask import Flask, render_template, request

from services.recommender import (
    ALLOWED_CITIES,
    ALLOWED_FORMATS,
    ALLOWED_LANGUAGES,
    DATE_MAX,
    DATE_MIN,
    categories_from,
    load_contractors,
    recommend,
    validate_request,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "hackathon-dataset-anonymized.csv"

app = Flask(__name__)
contractors = load_contractors(DATA_PATH)
categories = categories_from(contractors)


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None
    form = request.form.to_dict() if request.method == "POST" else {}
    if request.method == "POST":
        try:
            query = validate_request(form, categories)
            result = recommend(contractors, query)
        except ValueError as exc:
            error = str(exc)
    return render_template(
        "index.html",
        cities=ALLOWED_CITIES,
        event_formats=ALLOWED_FORMATS,
        languages=ALLOWED_LANGUAGES,
        categories=categories,
        date_min=DATE_MIN.isoformat(),
        date_max=DATE_MAX.isoformat(),
        form=form,
        result=result,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)
