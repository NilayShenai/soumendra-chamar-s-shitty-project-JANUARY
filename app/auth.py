from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from .models import User
from .utils import load_current_user

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def load_user():
    load_current_user()


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session.clear()
            session["user_id"] = user.id
            flash("Welcome back!", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid credentials.", "danger")

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Signed out.", "info")
    return redirect(url_for("auth.login"))
