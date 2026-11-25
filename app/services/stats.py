"""Numbers and short lists for the home page, the admin dashboard and the user's account page."""
from sqlalchemy import func

from ..extensions import db
from ..models import Appointment, City, Doctor, Facility, Hospital, User
from ..utils import timeslots
from . import appointments


def _count(model, *criteria):
    return db.session.scalar(db.select(func.count(model.id)).where(*criteria))


def _soonest(query, limit):
    """The first `limit` appointments of a search, earliest first."""
    query = query.order_by(None).order_by(Appointment.date, Appointment.time, Appointment.id)
    return db.session.scalars(query.limit(limit)).all()


def site_counts():
    return {'cities': _count(City), 'hospitals': _count(Hospital), 'doctors': _count(Doctor),
            'facilities': _count(Facility)}


def _awaiting_result():
    """Filter: tests whose date has come but that have no result yet."""
    return (Appointment.facility_id.is_not(None), Appointment.status == Appointment.BOOKED,
            Appointment.date <= timeslots.today())


def admin_overview():
    counts = site_counts()
    counts.update(users=_count(User, User.role == User.USER),
                  upcoming=appointments.upcoming_count(),
                  awaiting=_count(Appointment, *_awaiting_result()))
    return {
        'counts': counts,
        'upcoming': _soonest(appointments.search(status='upcoming'), 6),
        'awaiting': _soonest(appointments.search().where(*_awaiting_result()), 6),
    }


def user_overview(user):
    mine = Appointment.user_id == user.id
    results = appointments.search(user=user, kind='test', status=Appointment.COMPLETED)
    return {
        'counts': {'upcoming': appointments.upcoming_count(mine),
                   'completed': _count(Appointment, mine, Appointment.status == Appointment.COMPLETED),
                   'results': _count(Appointment, mine, Appointment.result.is_not(None))},
        'upcoming': _soonest(appointments.search(user=user, status='upcoming'), 5),
        'results': db.session.scalars(results.where(Appointment.result.is_not(None)).limit(3)).all(),
    }
