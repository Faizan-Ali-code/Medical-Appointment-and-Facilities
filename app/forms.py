"""Forms: each class lists the fields of one page and the rules its values must pass."""
from flask import g
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from sqlalchemy import func
from werkzeug.datastructures import FileStorage
from wtforms import (IntegerField, PasswordField, SelectField, SelectMultipleField, StringField, TextAreaField,
                     TimeField)
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, Regexp, ValidationError
from wtforms.widgets import CheckboxInput, ListWidget

from .extensions import db
from .models import WEEKDAYS, City, Doctor, Facility, Hospital, User
from .utils.uploads import IMAGE_EXTENSIONS, delete_image, save_image

SLOT_LENGTHS = (10, 15, 20, 30, 45, 60)
PASSWORD_LENGTH = Length(min=6, max=64, message='Password must be 6 to 64 characters long.')
EMAIL = Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', message='Enter a valid email address.')
PHONE = Regexp(r'^[0-9+()\-\s]{7,20}$', message='Enter a valid phone number.')


def strip(value):
    return value.strip() if isinstance(value, str) else value


def lower(value):
    return value.lower() if isinstance(value, str) else value


def optional_int(value):
    """Select values: '' (the "Choose..." option) becomes None, anything else a whole number."""
    return None if value in (None, '') else int(value)


def text(label, max_length, required=True, **kwargs):
    first = DataRequired(f'{label} is required.') if required else Optional()
    return StringField(label, [first, Length(max=max_length)], filters=[strip], **kwargs)


def choose(label, **kwargs):
    """A select whose first option is an empty "Choose..." entry; the choices are filled in when the form is built."""
    return SelectField(label, [DataRequired(f'Please choose a {label.lower()}.')], coerce=optional_int, **kwargs)


def city_choices(placeholder):
    cities = db.session.scalars(db.select(City).order_by(City.name))
    return [('', placeholder)] + [(city.id, city.name) for city in cities]


def hospital_choices():
    hospitals = db.session.scalars(db.select(Hospital).order_by(Hospital.name))
    return [('', 'Choose...')] + [(h.id, f'{h.name}, {h.city.name}') for h in hospitals]


class ImageField(FileField):
    """An optional picture. When no new file is chosen, the record keeps the picture it has."""

    def populate_obj(self, obj, name):
        if isinstance(self.data, FileStorage):
            delete_image(getattr(obj, name))
            setattr(obj, name, save_image(self.data))


def picture(label):
    allowed = FileAllowed(IMAGE_EXTENSIONS, 'Please upload a picture (PNG, JPG, GIF or WebP).')
    return ImageField(label, [allowed])


class RecordForm(FlaskForm):
    """A form that adds or edits one database row (`record`)."""

    def __init__(self, record, **kwargs):
        super().__init__(obj=record, **kwargs)
        self.record = record

    def taken(self, model, **values):
        """True when another row of `model` already has these values (text is compared without case)."""
        query = db.select(model.id)
        for name, value in values.items():
            column = getattr(model, name)
            query = query.where(func.lower(column) == value.lower() if isinstance(value, str) else column == value)
        if self.record.id is not None:
            query = query.where(model.id != self.record.id)
        return db.session.scalar(query) is not None


# ---------------------------------------------------------------- accounts

class LoginForm(FlaskForm):
    email = StringField('Email', [DataRequired('Email is required.')], filters=[strip, lower])
    password = PasswordField('Password', [DataRequired('Password is required.')])


class RegisterForm(RecordForm):
    name = text('Full name', 80)
    email = StringField('Email', [DataRequired('Email is required.'), EMAIL, Length(max=120)], filters=[strip, lower])
    password = PasswordField('Password', [DataRequired('Password is required.'), PASSWORD_LENGTH])
    phone = StringField('Phone', [DataRequired('Phone is required.'), PHONE], filters=[strip])
    city_id = SelectField('City', [Optional()], coerce=optional_int)

    def __init__(self, record, **kwargs):
        super().__init__(record, **kwargs)
        self.city_id.choices = city_choices('Select your city')

    def validate_email(self, field):
        if self.taken(User, email=field.data):
            raise ValidationError('An account with this email already exists.')


class UserForm(RegisterForm):
    """Admin: add or edit any account, including other admins."""
    role = SelectField('Role', choices=[(User.USER, 'User'), (User.ADMIN, 'Admin')])

    def __init__(self, record, **kwargs):
        super().__init__(record, **kwargs)
        if record.id is not None:   # editing: an empty password keeps the current one
            self.password.validators = [Optional(), PASSWORD_LENGTH]
            self.password.flags.required = False

    def validate_role(self, field):
        if self.record.id is not None and self.record.id == g.user.id and field.data != User.ADMIN:
            raise ValidationError('You cannot remove the admin role from your own account.')

    def populate_obj(self, obj):
        for name, field in self._fields.items():
            if name != 'password' or field.data:
                field.populate_obj(obj, name)


# ---------------------------------------------------------------- admin data

class CityForm(RecordForm):
    name = text('City name', 60)

    def validate_name(self, field):
        if self.taken(City, name=field.data):
            raise ValidationError('This city already exists.')


class HospitalForm(RecordForm):
    name = text('Name', 120)
    kind = SelectField('Type', choices=[(kind, kind) for kind in Hospital.KINDS])
    city_id = choose('City')
    address = text('Address', 200)
    phone = StringField('Phone', [DataRequired('Phone is required.'), PHONE], filters=[strip])
    timings = text('Timings', 80)
    description = TextAreaField('About and other facilities', [Length(max=2000)], filters=[strip])
    image = picture('Picture')

    def __init__(self, record, **kwargs):
        super().__init__(record, **kwargs)
        self.city_id.choices = city_choices('Choose...')

    def validate_name(self, field):
        if self.city_id.data and self.taken(Hospital, name=field.data, city_id=self.city_id.data):
            raise ValidationError('A hospital, clinic or lab with this name already exists in that city.')


class ScheduleForm(RecordForm):
    """Fields shared by doctors and facilities: where, how much, and on which days and hours."""
    hospital_id = choose('Hospital')
    fee = IntegerField('Fee (Rs.)', [InputRequired('Fee is required.'),
                                     NumberRange(min=0, max=1000000, message='Enter a fee from 0 to 1,000,000.')])
    day_list = SelectMultipleField('Working days', [DataRequired('Choose at least one working day.')],
                                   choices=[(day, day) for day in WEEKDAYS],
                                   widget=ListWidget(prefix_label=False), option_widget=CheckboxInput())
    start_time = TimeField('From', [InputRequired('Start time is required.')])
    end_time = TimeField('To', [InputRequired('End time is required.')])
    slot_minutes = SelectField('Slot length', coerce=int,
                               choices=[(minutes, f'{minutes} minutes') for minutes in SLOT_LENGTHS])

    def __init__(self, record, **kwargs):
        super().__init__(record, **kwargs)
        self.hospital_id.choices = hospital_choices()

    def validate_end_time(self, field):
        start, end = self.start_time.data, field.data
        if start and end:
            minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
            if minutes <= 0:
                raise ValidationError('The end time must be after the start time.')
            if minutes < (self.slot_minutes.data or 0):
                raise ValidationError('The working hours are shorter than one slot.')


class DoctorForm(ScheduleForm):
    name = text('Name', 80)
    specialization = text('Specialization', 60)
    qualification = text('Qualification', 120)
    description = TextAreaField('About', [Length(max=2000)], filters=[strip])
    image = picture('Photo')

    def validate_name(self, field):
        if self.hospital_id.data and self.taken(Doctor, name=field.data, hospital_id=self.hospital_id.data):
            raise ValidationError('This doctor is already listed at that hospital.')


class FacilityForm(ScheduleForm):
    name = text('Facility name', 80)
    category = SelectField('Department', choices=[(category, category) for category in Facility.CATEGORIES])
    description = TextAreaField('Details and preparation', [Length(max=2000)], filters=[strip])

    def validate_name(self, field):
        if self.hospital_id.data and self.taken(Facility, name=field.data, hospital_id=self.hospital_id.data):
            raise ValidationError('That hospital or lab already offers a facility with this name.')


class ResultForm(FlaskForm):
    result = TextAreaField('Test result', [DataRequired('Please enter the result.'), Length(max=2000)],
                           filters=[strip])
