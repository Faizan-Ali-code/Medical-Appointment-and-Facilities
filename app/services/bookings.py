"""Booking rules for doctor appointments and facility (test) bookings.

The checks here give users a clear message. They are not what guarantees
consistency: two requests can pass a check at the same moment, so the database
has unique constraints (see models.py) and a violation found at commit time is
turned into the same BookingError.
"""
import datetime

from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import DoctorBooking, FacilityBooking
from ..utils.timeslots import has_passed

SLOT_TAKEN = 'Someone already booked on this date and slot with this doctor'
ALREADY_PENDING = 'You already booked the service with this facility, wait for result'


class BookingError(Exception):
    """Raised when a booking is not allowed. The message is shown to the user."""


def parse_date(value):
    try:
        return datetime.datetime.strptime(value or '', '%Y-%m-%d').date()
    except ValueError:
        raise BookingError('Please choose a valid date') from None


def _commit(conflict_message):
    """Commit; a unique-constraint violation (lost race) becomes a BookingError."""
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise BookingError(conflict_message) from None


# ------------------------------------------------------------ doctor appointments

def _slot_holder(doctor, date, slot, exclude_id=None):
    """The active (not cancelled) booking holding this slot, if any."""
    query = db.select(DoctorBooking).where(
        DoctorBooking.doctor_id == doctor.id, DoctorBooking.date == date, DoctorBooking.slot == slot,
        DoctorBooking.status != DoctorBooking.CANCELLED)
    if exclude_id:
        query = query.where(DoctorBooking.id != exclude_id)
    return db.session.scalar(query)


def availability(doctor, date, exclude_id=None, now=None):
    """
    What can be booked with `doctor` on `date`:
    {'works': bool, 'past': bool, 'slots': [{'slot': '10:00 AM', 'free': True, 'passed': False}, ...]}
    """
    taken_query = db.select(DoctorBooking.slot).where(
        DoctorBooking.doctor_id == doctor.id, DoctorBooking.date == date,
        DoctorBooking.status != DoctorBooking.CANCELLED)
    if exclude_id:
        taken_query = taken_query.where(DoctorBooking.id != exclude_id)
    taken = set(db.session.scalars(taken_query))
    return {
        'works': doctor.works_on(date),
        'past': date < datetime.date.today(),
        'slots': [{'slot': s, 'free': s not in taken, 'passed': has_passed(date, s, now)} for s in doctor.slot_list],
    }


def _check_doctor_slot(user, doctor, date, slot, exclude_id=None):
    if date < datetime.date.today():
        raise BookingError('Please choose today or a future date')
    if not doctor.works_on(date):
        raise BookingError(f'{doctor.name} is not available on {date.strftime("%A")}s. '
                           f'Working days: {", ".join(doctor.day_list)}')
    if slot not in doctor.slot_list:
        raise BookingError('Please choose one of the available time slots')
    if has_passed(date, slot):
        raise BookingError('This time slot has already passed today. Please choose a later slot or another date')
    taken = _slot_holder(doctor, date, slot, exclude_id)
    if taken:
        if taken.user_id == user.id:
            raise BookingError('You already booked with this doctor on same date and slot')
        raise BookingError(SLOT_TAKEN)


def book_doctor(user, doctor, date, slot):
    _check_doctor_slot(user, doctor, date, slot)
    booking = DoctorBooking(doctor=doctor, user=user, date=date, slot=slot, status=DoctorBooking.BOOKED)
    db.session.add(booking)
    _commit(SLOT_TAKEN)
    return booking


def reschedule(booking, date, slot):
    if not booking.is_active:
        raise BookingError('Only upcoming booked appointments can be rescheduled')
    _check_doctor_slot(booking.user, booking.doctor, date, slot, exclude_id=booking.id)
    booking.date, booking.slot = date, slot
    _commit(SLOT_TAKEN)
    return booking


def cancel(booking):
    if not booking.is_active:
        raise BookingError('Only upcoming booked appointments can be cancelled')
    booking.status = DoctorBooking.CANCELLED
    db.session.commit()


def set_doctor_booking_status(booking, status):
    if status not in DoctorBooking.STATUSES:
        raise BookingError('Unknown status')
    booking.status = status
    _commit('This slot has been booked by someone else since the appointment was cancelled')


# ------------------------------------------------------------ facility (test) bookings

def book_facility(user, facility, service, image, date=None):
    date = date or datetime.date.today()
    check_facility_booking(user, facility, service)
    booking = FacilityBooking(facility=facility, user=user, date=date, service=service, image=image)
    db.session.add(booking)
    _commit(ALREADY_PENDING)
    return booking


def check_facility_booking(user, facility, service):
    """Raise BookingError if this facility booking is not allowed (run before saving any upload)."""
    if service not in facility.service_list:
        raise BookingError('Please choose one of the available services')
    pending = db.session.scalar(db.select(FacilityBooking).filter_by(
        user_id=user.id, facility_id=facility.id, service=service, status=FacilityBooking.STATUS_PENDING))
    if pending:
        raise BookingError(ALREADY_PENDING)


def set_result(booking, result):
    """Record the test result text (e.g. 'Normal', 'Positive', 'Hb 13.2 g/dL') and mark the booking done."""
    result = (result or '').strip()
    if not result:
        raise BookingError('Please enter a result')
    if len(result) > FacilityBooking.RESULT_MAX_LENGTH:
        raise BookingError(f'The result must be at most {FacilityBooking.RESULT_MAX_LENGTH} characters')
    booking.result = result
    booking.status = FacilityBooking.STATUS_DONE
    db.session.commit()
