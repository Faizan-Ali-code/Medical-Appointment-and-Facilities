"""
Appointment rules: free slots, booking, rescheduling, cancelling and completing.

Doctors and facilities are booked the same way, so every function takes a `subject`: a Doctor or a Facility.
"""
import datetime
from dataclasses import dataclass

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import Appointment, Doctor, Facility, User
from ..utils import timeslots
from .catalog import any_contains

SLOT_TAKEN = 'Sorry, that slot has just been booked. Please choose another one.'


class BookingError(Exception):
    """A booking rule was broken. The message is shown to the user."""


@dataclass(frozen=True)
class Slot:
    FREE, BOOKED, PASSED = 'free', 'booked', 'passed'

    time: datetime.time
    state: str

    @property
    def value(self):
        return self.time.strftime('%H:%M')

    @property
    def label(self):
        return timeslots.format_time(self.time)

    @property
    def is_free(self):
        return self.state == self.FREE


def _of(subject):
    """Filter: the appointments of this doctor or facility."""
    column = Appointment.doctor_id if isinstance(subject, Doctor) else Appointment.facility_id
    return column == subject.id


# ---------------------------------------------------------------- free slots

def next_working_day(subject):
    """The first day, starting today, on which `subject` still has a slot that has not started."""
    now = timeslots.now()
    day = now.date()
    for _ in range(8):
        if subject.works_on(day) and (day > now.date() or any(time > now.time() for time in subject.slots)):
            return day
        day += datetime.timedelta(days=1)
    return now.date()


def day_problem(subject, date):
    """Why nothing can be booked on `date`, or None when the day is open for booking."""
    if date is None:
        return 'Please choose a valid date.'
    if date < timeslots.today():
        return 'Please choose today or a later date.'
    if not subject.works_on(date):
        return f'{subject.name} is not available on {date:%A}s. Available: {subject.days_label}.'
    return None


def day_slots(subject, date, ignore=None):
    """Every slot of `subject` on `date` with its state. The slot of the appointment `ignore` counts as free
    (it is the one being rescheduled)."""
    query = db.select(Appointment.time).where(_of(subject), Appointment.date == date,
                                              Appointment.holds_slot.is_(True))
    if ignore is not None:
        query = query.where(Appointment.id != ignore.id)
    taken = set(db.session.scalars(query))
    now = timeslots.now()

    def state(time):
        if time in taken:
            return Slot.BOOKED
        return Slot.PASSED if datetime.datetime.combine(date, time) <= now else Slot.FREE

    return [Slot(time, state(time)) for time in subject.slots]


def day_view(subject, date_text=None, ignore=None):
    """Template values for the slot picker: the chosen date (default: the next working day), why that day
    cannot be booked (if so) and its slots."""
    date = timeslots.parse_date(date_text) if date_text else (ignore.date if ignore else next_working_day(subject))
    problem = day_problem(subject, date)
    return {'date': date, 'problem': problem, 'slots': [] if problem else day_slots(subject, date, ignore)}


def _require_free(subject, date, time, ignore=None):
    problem = day_problem(subject, date)
    if problem:
        raise BookingError(problem)
    slot = next((slot for slot in day_slots(subject, date, ignore) if slot.time == time), None)
    if slot is None:
        raise BookingError('Please choose one of the listed time slots.')
    if slot.state == Slot.PASSED:
        raise BookingError('That time has already passed. Please choose a later slot.')
    if slot.state == Slot.BOOKED:
        raise BookingError(SLOT_TAKEN)


def _save():
    """Commit. The unique constraint on (doctor or facility, date, time) is the final guard against two people
    booking the same slot at the same moment."""
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise BookingError(SLOT_TAKEN) from None


# ---------------------------------------------------------------- actions

def book(user, subject, date, time):
    _require_free(subject, date, time)
    appointment = Appointment(user=user, subject=subject, date=date, time=time)
    db.session.add(appointment)
    _save()
    return appointment


def _require_open(appointment, by_admin, action):
    if appointment.status != Appointment.BOOKED:
        raise BookingError(f'This appointment is already {appointment.status} and cannot be {action}.')
    if not by_admin and not appointment.is_upcoming:
        raise BookingError(f'This appointment has already started and cannot be {action}.')


def reschedule(appointment, date, time, by_admin=False):
    """Move a booked appointment to another free slot of the same doctor or facility."""
    _require_open(appointment, by_admin, 'rescheduled')
    if (date, time) == (appointment.date, appointment.time):
        raise BookingError('Please choose a different date or time.')
    _require_free(appointment.subject, date, time, ignore=appointment)
    appointment.date, appointment.time = date, time
    _save()


def cancel(appointment, by_admin=False):
    """Cancel a booked appointment, which frees its slot for others."""
    _require_open(appointment, by_admin, 'cancelled')
    appointment.status = Appointment.CANCELLED
    db.session.commit()


def complete(appointment, result=None):
    """Admin: mark an appointment as completed; for a test, store its result."""
    if appointment.status == Appointment.CANCELLED:
        raise BookingError('A cancelled appointment cannot be completed.')
    if appointment.date > timeslots.today():
        raise BookingError('An appointment cannot be completed before its date.')
    appointment.status = Appointment.COMPLETED
    if result is not None:
        appointment.result = result
    db.session.commit()


# ---------------------------------------------------------------- queries

def upcoming_count(*criteria):
    """How many booked appointments from today onwards match `criteria`. Records with such appointments
    (a user, doctor, facility or hospital) must not be deleted."""
    return db.session.scalar(db.select(func.count(Appointment.id)).where(
        Appointment.status == Appointment.BOOKED, Appointment.date >= timeslots.today(), *criteria))


def in_hospital(hospital):
    """Filter: appointments with a doctor or for a facility of this hospital."""
    return or_(Appointment.doctor.has(hospital_id=hospital.id), Appointment.facility.has(hospital_id=hospital.id))


def search(user=None, term='', kind='', status='', date=None):
    """SELECT of appointments, newest first. `kind` is 'doctor' or 'test'; `status` is one of
    Appointment.STATUSES or 'upcoming'; `term` matches the user's name, email or phone."""
    query = db.select(Appointment).options(
        selectinload(Appointment.user),
        selectinload(Appointment.doctor).selectinload(Doctor.hospital),
        selectinload(Appointment.facility).selectinload(Facility.hospital))
    if user is not None:
        query = query.where(Appointment.user_id == user.id)
    if term:
        query = query.join(Appointment.user).where(any_contains(term, User.name, User.email, User.phone))
    if kind == 'doctor':
        query = query.where(Appointment.doctor_id.is_not(None))
    elif kind == 'test':
        query = query.where(Appointment.facility_id.is_not(None))
    if status == 'upcoming':
        query = query.where(Appointment.status == Appointment.BOOKED, Appointment.date >= timeslots.today())
    elif status in Appointment.STATUSES:
        query = query.where(Appointment.status == status)
    if date is not None:
        query = query.where(Appointment.date == date)
    return query.order_by(Appointment.date.desc(), Appointment.time.desc(), Appointment.id.desc())
