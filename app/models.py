"""
Database models.

Table and column names are the same as in the project's original MySQL dump, so
an existing database imported from that dump works without changes; columns
added since then are listed in migrations.py.

Design notes (see docs/ARCHITECTURE.md):
* Doctor slots and facility services/fees stay comma-separated text, as in the
  original schema. The admin forms validate and normalise them, and bookings
  store the parsed start time (`starts_at`) so they sort and compare correctly.
* Hospitals, doctors, facilities and users are archived instead of deleted, so
  the bookings that refer to them survive. (An admin can still remove a single
  booking, e.g. one entered by mistake.)
* Double bookings are prevented by the database, not only by a check in Python:
  a unique constraint covers (doctor, date, slot, holds_slot). `holds_slot` is
  True while a booking occupies its slot and NULL once it is cancelled, and
  unique indexes treat NULLs as distinct in SQLite, MySQL and PostgreSQL.
"""
import datetime
import hmac

import sqlalchemy as sa
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .utils.timeslots import parse_slot, sort_key

# werkzeug hashes look like "scrypt:32768:8:1$salt$hash" or "pbkdf2:sha256:...$salt$hash"
_HASH_PREFIXES = ('scrypt:', 'pbkdf2:')


WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


def _split(value):
    """'a, b ,c' -> ['a', 'b', 'c']"""
    return [part.strip() for part in (value or '').split(',') if part.strip()]


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    city = db.Column(db.String(50))
    role = db.Column(db.String(50), default='user')
    archived = db.Column(db.Boolean, nullable=False, default=False, server_default='0')
    # bumped on logout and password change: every older session cookie stops working
    session_version = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    failed_logins = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    locked_until = db.Column(db.DateTime)

    doctor_bookings = db.relationship('DoctorBooking', back_populates='user', cascade='all, delete-orphan')
    facility_bookings = db.relationship('FacilityBooking', back_populates='user', cascade='all, delete-orphan')

    @property
    def is_admin(self):
        return self.role == 'admin'

    def is_locked(self, now=None):
        return self.locked_until is not None and self.locked_until > (now or datetime.datetime.now())

    def set_password(self, raw):
        self.password = generate_password_hash(raw, method=current_app.config['PASSWORD_HASH_METHOD'])

    @property
    def has_hashed_password(self):
        return (self.password or '').startswith(_HASH_PREFIXES)

    def check_password(self, raw):
        """
        True if `raw` is this user's password.
        Old rows (from the original MySQL dump) store plain text; they are accepted
        once and immediately re-saved as a hash (caller commits).
        """
        if not self.password or not raw:
            return False
        if self.has_hashed_password:
            return check_password_hash(self.password, raw)
        if hmac.compare_digest(self.password.encode(), raw.encode()):
            self.set_password(raw)
            return True
        return False


class Hospital(db.Model):
    __tablename__ = 'hospitals'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    city = db.Column(db.String(50))
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    archived = db.Column(db.Boolean, nullable=False, default=False, server_default='0')

    doctors = db.relationship('Doctor', back_populates='hospital', cascade='all, delete-orphan')
    facilities = db.relationship('Facility', back_populates='hospital', cascade='all, delete-orphan')

    def archive(self):
        """Hide the hospital with its doctors and facilities; their bookings stay."""
        self.archived = True
        for item in (*self.doctors, *self.facilities):
            item.archived = True


class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'))
    specialization = db.Column(db.String(255))
    fee = db.Column(db.String(50))
    slots = db.Column(db.String(255))
    description = db.Column(db.String(255))
    image = db.Column(db.String(255))
    days = db.Column(db.String(50), default='', server_default='')  # 'Mon,Wed,Fri'; empty = every day
    archived = db.Column(db.Boolean, nullable=False, default=False, server_default='0')

    hospital = db.relationship('Hospital', back_populates='doctors')
    bookings = db.relationship('DoctorBooking', back_populates='doctor', cascade='all, delete-orphan')

    @property
    def slot_list(self):
        """Slots in time-of-day order (stored text may be in any order)."""
        return sorted(_split(self.slots), key=sort_key)

    @property
    def day_list(self):
        """Working days in week order; all days when none are set."""
        chosen = set(_split(self.days))
        return [d for d in WEEKDAYS if d in chosen] or list(WEEKDAYS)

    @property
    def works_every_day(self):
        return len(self.day_list) == len(WEEKDAYS)

    def works_on(self, date):
        return WEEKDAYS[date.weekday()] in self.day_list

    @property
    def hospital_name(self):
        return self.hospital.name if self.hospital else 'Not Found'


class Facility(db.Model):
    __tablename__ = 'facilities'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'))
    name = db.Column(db.String(150))
    description = db.Column(db.String(255))
    services = db.Column(db.String(255))
    fee = db.Column(db.String(255))
    contact = db.Column(db.String(50))
    archived = db.Column(db.Boolean, nullable=False, default=False, server_default='0')

    hospital = db.relationship('Hospital', back_populates='facilities')
    bookings = db.relationship('FacilityBooking', back_populates='facility', cascade='all, delete-orphan')

    @property
    def service_list(self):
        return _split(self.services)

    @property
    def fee_list(self):
        return _split(self.fee)

    @property
    def service_fees(self):
        """[(service, fee), ...] — fee is '' when fewer fees than services were entered."""
        fees = self.fee_list
        return [(s, fees[i] if i < len(fees) else '') for i, s in enumerate(self.service_list)]

    @property
    def hospital_name(self):
        return self.hospital.name if self.hospital else 'Not Found'


class DoctorBooking(db.Model):
    __tablename__ = 'doctor_bookings'
    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'date', 'slot', 'holds_slot', name='uq_doctor_bookings_active_slot'),
    )

    BOOKED = 'booked'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    STATUSES = (BOOKED, COMPLETED, CANCELLED)

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date = db.Column(db.Date)
    slot = db.Column(db.String(100))
    status = db.Column(db.String(20), default=BOOKED, server_default=BOOKED)
    starts_at = db.Column(db.Time)  # parsed from `slot`, for ordering
    holds_slot = db.Column(db.Boolean, default=True)  # True while the slot is taken, NULL once cancelled

    doctor = db.relationship('Doctor', back_populates='bookings')
    user = db.relationship('User', back_populates='doctor_bookings')

    @property
    def status_label(self):
        return (self.status or self.BOOKED).title()

    @property
    def is_active(self):
        """Booked and not in the past: can still be cancelled or rescheduled."""
        return (self.status or self.BOOKED) == self.BOOKED and self.date >= datetime.date.today()


@sa.event.listens_for(DoctorBooking, 'before_insert')
@sa.event.listens_for(DoctorBooking, 'before_update')
def _keep_slot_columns_in_sync(_mapper, _connection, booking):
    """Every write path (services, admin, seed, demo data) keeps starts_at and holds_slot consistent."""
    booking.starts_at = parse_slot(booking.slot)
    booking.holds_slot = None if booking.status == DoctorBooking.CANCELLED else True


class FacilityBooking(db.Model):
    __tablename__ = 'facility_bookings'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'facility_id', 'service', 'open_request', name='uq_facility_bookings_open'),
    )

    STATUS_PENDING = 0
    STATUS_DONE = 1
    RESULT_MAX_LENGTH = 50

    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    service = db.Column(db.String(100))
    image = db.Column(db.String(255))
    date = db.Column(db.Date)
    result = db.Column(db.String(50), default='-', server_default='-')
    status = db.Column(db.Integer, default=STATUS_PENDING, server_default='0')
    open_request = db.Column(db.Boolean, default=True)  # True while waiting for a result, NULL once done

    facility = db.relationship('Facility', back_populates='bookings')
    user = db.relationship('User', back_populates='facility_bookings')

    @property
    def status_label(self):
        return 'Pending' if self.status == self.STATUS_PENDING else 'Result ready'


@sa.event.listens_for(FacilityBooking, 'before_insert')
@sa.event.listens_for(FacilityBooking, 'before_update')
def _keep_open_request_in_sync(_mapper, _connection, booking):
    booking.open_request = True if booking.status in (None, FacilityBooking.STATUS_PENDING) else None
