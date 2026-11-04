"""Counts and short lists for the home page, the admin dashboard and the user's account page."""
import datetime

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import Doctor, DoctorBooking, Facility, FacilityBooking, Hospital, User


def _count(model, *where):
    return db.session.scalar(db.select(func.count()).select_from(model).where(*where))


def public_counts():
    return {'hospitals': _count(Hospital), 'doctors': _count(Doctor), 'facilities': _count(Facility)}


def _is_upcoming():
    return (DoctorBooking.date >= datetime.date.today()) & (DoctorBooking.status == DoctorBooking.BOOKED)


def _upcoming(*where, limit):
    query = (db.select(DoctorBooking)
             .options(selectinload(DoctorBooking.doctor).selectinload(Doctor.hospital),
                      selectinload(DoctorBooking.user))
             .where(_is_upcoming(), *where)
             .order_by(DoctorBooking.date, DoctorBooking.slot)
             .limit(limit))
    return db.session.scalars(query).all()


def admin_overview(limit=8):
    pending = FacilityBooking.status == FacilityBooking.STATUS_PENDING
    return {
        'counts': {
            **public_counts(),
            'users': _count(User, User.role == 'user'),
            'upcoming': _count(DoctorBooking, _is_upcoming()),
            'pending_tests': _count(FacilityBooking, pending),
        },
        'upcoming': _upcoming(limit=limit),
        'pending_tests': db.session.scalars(
            db.select(FacilityBooking)
            .options(selectinload(FacilityBooking.facility), selectinload(FacilityBooking.user))
            .where(pending).order_by(FacilityBooking.date.desc()).limit(limit)).all(),
    }


def user_overview(user, limit=5):
    return {
        'upcoming': _upcoming(DoctorBooking.user_id == user.id, limit=limit),
        'recent_tests': db.session.scalars(
            db.select(FacilityBooking).options(selectinload(FacilityBooking.facility))
            .where(FacilityBooking.user_id == user.id)
            .order_by(FacilityBooking.date.desc(), FacilityBooking.id.desc()).limit(limit)).all(),
    }
