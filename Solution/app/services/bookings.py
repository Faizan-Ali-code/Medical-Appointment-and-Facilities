"""Booking rules for doctor appointments and facility (test) bookings."""
import datetime

from ..extensions import db
from ..models import DoctorBooking, FacilityBooking


class BookingError(Exception):
    """Raised when a booking is not allowed. The message is shown to the user."""


def parse_date(value):
    try:
        return datetime.datetime.strptime(value or '', '%Y-%m-%d').date()
    except ValueError:
        raise BookingError('Please choose a valid date') from None


# ------------------------------------------------------------ doctor appointments

def _slot_holder(doctor, date, slot, exclude_id=None):
    """The active (not cancelled) booking holding this slot, if any."""
    query = db.select(DoctorBooking).where(
        DoctorBooking.doctor_id == doctor.id, DoctorBooking.date == date, DoctorBooking.slot == slot,
        DoctorBooking.status != DoctorBooking.CANCELLED)
    if exclude_id:
        query = query.where(DoctorBooking.id != exclude_id)
    return db.session.scalar(query)


def availability(doctor, date, exclude_id=None):
    """
    What can be booked with `doctor` on `date`:
    {'works': bool, 'past': bool, 'slots': [{'slot': '10:00 AM', 'free': True}, ...]}
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
        'slots': [{'slot': s, 'free': s not in taken} for s in doctor.slot_list],
    }


def _check_doctor_slot(user, doctor, date, slot, exclude_id=None):
    if date < datetime.date.today():
        raise BookingError('Please choose today or a future date')
    if not doctor.works_on(date):
        raise BookingError(f'{doctor.name} is not available on {date.strftime("%A")}s. '
                           f'Working days: {", ".join(doctor.day_list)}')
    if slot not in doctor.slot_list:
        raise BookingError('Please choose one of the available time slots')
    taken = _slot_holder(doctor, date, slot, exclude_id)
    if taken:
        if taken.user_id == user.id:
            raise BookingError('You already booked with this doctor on same date and slot')
        raise BookingError('Someone already booked on this date and slot with this doctor')


def book_doctor(user, doctor, date, slot):
    _check_doctor_slot(user, doctor, date, slot)
    booking = DoctorBooking(doctor=doctor, user=user, date=date, slot=slot, status=DoctorBooking.BOOKED)
    db.session.add(booking)
    db.session.commit()
    return booking


def reschedule(booking, date, slot):
    if not booking.is_active:
        raise BookingError('Only upcoming booked appointments can be rescheduled')
    _check_doctor_slot(booking.user, booking.doctor, date, slot, exclude_id=booking.id)
    booking.date, booking.slot = date, slot
    db.session.commit()
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
    db.session.commit()


# ------------------------------------------------------------ facility (test) bookings

def book_facility(user, facility, service, image, date=None):
    date = date or datetime.date.today()
    check_facility_booking(user, facility, service)
    booking = FacilityBooking(facility=facility, user=user, date=date, service=service, image=image)
    db.session.add(booking)
    db.session.commit()
    return booking


def check_facility_booking(user, facility, service):
    """Raise BookingError if this facility booking is not allowed (run before saving any upload)."""
    if service not in facility.service_list:
        raise BookingError('Please choose one of the available services')
    pending = db.session.scalar(db.select(FacilityBooking).filter_by(
        user_id=user.id, facility_id=facility.id, service=service, status=FacilityBooking.STATUS_PENDING))
    if pending:
        raise BookingError('You already booked the service with this facility, wait for result')


def set_result(booking, result):
    booking.result = result
    booking.status = FacilityBooking.STATUS_DONE
    db.session.commit()
