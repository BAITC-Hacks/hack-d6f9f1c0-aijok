"""Flask entry point for EventMatch AI."""

import os
import secrets
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

from services.auth import authenticate, get_user, init_database, register_user
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
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    DATABASE=BASE_DIR / "instance" / "eventmatch.db",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
init_database(app.config["DATABASE"])
contractors = load_contractors(DATA_PATH)
categories = categories_from(contractors)


@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    return {"current_user": get_user(app.config["DATABASE"], user_id) if user_id else None}


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


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            user_id = register_user(
                app.config["DATABASE"],
                request.form.get("name", ""),
                request.form.get("password", ""),
                request.form.get("email", ""),
                request.form.get("phone", ""),
            )
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            session.clear()
            session["user_id"] = user_id
            flash("Регистрация завершена. Добро пожаловать!", "success")
            return redirect(url_for("index"))
    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = authenticate(
            app.config["DATABASE"],
            request.form.get("identifier", ""),
            request.form.get("password", ""),
        )
        if user is None:
            flash("Неверный email, телефон или пароль.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Здравствуйте, {user['name']}!", "success")
            return redirect(url_for("index"))
    return render_template("auth.html", mode="login")


@app.post("/logout")
def logout():
    session.clear()
    flash("Вы вышли из аккаунта.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
