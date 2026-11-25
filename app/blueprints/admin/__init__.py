"""The admin area (/admin): manage cities, hospitals and labs, specialists, facilities, users and appointments."""
from flask import Blueprint, flash, redirect, render_template, url_for

from ...extensions import db
from ...services import stats
from ...utils import back_to
from ...utils.auth import admin_required

bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.before_request
@admin_required
def admins_only():
    """Every page here needs a logged-in admin."""


@bp.get('/')
def dashboard():
    return render_template('admin/dashboard.html', **stats.admin_overview())


def save(form, record, label, endpoint):
    """Store a submitted add or edit form and go back to the list. Returns None when the form has to be
    shown: on first display, or again with its error messages."""
    if not form.validate_on_submit():
        return None
    is_new = record.id is None
    form.populate_obj(record)
    db.session.add(record)
    db.session.commit()
    flash(f'{label} {"added" if is_new else "updated"}.', 'success')
    return redirect(url_for(endpoint))


def delete(record, label, endpoint, blocked_by=None):
    """Delete a record and go back to the list; `blocked_by` is the reason why it must stay, if any."""
    if blocked_by:
        flash(blocked_by, 'danger')
    else:
        db.session.delete(record)
        db.session.commit()
        flash(f'{label} deleted.', 'success')
    return redirect(back_to(url_for(endpoint)))


def upcoming_note(count, what):
    """The reason a record with upcoming appointments cannot be deleted (None when it has none)."""
    if not count:
        return None
    booked = '1 upcoming appointment' if count == 1 else f'{count} upcoming appointments'
    return f'{what} has {booked}. Cancel or reschedule them first.'


from . import appointments, cities, doctors, facilities, hospitals, users  # noqa: E402,F401  (register the pages)
