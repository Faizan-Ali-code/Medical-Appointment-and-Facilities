"""Booking a doctor / facility, and the user's own bookings."""
import datetime

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..extensions import db
from ..models import Doctor, DoctorBooking, Facility, FacilityBooking
from ..services import bookings as booking_service
from ..services import catalog
from ..services.bookings import BookingError
from ..utils.auth import login_required
from ..utils.uploads import IMAGES_AND_PDF, UploadError, save_upload

bp = Blueprint('bookings', __name__)


def _can_book():
    """Only logged-in normal users can book. Returns a redirect response if not allowed."""
    if g.user is None:
        flash('Please login first.', 'warning')
        return redirect(url_for('auth.login'))
    if g.user.is_admin:
        flash('Please Login As User before Booking', 'warning')
        return redirect(request.path)
    return None


@bp.route('/book_doctor/<int:id>', methods=['GET', 'POST'])
def book_doctor(id):
    doctor = db.get_or_404(Doctor, id)
    if request.method == 'POST':
        denied = _can_book()
        if denied:
            return denied
        try:
            date = booking_service.parse_date(request.form.get('date'))
            booking_service.book_doctor(g.user, doctor, date, request.form.get('slot', '').strip())
            flash('Booking Successful', 'success')
        except BookingError as e:
            flash(str(e), 'danger')
        return redirect(url_for('bookings.book_doctor', id=id))
    return render_template('bookings/book_doctor.html', doctor=doctor, today=datetime.date.today())


@bp.route('/book_facilities/<int:id>', methods=['GET', 'POST'])
def book_facility(id):
    facility = db.get_or_404(Facility, id)
    if request.method == 'POST':
        denied = _can_book()
        if denied:
            return denied
        service = request.form.get('service', '').strip()
        try:
            booking_service.check_facility_booking(g.user, facility, service)  # before saving the file
            image = save_upload(request.files.get('image'), allowed=IMAGES_AND_PDF)
            booking_service.book_facility(g.user, facility, service, image)
            flash('Service Booking Successful', 'success')
        except (BookingError, UploadError) as e:
            flash(str(e), 'danger')
        return redirect(url_for('bookings.book_facility', id=id))
    return render_template('bookings/book_facility.html', facility=facility, today=datetime.date.today())


def _own_booking(id):
    return db.first_or_404(db.select(DoctorBooking).filter_by(id=id, user_id=g.user.id))


@bp.route('/user_docbookings')
@login_required
def my_doctor_bookings():
    query = (db.select(DoctorBooking).filter_by(user_id=g.user.id)
             .order_by(DoctorBooking.date.desc(), DoctorBooking.id.desc()))
    return render_template('bookings/my_doctor_bookings.html', page=catalog.paginate(query))


@bp.route('/deluser_docbookings/<int:id>', methods=['POST'])
@login_required
def cancel_doctor_booking(id):
    """Cancel keeps the row (status = cancelled) so the history stays visible."""
    try:
        booking_service.cancel(_own_booking(id))
        flash('Booking cancelled', 'info')
    except BookingError as e:
        flash(str(e), 'danger')
    return redirect(url_for('bookings.my_doctor_bookings'))


@bp.route('/user_docbookings/<int:id>/reschedule', methods=['GET', 'POST'])
@login_required
def reschedule_doctor_booking(id):
    booking = _own_booking(id)
    if not booking.is_active:
        flash('Only upcoming booked appointments can be rescheduled', 'warning')
        return redirect(url_for('bookings.my_doctor_bookings'))
    if request.method == 'POST':
        try:
            date = booking_service.parse_date(request.form.get('date'))
            booking_service.reschedule(booking, date, request.form.get('slot', '').strip())
            flash('Appointment rescheduled', 'success')
            return redirect(url_for('bookings.my_doctor_bookings'))
        except BookingError as e:
            flash(str(e), 'danger')
    return render_template('bookings/reschedule.html', booking=booking, doctor=booking.doctor,
                           today=datetime.date.today())


@bp.route('/user_facbookings')
@login_required
def my_facility_bookings():
    query = (db.select(FacilityBooking).filter_by(user_id=g.user.id)
             .order_by(FacilityBooking.date.desc(), FacilityBooking.id.desc()))
    return render_template('bookings/my_facility_bookings.html', page=catalog.paginate(query))
