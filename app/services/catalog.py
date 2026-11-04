"""
Queries for hospitals, doctors, facilities and users: search, filters, pagination.

The *_query() functions return a SELECT statement; views pass it to `paginate()`.
"""
from flask import request
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import Doctor, Facility, Hospital, User

CARDS_PER_PAGE = 9    # 3 x 3 grid
ROWS_PER_PAGE = 10


def _contains(column, term):
    return column.ilike(f'%{term}%')


def paginate(query, per_page=ROWS_PER_PAGE):
    """Paginate a SELECT using ?page=N from the request (out-of-range pages show the last page)."""
    page = request.args.get('page', 1, type=int)
    result = db.paginate(query, page=max(page, 1), per_page=per_page, error_out=False)
    if result.pages and page > result.pages:
        result = db.paginate(query, page=result.pages, per_page=per_page, error_out=False)
    return result


# ------------------------------------------------------------ hospitals

def hospitals_query(term='', city=''):
    query = db.select(Hospital).options(selectinload(Hospital.doctors), selectinload(Hospital.facilities))
    if term:
        query = query.where(or_(_contains(Hospital.name, term), _contains(Hospital.city, term)))
    if city:
        query = query.where(func.lower(func.trim(Hospital.city)) == city.strip().lower())
    return query.order_by(Hospital.name)


def cities():
    names = db.session.scalars(db.select(func.trim(Hospital.city)).distinct())
    return sorted({n for n in names if n}, key=str.lower)


def hospital_choices():
    return db.session.scalars(db.select(Hospital).order_by(Hospital.name)).all()


# ------------------------------------------------------------ doctors

def doctors_query(term='', specialization='', hospital_id=None):
    query = db.select(Doctor).options(selectinload(Doctor.hospital))
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
    names = db.session.scalars(db.select(func.trim(Doctor.specialization)).distinct())
    return sorted({n for n in names if n}, key=str.lower)


# ------------------------------------------------------------ facilities

def facilities_query(term='', hospital_id=None):
    query = db.select(Facility).options(selectinload(Facility.hospital))
    if term:
        query = query.where(or_(_contains(Facility.name, term),
                                _contains(Facility.services, term),
                                _contains(Facility.description, term)))
    if hospital_id:
        query = query.where(Facility.hospital_id == hospital_id)
    return query.order_by(Facility.name)


# ------------------------------------------------------------ users

def normal_users_query(term=''):
    query = db.select(User).where(User.role == 'user')
    if term:
        query = query.where(or_(_contains(User.name, term), User.email == term.lower(), User.city == term))
    return query.order_by(User.name)
