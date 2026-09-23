"""Flask entry point for EventMatch AI."""

from pathlib import Path

import os

from flask import Flask, flash, redirect, render_template, request, session, url_for

from services.auth import authenticate_user, create_user, init_db
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
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "eventmatch-demo-local-secret"),
    DATABASE=BASE_DIR / "instance" / "eventmatch.db",
)
init_db(app.config["DATABASE"])
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
            result["event_date_display"] = query["event_date"].strftime("%d.%m.%Y")
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


@app.route("/auth", methods=["GET", "POST"])
def auth():
    mode = request.form.get("mode", request.args.get("mode", "login"))
    if mode not in {"login", "register"}:
        mode = "login"
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        if mode == "register":
            name = request.form.get("name", "").strip()
            try:
                user = create_user(app.config["DATABASE"], name, identity, password)
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                session["user"] = {"id": user["id"], "name": user["name"]}
                flash("Регистрация завершена. Вы вошли в аккаунт.", "success")
                return redirect(url_for("index"))
        else:
            user = authenticate_user(app.config["DATABASE"], identity, password)
            if user is None:
                flash("Неверный email, телефон или пароль.", "error")
            else:
                session["user"] = {"id": user["id"], "name": user["name"]}
                flash("Вы вошли в аккаунт.", "success")
                return redirect(url_for("index"))
    return render_template("auth.html", mode=mode)


@app.post("/logout")
def logout():
    session.clear()
    flash("Вы вышли из аккаунта.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
