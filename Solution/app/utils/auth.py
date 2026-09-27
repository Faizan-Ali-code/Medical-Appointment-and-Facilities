"""Session login helpers and route decorators."""
from functools import wraps

from flask import flash, g, redirect, session, url_for

from ..extensions import db
from ..models import User

SESSION_KEY = 'user_id'


def login_user(user):
    session.clear()
    session[SESSION_KEY] = user.id


def logout_user():
    session.clear()


def load_current_user():
    """before_app_request hook: put the logged-in user (or None) on g.user."""
    user_id = session.get(SESSION_KEY)
    g.user = db.session.get(User, user_id) if user_id else None
    if user_id and g.user is None:  # user was deleted
        session.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash('Please login first.', 'warning')
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not g.user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('account.account'))
        return view(*args, **kwargs)
    return wrapped
