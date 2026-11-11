"""
Queries for hospitals, doctors, facilities and users: search, filters, pagination.

The *_query() functions return a SELECT statement; views pass it to `paginate()`.
Archived rows (see models.py) are never listed.
"""
from flask import abort, request
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import Doctor, Facility, Hospital, User

CARDS_PER_PAGE = 9    # 3 x 3 grid
ROWS_PER_PAGE = 10


def _contains(column, term):
    """Case-insensitive substring match; % and _ typed by the user are matched literally."""
    escaped = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return column.ilike(f'%{escaped}%', escape='\\')


def paginate(query, per_page=ROWS_PER_PAGE):
    """Paginate a SELECT using ?page=N from the request (out-of-range pages show the last page)."""
    page = request.args.get('page', 1, type=int)
    result = db.paginate(query, page=max(page, 1), per_page=per_page, error_out=False)
    if result.pages and page > result.pages:
        result = db.paginate(query, page=result.pages, per_page=per_page, error_out=False)
    return result


def get_active_or_404(model, id):
    """The row, or 404 when it does not exist or is archived."""
    row = db.get_or_404(model, id)
    if row.archived:
        abort(404)
    return row


# ------------------------------------------------------------ hospitals

def hospitals_query(term='', city=''):
    query = (db.select(Hospital).where(Hospital.archived.is_(False))
             .options(selectinload(Hospital.doctors), selectinload(Hospital.facilities)))
    if term:
        query = query.where(or_(_contains(Hospital.name, term), _contains(Hospital.city, term)))
    if city:
        query = query.where(func.lower(func.trim(Hospital.city)) == city.strip().lower())
    return query.order_by(Hospital.name)


def cities():
    names = db.session.scalars(db.select(func.trim(Hospital.city)).where(Hospital.archived.is_(False)).distinct())
    return sorted({n for n in names if n}, key=str.lower)


def hospital_choices():
    return db.session.scalars(db.select(Hospital).where(Hospital.archived.is_(False)).order_by(Hospital.name)).all()


# ------------------------------------------------------------ doctors

def doctors_query(term='', specialization='', hospital_id=None):
    query = db.select(Doctor).where(Doctor.archived.is_(False)).options(selectinload(Doctor.hospital))
    if term:
        query = query.where(or_(_contains(Doctor.name, term),
                                _contains(Doctor.specialization, term),
                                _contains(Doctor.description, term)))
    if specialization:
        query = query.where(func.lower(func.trim(Doctor.specialization)) == specialization.strip().lower())
    if hospital_id:
        query = query.where(Doctor.hospital_id == hospital_id)
    return query.order_by(Doctor.name)


def specializations():
    names = db.session.scalars(db.select(func.trim(Doctor.specialization)).where(Doctor.archived.is_(False))
                               .distinct())
    return sorted({n for n in names if n}, key=str.lower)


# ------------------------------------------------------------ facilities

def facilities_query(term='', hospital_id=None):
    query = db.select(Facility).where(Facility.archived.is_(False)).options(selectinload(Facility.hospital))
    if term:
        query = query.where(or_(_contains(Facility.name, term),
                                _contains(Facility.services, term),
                                _contains(Facility.description, term)))
    if hospital_id:
        query = query.where(Facility.hospital_id == hospital_id)
    return query.order_by(Facility.name)


# ------------------------------------------------------------ users

def normal_users_query(term=''):
    query = db.select(User).where(User.role == 'user', User.archived.is_(False))
    if term:
        query = query.where(or_(_contains(User.name, term), User.email == term.lower(), User.city == term))
    return query.order_by(User.name)
