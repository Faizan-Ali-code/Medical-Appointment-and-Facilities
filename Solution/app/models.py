"""
Database models.

Table and column names are the same as in medicalappointmentsfinal.sql, so an
existing MySQL database imported from that dump works without changes.
"""
import datetime
import hmac

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

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
    email = db.Column(db.String(150), index=True)
    password = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    city = db.Column(db.String(50))
    role = db.Column(db.String(50), default='user')

    doctor_bookings = db.relationship('DoctorBooking', back_populates='user', cascade='all, delete-orphan')
    facility_bookings = db.relationship('FacilityBooking', back_populates='user', cascade='all, delete-orphan')

    @property
    def is_admin(self):
        return self.role == 'admin'

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

    doctors = db.relationship('Doctor', back_populates='hospital', cascade='all, delete-orphan')
    facilities = db.relationship('Facility', back_populates='hospital', cascade='all, delete-orphan')


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

    hospital = db.relationship('Hospital', back_populates='doctors')
    bookings = db.relationship('DoctorBooking', back_populates='doctor', cascade='all, delete-orphan')

    @property
    def slot_list(self):
        return _split(self.slots)

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

    doctor = db.relationship('Doctor', back_populates='bookings')
    user = db.relationship('User', back_populates='doctor_bookings')

    @property
    def status_label(self):
        return (self.status or self.BOOKED).title()

    @property
    def is_active(self):
        """Booked and not in the past: can still be cancelled or rescheduled."""
        return (self.status or self.BOOKED) == self.BOOKED and self.date >= datetime.date.today()


class FacilityBooking(db.Model):
    __tablename__ = 'facility_bookings'

    STATUS_PENDING = 0
    STATUS_DONE = 1

    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    service = db.Column(db.String(100))
    image = db.Column(db.String(255))
    date = db.Column(db.Date)
    result = db.Column(db.String(50), default='-', server_default='-')
    status = db.Column(db.Integer, default=STATUS_PENDING, server_default='0')

    facility = db.relationship('Facility', back_populates='bookings')
    user = db.relationship('User', back_populates='facility_bookings')

    @property
    def status_label(self):
        return 'Pending' if self.status == self.STATUS_PENDING else 'Approved'
