"""Logged-in user's own account and profile settings."""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..extensions import db
from ..services import stats
from ..utils import form_values
from ..utils.auth import login_required
from .auth import password_problem

bp = Blueprint('account', __name__)

PROFILE_FIELDS = ('name', 'city', 'phone')


def update_profile(user):
    """
    Shared by the user's own settings page and the admin's user edit page. Returns True if saved.
    The password field is optional: leave it empty to keep the current password.
    """
    form = form_values(*PROFILE_FIELDS)
    new_password = request.form.get('password', '')
    if not all(form.values()):
        flash('Please Fill All The Fields', 'warning')
        return False
    if new_password:
        problem = password_problem(new_password)
        if problem:
            flash(problem, 'warning')
            return False
        user.set_password(new_password)
    for field, value in form.items():
        setattr(user, field, value)
    db.session.commit()
    return True


@bp.route('/account')
@login_required
def account():
    overview = None if g.user.is_admin else stats.user_overview(g.user)
    return render_template('account/account.html', user=g.user, overview=overview)


@bp.route('/setting', methods=['GET', 'POST'])
@login_required
def setting():
    if request.method == 'POST':
        if update_profile(g.user):
            flash('Congrats, Your Profile Is Updated', 'success')
            return redirect(url_for('account.setting'))
    return render_template('account/settings.html', user=g.user)
