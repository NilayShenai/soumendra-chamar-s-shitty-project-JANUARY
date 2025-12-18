from functools import wraps
from typing import Callable, Any
from flask import g, redirect, session, url_for, flash

from .models import User


def load_current_user() -> None:
    user_id = session.get("user_id")
    g.user = User.query.get(user_id) if user_id else None


def login_required(view: Callable[..., Any]):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.get("user") is None:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view
