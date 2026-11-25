"""Admin: see every appointment; cancel, reschedule or complete it; enter test results."""
from flask import flash, redirect, render_template, request, url_for

from ...extensions import db
from ...forms import ResultForm
from ...models import Appointment
from ...services import appointments as service
from ...services.appointments import BookingError
from ...utils import back_to, paginate, search_term, timeslots
from .. import shared
from . import bp


def _list_url():
    return url_for('admin.appointments')


@bp.get('/appointments')
def appointments():
    query = service.search(term=search_term(), kind=request.args.get('type', ''),
                           status=request.args.get('status', ''),
                           date=timeslots.parse_date(request.args.get('date')))
    return render_template('admin/appointments.html', page=paginate(query))


@bp.post('/appointments/<int:id>/cancel')
def appointment_cancel(id):
    return shared.cancel(db.get_or_404(Appointment, id), _list_url(), by_admin=True)


@bp.route('/appointments/<int:id>/reschedule', methods=['GET', 'POST'])
def appointment_reschedule(id):
    return shared.reschedule(db.get_or_404(Appointment, id), _list_url(), 'layouts/admin.html', by_admin=True)


@bp.post('/appointments/<int:id>/complete')
def appointment_complete(id):
    """Mark a doctor's appointment as completed. Tests are completed by entering their result."""
    appointment = db.get_or_404(Appointment, id)
    if appointment.is_test:
        return redirect(url_for('admin.appointment_result', id=id))
    try:
        service.complete(appointment)
        flash('The appointment has been marked as completed.', 'success')
    except BookingError as error:
        flash(str(error), 'danger')
    return redirect(back_to(_list_url()))


@bp.route('/appointments/<int:id>/result', methods=['GET', 'POST'])
def appointment_result(id):
    """Enter or correct the result of a test; the user then sees it in their account."""
    appointment = db.get_or_404(Appointment, id)
    if not appointment.is_test:
        flash('Only tests and scans have a result.', 'warning')
        return redirect(_list_url())
    form = ResultForm(obj=appointment)
    if form.validate_on_submit():
        try:
            service.complete(appointment, form.result.data)
            flash('The result has been saved. The user can now see it in their account.', 'success')
            return redirect(_list_url())
        except BookingError as error:
            flash(str(error), 'danger')
    return render_template('admin/result_form.html', form=form, appointment=appointment)
