import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from models import DailyEntry, User, db


SLOTS = [
    {
        "key": "early_morning",
        "label": "Early Morning",
        "range": "5-8am",
        "short": "5-8",
    },
    {"key": "morning", "label": "Morning", "range": "8-11am", "short": "8-11"},
    {"key": "midday", "label": "Midday", "range": "11am-2pm", "short": "11-2"},
    {
        "key": "afternoon",
        "label": "Afternoon",
        "range": "2-5pm",
        "short": "2-5",
    },
    {"key": "evening", "label": "Evening", "range": "5-8pm", "short": "5-8"},
    {"key": "night", "label": "Night", "range": "8-11pm", "short": "8-11"},
    {
        "key": "late_night",
        "label": "Late Night",
        "range": "11pm-2am",
        "short": "11-2",
    },
    {
        "key": "overnight",
        "label": "Overnight",
        "range": "2-5am",
        "short": "2-5",
    },
]

SLOT_KEYS = [slot["key"] for slot in SLOTS]
STATUSES = ["Free", "Maybe", "Busy"]
STATUS_WEIGHTS = {"Free": 1.0, "Maybe": 0.6, "Busy": 0.0}
TYPE_META = {
    "morning": {"label": "Morning Person", "icon": "&#9728;"},
    "night": {"label": "Night Owl", "icon": "&#9790;"},
}


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)
    db_path = os.path.join(app.instance_path, "best_time_chat.sqlite3")

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        SQLALCHEMY_DATABASE_URI="sqlite:///" + db_path.replace("\\", "/"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_template_helpers(app)
    register_cli(app)
    register_routes(app)

    return app


def register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Create SQLite tables."""
        db.create_all()
        print("Database initialized.")


def register_template_helpers(app):
    @app.context_processor
    def inject_globals():
        return {
            "current_user": get_current_user(),
            "slots": SLOTS,
            "statuses": STATUSES,
            "type_meta": TYPE_META,
            "today_iso": date.today().isoformat(),
        }

    @app.template_filter("friendly_date")
    def friendly_date(value):
        if not value:
            return ""
        return value.strftime("%a, %b %-d") if os.name != "nt" else value.strftime("%a, %b %#d")

    @app.template_filter("weekday_name")
    def weekday_name(value):
        if not value:
            return ""
        return value.strftime("%A")


def register_routes(app):
    @app.route("/")
    def index():
        if get_current_user():
            return redirect(url_for("daily_input"))
        return redirect(url_for("login"))

    @app.route("/setup", methods=["GET", "POST"])
    def setup():
        if User.query.count() >= 2:
            flash("Both friend profiles are already set up. Log in with your PIN.")
            return redirect(url_for("login"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            pin = request.form.get("pin", "").strip()
            user_type = request.form.get("user_type", "morning")

            if not username:
                flash("Pick a name for this friend profile.")
            elif User.query.filter_by(username=username).first():
                flash("That name is already taken. Try a slightly different one.")
            elif len(pin) < 4 or not pin.isdigit():
                flash("Use a numeric PIN with at least 4 digits.")
            elif user_type not in TYPE_META:
                flash("Choose Morning Person or Night Owl.")
            else:
                user = User(username=username, user_type=user_type)
                user.set_pin(pin)
                db.session.add(user)
                db.session.commit()
                session.clear()
                session["user_id"] = user.id
                flash("Profile created. You are logged in.")
                return redirect(url_for("daily_input"))

        return render_template(
            "setup.html",
            profile_count=User.query.count(),
            profile_limit=2,
        )

    @app.route("/login", methods=["GET", "POST"])
    def login():
        users = User.query.order_by(User.id).all()
        if not users:
            return redirect(url_for("setup"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            pin = request.form.get("pin", "").strip()
            user = User.query.filter_by(username=username).first()

            if user and user.check_pin(pin):
                session.clear()
                session["user_id"] = user.id
                flash("Welcome back.")
                return redirect(url_for("daily_input"))
            flash("That name and PIN did not match.")

        return render_template("login.html", users=users, can_setup=len(users) < 2)

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out.")
        return redirect(url_for("login"))

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        user = get_current_user()

        if request.method == "POST":
            user_type = request.form.get("user_type", user.user_type)
            new_pin = request.form.get("pin", "").strip()

            if user_type not in TYPE_META:
                flash("Choose Morning Person or Night Owl.")
            else:
                user.user_type = user_type
                if new_pin:
                    if len(new_pin) < 4 or not new_pin.isdigit():
                        flash("New PIN must be numeric and at least 4 digits.")
                        return render_template("profile.html", user=user)
                    user.set_pin(new_pin)
                db.session.commit()
                flash("Profile updated.")
                return redirect(url_for("daily_input"))

        return render_template("profile.html", user=user)

    @app.route("/day", methods=["GET", "POST"])
    @login_required
    def daily_input():
        user = get_current_user()
        selected_day = parse_day(request.values.get("date"))

        if request.method == "POST":
            for slot in SLOTS:
                status = request.form.get(f"status_{slot['key']}", "Maybe")
                energy = parse_energy(request.form.get(f"energy_{slot['key']}"))
                if status not in STATUSES:
                    status = "Maybe"
                save_entry(user, selected_day, slot["key"], status, energy)

            db.session.commit()
            flash("Today is saved.")
            return redirect(url_for("results", date=selected_day.isoformat()))

        entries = entries_for_user_day(user.id, selected_day)
        return render_template(
            "daily.html",
            selected_day=selected_day,
            entries=entries,
        )

    @app.route("/results")
    @login_required
    def results():
        selected_day = parse_day(request.args.get("date"))
        user = get_current_user()
        recommendation = calculate_best_times(selected_day)
        week = build_user_heatmap(user, selected_day)
        shared_history = build_shared_history(selected_day)
        insight = best_day_of_week_insight()

        return render_template(
            "results.html",
            selected_day=selected_day,
            recommendation=recommendation,
            week=week,
            shared_history=shared_history,
            insight=insight,
        )


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not get_current_user():
            flash("Log in first.")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def parse_day(value):
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        flash("That date did not look right, so today is selected.")
        return date.today()


def parse_energy(value):
    if value in (None, ""):
        return 3
    try:
        return min(5, max(1, int(value)))
    except ValueError:
        return 3


def save_entry(user, selected_day, slot_key, status, energy):
    entry = DailyEntry.query.filter_by(
        user_id=user.id,
        entry_date=selected_day,
        slot_key=slot_key,
    ).first()
    if not entry:
        entry = DailyEntry(user_id=user.id, entry_date=selected_day, slot_key=slot_key)
        db.session.add(entry)
    entry.status = status
    entry.energy = energy


def entries_for_user_day(user_id, selected_day):
    entries = DailyEntry.query.filter_by(user_id=user_id, entry_date=selected_day).all()
    return {entry.slot_key: entry for entry in entries}


def user_has_complete_day(user_id, selected_day):
    entries = entries_for_user_day(user_id, selected_day)
    return all(slot_key in entries for slot_key in SLOT_KEYS)


def calculate_best_times(selected_day):
    users = User.query.order_by(User.id).all()
    if len(users) < 2:
        return {
            "ready": False,
            "setup_needed": True,
            "waiting_users": [],
            "ranked": [],
            "top": [],
            "all_busy": False,
        }

    day_entries = {
        user.id: entries_for_user_day(user.id, selected_day)
        for user in users
    }
    waiting_users = [
        user for user in users if not all(slot_key in day_entries[user.id] for slot_key in SLOT_KEYS)
    ]

    if waiting_users:
        return {
            "ready": False,
            "setup_needed": False,
            "waiting_users": waiting_users,
            "ranked": [],
            "top": [],
            "all_busy": False,
        }

    ranked = []
    for slot in SLOTS:
        first = day_entries[users[0].id][slot["key"]]
        second = day_entries[users[1].id][slot["key"]]
        score = score_slot(first, second)
        ranked.append(
            {
                "slot": slot,
                "score": score,
                "first_status": first.status,
                "second_status": second.status,
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    positive = [item for item in ranked if item["score"] > 0]

    return {
        "ready": True,
        "setup_needed": False,
        "waiting_users": [],
        "ranked": ranked,
        "top": positive[:2],
        "all_busy": not positive,
    }


def score_slot(first_entry, second_entry):
    if first_entry.status == "Busy" or second_entry.status == "Busy":
        return 0
    first_score = first_entry.energy * STATUS_WEIGHTS[first_entry.status]
    second_score = second_entry.energy * STATUS_WEIGHTS[second_entry.status]
    return round((first_score + second_score) / 2, 2)


def build_user_heatmap(user, anchor_day):
    days = [anchor_day - timedelta(days=offset) for offset in range(6, -1, -1)]
    cells_by_slot = []

    for slot in SLOTS:
        cells = []
        for day_item in days:
            entry = DailyEntry.query.filter_by(
                user_id=user.id,
                entry_date=day_item,
                slot_key=slot["key"],
            ).first()
            cells.append(build_heat_cell(entry))
        cells_by_slot.append({"slot": slot, "cells": cells})

    return {"days": days, "rows": cells_by_slot}


def build_heat_cell(entry):
    if not entry:
        return {"label": "-", "title": "No entry", "class": "empty", "energy": None}
    if entry.status == "Busy":
        return {"label": "B", "title": "Busy", "class": "busy", "energy": entry.energy}
    if entry.status == "Maybe":
        return {
            "label": str(entry.energy),
            "title": f"Maybe, energy {entry.energy}",
            "class": f"maybe energy-{entry.energy}",
            "energy": entry.energy,
        }
    return {
        "label": str(entry.energy),
        "title": f"Free, energy {entry.energy}",
        "class": f"free energy-{entry.energy}",
        "energy": entry.energy,
    }


def build_shared_history(anchor_day):
    days = [anchor_day - timedelta(days=offset) for offset in range(6, -1, -1)]
    history = []

    for day_item in days:
        result = calculate_best_times(day_item)
        if result["setup_needed"]:
            summary = "Second profile needed"
            score = None
        elif not result["ready"]:
            names = ", ".join(user.username for user in result["waiting_users"])
            summary = f"Waiting on {names}"
            score = None
        elif result["all_busy"]:
            summary = "No overlap"
            score = 0
        else:
            labels = ", ".join(item["slot"]["label"] for item in result["top"])
            summary = labels
            score = result["top"][0]["score"]

        history.append({"day": day_item, "summary": summary, "score": score})

    return history


def best_day_of_week_insight():
    all_days = {
        entry.entry_date
        for entry in DailyEntry.query.with_entities(DailyEntry.entry_date).distinct()
    }
    grouped_scores = defaultdict(list)

    for day_item in sorted(all_days):
        result = calculate_best_times(day_item)
        if result["ready"] and result["top"]:
            grouped_scores[day_item.strftime("%A")].append(result["top"][0]["score"])

    if not grouped_scores:
        return None

    averages = {
        weekday: sum(scores) / len(scores)
        for weekday, scores in grouped_scores.items()
        if scores
    }
    if not averages:
        return None

    best_weekday = max(averages, key=averages.get)
    return {
        "weekday": best_weekday,
        "score": round(averages[best_weekday], 2),
        "count": len(grouped_scores[best_weekday]),
    }


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5050)
