"""A user's own area: account overview, booking, and viewing, rescheduling or cancelling appointments."""
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ..extensions import db
from ..models import Appointment, Doctor, Facility
from ..services import appointments, stats
from ..services.appointments import BookingError
from ..utils import paginate, timeslots
from ..utils.auth import user_required
from . import shared

bp = Blueprint('account', __name__)


@bp.before_request
@user_required
def users_only():
    """Every page here needs a logged-in user."""


def _own(id):
    """The appointment, only if it belongs to the logged-in user."""
    appointment = db.get_or_404(Appointment, id)
    if appointment.user_id != g.user.id:
        abort(404)
    return appointment


@bp.get('/account')
def overview():
    return render_template('account/overview.html', **stats.user_overview(g.user))


# ---------------------------------------------------------------- booking

def _book(subject, endpoint):
    date, time = shared.chosen_slot()
    try:
        appointment = appointments.book(g.user, subject, date, time)
    except BookingError as error:
        flash(str(error), 'danger')
        return redirect(url_for(endpoint, id=subject.id, date=request.form.get('date')))
    flash(f'Booked: {subject.name} on {date:%A, %d %B %Y} at {timeslots.format_time(time)}.', 'success')
    return redirect(url_for('account.appointment', id=appointment.id))


@bp.post('/doctors/<int:id>/book')
def book_doctor(id):
    return _book(db.get_or_404(Doctor, id), 'public.doctor')


@bp.post('/facilities/<int:id>/book')
def book_facility(id):
    return _book(db.get_or_404(Facility, id), 'public.facility')


# ---------------------------------------------------------------- my appointments

@bp.get('/account/appointments')
def appointment_list():
    query = appointments.search(user=g.user, kind=request.args.get('type', ''),
                                status=request.args.get('status', ''))
    return render_template('account/appointments.html', page=paginate(query))


@bp.get('/account/appointments/<int:id>')
def appointment(id):
    return render_template('account/appointment.html', appointment=_own(id))


@bp.post('/account/appointments/<int:id>/cancel')
def cancel(id):
    return shared.cancel(_own(id), url_for('account.appointment', id=id))


@bp.route('/account/appointments/<int:id>/reschedule', methods=['GET', 'POST'])
def reschedule(id):
    return shared.reschedule(_own(id), url_for('account.appointment', id=id), 'layouts/base.html')
