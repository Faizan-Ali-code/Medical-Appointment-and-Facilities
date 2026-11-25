"""Steps that work the same for a user (own appointments) and for an admin (all appointments)."""
from flask import flash, redirect, render_template, request, url_for

from ..services import appointments
from ..services.appointments import BookingError
from ..utils import back_to, timeslots


def chosen_slot():
    """The date and time sent by the slot picker (None for anything that is not a date or time)."""
    return timeslots.parse_date(request.form.get('date')), timeslots.parse_time(request.form.get('time'))


def cancel(appointment, done_url, by_admin=False):
    try:
        appointments.cancel(appointment, by_admin=by_admin)
        flash('The appointment has been cancelled and its slot is free again.', 'success')
    except BookingError as error:
        flash(str(error), 'danger')
    return redirect(back_to(done_url))


def reschedule(appointment, done_url, layout, by_admin=False):
    """GET: the slot picker for another day or time. POST: move the appointment to the chosen slot."""
    if request.method == 'POST':
        try:
            appointments.reschedule(appointment, *chosen_slot(), by_admin=by_admin)
        except BookingError as error:
            flash(str(error), 'danger')
            return redirect(url_for(request.endpoint, id=appointment.id, date=request.form.get('date')))
        flash(f'The appointment has been moved to {appointment.date:%A, %d %B %Y} at '
              f'{timeslots.format_time(appointment.time)}.', 'success')
        return redirect(done_url)

    if appointment.status != appointment.BOOKED or not (by_admin or appointment.is_upcoming):
        flash('This appointment can no longer be rescheduled.', 'warning')
        return redirect(done_url)
    return render_template('appointments/reschedule.html', appointment=appointment, layout=layout,
                           done_url=done_url,
                           **appointments.day_view(appointment.subject, request.args.get('date'), appointment))
