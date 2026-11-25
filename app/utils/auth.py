"""Login session helpers and the decorators that protect pages by role."""
from functools import wraps

from flask import flash, g, redirect, request, session, url_for

from ..extensions import db
from ..models import User

SESSION_KEY = 'user_id'


def login_user(user):
    session.clear()
    session[SESSION_KEY] = user.id


def logout_user():
    session.clear()


def load_current_user():
    """Runs before every request: puts the logged-in user (or None) on g.user."""
    user_id = session.get(SESSION_KEY)
    g.user = db.session.get(User, user_id) if user_id else None
    if user_id and g.user is None:   # the account was deleted while logged in
        session.clear()


def home_endpoint(user):
    """Where a user lands after login: admins on the dashboard, everyone else on their account."""
    return 'admin.dashboard' if user.is_admin else 'account.overview'


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash('Please log in to continue.', 'warning')
            next_page = request.full_path.rstrip('?') if request.method == 'GET' else None
            return redirect(url_for('auth.login', next=next_page))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not g.user.is_admin:
            flash('That page is for administrators only.', 'danger')
            return redirect(url_for('account.overview'))
        return view(*args, **kwargs)
    return wrapped


def user_required(view):
    """For the pages of normal users (booking, My Appointments); admins work in the admin area instead."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user.is_admin:
            flash('Administrators manage appointments from the admin area.', 'info')
            return redirect(url_for('admin.appointments'))
        return view(*args, **kwargs)
    return wrapped
