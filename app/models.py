"""Database models: cities, users, hospitals (and clinics and labs), doctors, facilities and appointments."""
import datetime

import sqlalchemy as sa
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db
from .utils import timeslots

WEEKDAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


class City(db.Model):
    __tablename__ = 'cities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False, unique=True)

    hospitals = db.relationship('Hospital', back_populates='city', order_by='Hospital.name')
    users = db.relationship('User', back_populates='city')


class User(db.Model):
    __tablename__ = 'users'

    ADMIN, USER = 'admin', 'user'
    ROLES = (USER, ADMIN)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id', ondelete='SET NULL'))
    role = db.Column(db.String(10), nullable=False, default=USER)

    city = db.relationship('City', back_populates='users')
    appointments = db.relationship('Appointment', back_populates='user', cascade='all')

    @property
    def is_admin(self):
        return self.role == self.ADMIN

    @property
    def password(self):
        raise AttributeError('The password itself is never stored, only its hash.')

    @password.setter
    def password(self, value):
        self.password_hash = generate_password_hash(value)

    def check_password(self, value):
        return check_password_hash(self.password_hash, value)


class Hospital(db.Model):
    """A place that offers doctors and facilities: a hospital, a clinic or a laboratory."""
    __tablename__ = 'hospitals'
    __table_args__ = (db.UniqueConstraint('name', 'city_id', name='uq_hospital_name_city'),)

    HOSPITAL, CLINIC, LAB = 'Hospital', 'Clinic', 'Laboratory'
    KINDS = (HOSPITAL, CLINIC, LAB)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(20), nullable=False, default=HOSPITAL)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    timings = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    image = db.Column(db.String(100))

    city = db.relationship('City', back_populates='hospitals')
    doctors = db.relationship('Doctor', back_populates='hospital', cascade='all', order_by='Doctor.name')
    facilities = db.relationship('Facility', back_populates='hospital', cascade='all', order_by='Facility.name')


class Schedule:
    """Columns and helpers shared by everything that is booked in time slots: working days, hours, slot length."""

    days = db.Column(db.String(27), nullable=False, default=','.join(WEEKDAYS))
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    slot_minutes = db.Column(db.Integer, nullable=False, default=30)

    @property
    def day_list(self):
        chosen = (self.days or '').split(',')
        return [day for day in WEEKDAYS if day in chosen]

    @day_list.setter
    def day_list(self, value):
        self.days = ','.join(day for day in WEEKDAYS if day in value)

    @property
    def days_label(self):
        """'Every day', 'Mon – Fri' for a run of days, otherwise 'Mon, Wed, Fri'."""
        days = self.day_list
        if len(days) == len(WEEKDAYS):
            return 'Every day'
        first = WEEKDAYS.index(days[0]) if days else 0
        if len(days) > 2 and days == list(WEEKDAYS[first:first + len(days)]):
            return f'{days[0]} – {days[-1]}'
        return ', '.join(days)

    @property
    def hours_label(self):
        return f'{timeslots.format_time(self.start_time)} – {timeslots.format_time(self.end_time)}'

    @property
    def slots(self):
        return timeslots.make_slots(self.start_time, self.end_time, self.slot_minutes)

    def works_on(self, date):
        return WEEKDAYS[date.weekday()] in self.day_list


class Doctor(Schedule, db.Model):
    __tablename__ = 'doctors'
    __table_args__ = (db.UniqueConstraint('name', 'hospital_id', name='uq_doctor_name_hospital'),)

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    specialization = db.Column(db.String(60), nullable=False)
    qualification = db.Column(db.String(120), nullable=False)
    fee = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    image = db.Column(db.String(100))

    hospital = db.relationship('Hospital', back_populates='doctors')
    appointments = db.relationship('Appointment', back_populates='doctor', cascade='all')


class Facility(Schedule, db.Model):
    """A test, scan or other service offered by a hospital or lab."""
    __tablename__ = 'facilities'
    __table_args__ = (db.UniqueConstraint('name', 'hospital_id', name='uq_facility_name_hospital'),)

    PATHOLOGY, RADIOLOGY = 'Pathology & Paramedical', 'Radiology'
    CATEGORIES = (PATHOLOGY, RADIOLOGY)

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    fee = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False, default='')

    hospital = db.relationship('Hospital', back_populates='facilities')
    appointments = db.relationship('Appointment', back_populates='facility', cascade='all')


class Appointment(db.Model):
    """One booked slot of a user with a doctor or for a facility (exactly one of the two is set)."""
    __tablename__ = 'appointments'
    __table_args__ = (
        # One appointment per slot. `holds_slot` is NULL for cancelled appointments and unique constraints
        # ignore NULL, so a cancelled appointment frees its slot while its row stays in the history.
        db.UniqueConstraint('doctor_id', 'date', 'time', 'holds_slot', name='uq_appointment_doctor_slot'),
        db.UniqueConstraint('facility_id', 'date', 'time', 'holds_slot', name='uq_appointment_facility_slot'),
        db.CheckConstraint('(doctor_id IS NULL) <> (facility_id IS NULL)', name='ck_appointment_doctor_or_facility'),
    )

    BOOKED, COMPLETED, CANCELLED = 'booked', 'completed', 'cancelled'
    STATUSES = (BOOKED, COMPLETED, CANCELLED)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'))
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'))
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(10), nullable=False, default=BOOKED)
    result = db.Column(db.Text)
    holds_slot = db.Column(db.Boolean)   # kept in step with `status` by the listener below
    created_at = db.Column(db.DateTime, nullable=False, default=timeslots.now)

    user = db.relationship('User', back_populates='appointments')
    doctor = db.relationship('Doctor', back_populates='appointments')
    facility = db.relationship('Facility', back_populates='appointments')

    @property
    def subject(self):
        """What is booked: the doctor or the facility."""
        return self.doctor or self.facility

    @subject.setter
    def subject(self, value):
        if isinstance(value, Doctor):
            self.doctor = value
        else:
            self.facility = value

    @property
    def is_test(self):
        return self.facility_id is not None or self.facility is not None

    @property
    def hospital(self):
        return self.subject.hospital

    @property
    def starts_at(self):
        return datetime.datetime.combine(self.date, self.time)

    @property
    def is_upcoming(self):
        """Booked and not started yet: the only state in which a user can cancel or reschedule."""
        return self.status == self.BOOKED and self.starts_at > timeslots.now()


@sa.event.listens_for(Appointment, 'before_insert')
@sa.event.listens_for(Appointment, 'before_update')
def _free_slot_of_cancelled(_mapper, _connection, appointment):
    appointment.holds_slot = None if appointment.status == Appointment.CANCELLED else True
