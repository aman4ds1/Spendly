import re
import sqlite3
from datetime import date, datetime, timedelta

from flask import Flask, flash, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db, create_user, get_user_by_email
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key"

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

NAV_USERNAME = "Nitish Kumar"


@app.context_processor
def inject_nav_user():
    if session.get("user_id"):
        return {"nav_username": NAV_USERNAME}
    return {}


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    if "user_id" in session:
        return redirect(url_for("profile"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name:
        return render_template("register.html", error="Full name is required.", name=name, email=email)

    if not email or not EMAIL_PATTERN.match(email):
        return render_template("register.html", error="Please enter a valid email address.", name=name, email=email)

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.", name=name, email=email)

    try:
        user_id = create_user(name, email, generate_password_hash(password))
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with this email already exists.", name=name, email=email)

    session["user_id"] = user_id
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.", email=email)

    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # --- date-range validation ---
    raw_from = request.args.get("date_from", "").strip()
    raw_to = request.args.get("date_to", "").strip()
    date_from = date_to = None
    try:
        if raw_from:
            date_from = datetime.strptime(raw_from, "%Y-%m-%d").date()
        if raw_to:
            date_to = datetime.strptime(raw_to, "%Y-%m-%d").date()
    except ValueError:
        date_from = date_to = None

    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.", "error")
        date_from = date_to = None

    df_str = date_from.isoformat() if date_from else None
    dt_str = date_to.isoformat() if date_to else None

    # --- preset definitions (computed in Python, passed to template) ---
    today = date.today()
    presets = {
        "this_month": (today.replace(day=1).isoformat(), today.isoformat()),
        "last_3_months": ((today - timedelta(days=90)).isoformat(), today.isoformat()),
        "last_6_months": ((today - timedelta(days=180)).isoformat(), today.isoformat()),
        "all_time": (None, None),
    }

    active_preset = "all_time" if not df_str and not dt_str else None
    if active_preset is None:
        for preset_key, (pf, pt) in presets.items():
            if df_str == pf and dt_str == pt:
                active_preset = preset_key
                break

    # --- live data ---
    user = get_user_by_id(user_id)
    summary = get_summary_stats(user_id, df_str, dt_str)
    transactions = get_recent_transactions(user_id, date_from=df_str, date_to=dt_str)
    categories = get_category_breakdown(user_id, df_str, dt_str)

    return render_template(
        "profile.html",
        user=user,
        summary=summary,
        transactions=transactions,
        categories=categories,
        presets=presets,
        active_preset=active_preset,
        date_from=df_str,
        date_to=dt_str,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
