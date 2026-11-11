"""Create tables, load the sample data and the maintenance commands (flask --app run <command>).

The sample data keeps the ids and table layout of the project's original MySQL dump, but every name, address,
phone number and picture in it is fictional. Seeded accounts get random passwords (printed once by init-db),
so no known password ships with the app.
"""
import datetime
import os
import secrets
import shutil

import click
from flask import current_app

from .extensions import db
from .migrations import upgrade_schema
from .models import Doctor, DoctorBooking, Facility, FacilityBooking, Hospital, User
from .utils.passwords import password_problem

ADMIN_EMAIL = 'admin@yahoo.com'
USER_EMAIL = 'user@yahoo.com'


def _user(password, **fields):
    user = User(**fields)
    user.set_password(password)
    return user


def seed_passwords():
    """{email: password} for the seeded accounts: from the config, else random."""
    config = current_app.config
    return {ADMIN_EMAIL: config['SEED_ADMIN_PASSWORD'] or secrets.token_urlsafe(9),
            USER_EMAIL: config['SEED_USER_PASSWORD'] or secrets.token_urlsafe(9)}


def sample_data(passwords):
    return [
        Hospital(
            id=3, name='General Hospital', city='Lahore ',
            address='12 Hospital Road, Lahore (fictional address)',
            phone='042-0000-0003',
            description='A public teaching hospital with outpatient clinics, a diagnostic wing and 24-hour '
                        'emergency care. (Sample record: fictional hospital.)',
            image='sample-hospital.svg'),
        Doctor(
            id=3, name='Sadaf', hospital_id=3, specialization='MBBS ', fee='1600',
            slots='10:00 AM, 10:10 AM, 10:15 AM',
            description='MBBS, FCPS (Medicine), MRCP (UK, Royal College of Physicians); 11 years of experience. '
                        '(Sample record: fictional doctor.)',
            image='sample-doctor.svg'),
        Facility(
            id=3, hospital_id=3, name='Radiance Imaging Center',
            description='Radiology facility with experienced radiologists offering X-rays, ultrasound, CT and MRI. '
                        '(Sample record: fictional facility.)',
            services='X-rays, Ultrasound, CT Scan, MRI', fee='1500, 800, 2500, 3000', contact='0300-0000003'),
        _user(passwords[USER_EMAIL], id=1, name='User', email=USER_EMAIL, phone='0300-0000001',
              city='Islamabad', role='user'),
        _user(passwords[ADMIN_EMAIL], id=2, name='Salman', email=ADMIN_EMAIL, phone='0300-0000002',
              city='Gujranwala', role='admin'),
        DoctorBooking(id=1, doctor_id=3, user_id=1, date=datetime.date(2023, 8, 1), slot='10:00 AM'),
        FacilityBooking(id=1, facility_id=3, user_id=1, service='X-rays', image=None,
                        date=datetime.date(2023, 8, 1), result='-', status=0),
    ]


def init_db(reset=False):
    """Create tables; load sample data if the users table is empty. Needs an app context.

    Returns {email: password} of the seeded accounts, or {} when the database already had data.
    """
    if reset:
        db.drop_all()
    db.create_all()
    upgrade_schema()
    if db.session.query(User).count() == 0:
        passwords = seed_passwords()
        db.session.add_all(sample_data(passwords))
        db.session.commit()
        return passwords
    return {}


def secure_uploads():
    """Move patient files that older versions saved in the public images folder into the private folder.

    Files also used as a hospital or doctor picture stay where they are. Returns the number of files moved.
    """
    public, private = current_app.config['UPLOAD_FOLDER'], current_app.config['PRIVATE_UPLOAD_FOLDER']
    pictures = set(db.session.scalars(db.select(Hospital.image))) | set(db.session.scalars(db.select(Doctor.image)))
    moved = 0
    for name in set(db.session.scalars(db.select(FacilityBooking.image).where(FacilityBooking.image.isnot(None)))):
        source = os.path.join(public, os.path.basename(name))
        if name in pictures or not os.path.isfile(source):
            continue
        os.makedirs(private, exist_ok=True)
        shutil.move(source, os.path.join(private, os.path.basename(name)))
        moved += 1
    return moved


def register_cli(app):
    @app.cli.command('init-db')
    @click.option('--reset', is_flag=True, help='Drop all tables first.')
    def init_db_command(reset):
        """Create tables and load sample data."""
        passwords = init_db(reset=reset)
        url = db.engine.url.render_as_string(hide_password=True)
        click.echo(f'Database ready: {url}' + ('' if passwords else ' (already had data)'))
        for email, password in passwords.items():
            click.echo(f'  Sample login: {email} / {password}')
        current_app.logger.info('init-db done')

    @app.cli.command('upgrade-db')
    def upgrade_db_command():
        """Add columns and unique indexes introduced by newer versions to an existing database."""
        added = upgrade_schema()
        click.echo('Added: ' + ', '.join(added) if added else 'Database is up to date.')

    @app.cli.command('seed-demo')
    @click.option('--reset', is_flag=True, help='Recreate the database with only the demo data.')
    def seed_demo_command(reset):
        """Load demo hospitals, doctors, facilities, users and bookings."""
        from .demo import load_demo
        for email, password in init_db(reset=reset).items():  # creates/upgrades tables; sample data only if empty
            click.echo(f'  Sample login: {email} / {password}')
        click.echo(load_demo())

    @app.cli.command('create-admin')
    @click.option('--email', prompt=True)
    @click.option('--name', prompt=True)
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin_command(email, name, password):
        """Create an admin account, or make an existing account admin."""
        email = email.strip().lower()
        problem = password_problem(password, email, name)
        if problem:
            raise click.ClickException(problem)
        user = db.session.scalar(db.select(User).filter_by(email=email))
        if user is None:
            user = User(email=email, name=name, phone='-', city='-')
            db.session.add(user)
        user.role = 'admin'
        user.archived = False
        user.set_password(password)
        db.session.commit()
        click.echo(f'Admin ready: {email}')

    @app.cli.command('hash-passwords')
    def hash_passwords_command():
        """Hash all plain-text passwords left over from the original database."""
        count = 0
        for user in db.session.scalars(db.select(User)):
            if user.password and not user.has_hashed_password:
                user.set_password(user.password)
                count += 1
        db.session.commit()
        click.echo(f'Hashed {count} password(s).')

    @app.cli.command('secure-uploads')
    def secure_uploads_command():
        """Move patient files uploaded by older versions out of the public static folder."""
        click.echo(f'Moved {secure_uploads()} patient file(s) to {current_app.config["PRIVATE_UPLOAD_FOLDER"]}.')
