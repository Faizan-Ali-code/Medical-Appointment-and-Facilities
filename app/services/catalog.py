"""
Search and filter queries for cities, hospitals, doctors, facilities and users.

Each function returns a SELECT; views pass it to `utils.paginate()` or run it directly.
"""
from sqlalchemy import func, or_
from sqlalchemy.orm import contains_eager, selectinload

from ..extensions import db
from ..models import City, Doctor, Facility, Hospital, User


def contains(column, term):
    """Case-insensitive "contains" match; % and _ typed by the user are matched literally."""
    escaped = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return column.ilike(f'%{escaped}%', escape='\\')


def any_contains(term, *columns):
    return or_(*(contains(column, term) for column in columns))


def count(query):
    """How many rows a SELECT returns."""
    return db.session.scalar(db.select(func.count()).select_from(query.order_by(None).subquery()))


def cities(term=''):
    query = db.select(City).options(selectinload(City.hospitals)).order_by(City.name)
    return query.where(contains(City.name, term)) if term else query


def city_list():
    return db.session.scalars(db.select(City).order_by(City.name)).all()


def hospitals(term='', city_id=None, kind=''):
    """Hospitals, clinics and labs. `term` matches the name, the address, the type or the city."""
    query = (db.select(Hospital).join(Hospital.city)
             .options(contains_eager(Hospital.city), selectinload(Hospital.doctors),
                      selectinload(Hospital.facilities)))
    if term:
        query = query.where(any_contains(term, Hospital.name, Hospital.address, Hospital.kind, City.name))
    if city_id:
        query = query.where(Hospital.city_id == city_id)
    if kind:
        query = query.where(Hospital.kind == kind)
    return query.order_by(Hospital.name)


def hospital_list():
    return db.session.scalars(db.select(Hospital).order_by(Hospital.name)).all()


def _offered(model, city_id, hospital_id):
    """SELECT of doctors or facilities together with their hospital and city, narrowed to one city or hospital."""
    query = (db.select(model).join(model.hospital).join(Hospital.city)
             .options(contains_eager(model.hospital).contains_eager(Hospital.city)))
    if city_id:
        query = query.where(Hospital.city_id == city_id)
    if hospital_id:
        query = query.where(model.hospital_id == hospital_id)
    return query.order_by(model.name, model.id)


def doctors(term='', city_id=None, specialization='', hospital_id=None):
    """`term` matches the doctor's name, the specialization, the hospital or the city."""
    query = _offered(Doctor, city_id, hospital_id)
    if term:
        query = query.where(any_contains(term, Doctor.name, Doctor.specialization, Hospital.name, City.name))
    if specialization:
        query = query.where(func.lower(Doctor.specialization) == specialization.lower())
    return query


def specializations():
    return db.session.scalars(db.select(Doctor.specialization).distinct().order_by(Doctor.specialization)).all()


def facilities(term='', city_id=None, category='', hospital_id=None):
    """`term` matches the facility's name, its department, the hospital or the city."""
    query = _offered(Facility, city_id, hospital_id)
    if term:
        query = query.where(any_contains(term, Facility.name, Facility.category, Hospital.name, City.name))
    if category:
        query = query.where(Facility.category == category)
    return query


def users(term='', role=''):
    query = db.select(User).options(selectinload(User.city))
    if term:
        query = query.where(any_contains(term, User.name, User.email, User.phone))
    if role:
        query = query.where(User.role == role)
    return query.order_by(User.name, User.id)
