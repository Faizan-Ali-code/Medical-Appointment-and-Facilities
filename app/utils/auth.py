"""Session login helpers and route decorators.

Flask keeps the session in a signed cookie, so clearing it on logout only removes the browser's copy; a copied
cookie would stay valid. Each session therefore carries the user's `session_version`, and logout or a password
change increments it, which invalidates every older cookie. Sessions also expire after PERMANENT_SESSION_LIFETIME
of inactivity (the cookie is refreshed on every request) and SESSION_ABSOLUTE_HOURS after login.
"""
import time
from functools import wraps

from flask import current_app, flash, g, redirect, session, url_for

from ..extensions import db
from ..models import User

SESSION_KEY = 'user_id'
VERSION_KEY = 'session_version'
LOGIN_AT_KEY = 'login_at'


def login_user(user):
    session.clear()
    session.permanent = True
    session[SESSION_KEY] = user.id
    session[VERSION_KEY] = user.session_version
    session[LOGIN_AT_KEY] = int(time.time())


def end_all_sessions(user):
    """Invalidate every existing session cookie of `user` (caller commits)."""
    user.session_version = (user.session_version or 0) + 1


def logout_user():
    if g.get('user') is not None:
        end_all_sessions(g.user)
        db.session.commit()
    session.clear()


def _session_is_valid(user):
    if user is None or user.archived or session.get(VERSION_KEY) != user.session_version:
        return False
    max_age = current_app.config['SESSION_ABSOLUTE_HOURS'] * 3600
    return time.time() - session.get(LOGIN_AT_KEY, 0) <= max_age


def load_current_user():
    """before_app_request hook: put the logged-in user (or None) on g.user."""
    user_id = session.get(SESSION_KEY)
    user = db.session.get(User, user_id) if user_id else None
    if user_id and not _session_is_valid(user):  # deleted, archived, logged out elsewhere or expired
        session.clear()
        user = None
    g.user = user


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
