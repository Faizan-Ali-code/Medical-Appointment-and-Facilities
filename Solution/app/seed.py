"""Create tables and load the sample data (same data as medicalappointmentsfinal.sql)."""
import datetime

import click
from flask import current_app

from .extensions import db
from .migrations import upgrade_schema
from .models import Doctor, DoctorBooking, Facility, FacilityBooking, Hospital, User


def _user(password, **fields):
    user = User(**fields)
    user.set_password(password)
    return user


def sample_data():
    return [
        Hospital(
            id=3, name='General Hospital', city='Lahore ',
            address='Ferozpur Road، near Chungi, Amar Sidhu Ismail Nagar, Lahore, Punjab 54000',
            phone='04299268801',
            description='Lahore General Hospital is a public sector teaching hospital located on Ferozepur '
                        'Road in Lahore, Punjab, Pakistan. It is affiliated with Ameer-ud-Din Medical '
                        'College, Lahore',
            image='lahore-general-hos-1.jpg'),
        Doctor(
            id=3, name='Sadaf', hospital_id=3, specialization='MBBS ', fee='1600',
            slots='10:00 AM, 10:10 AM, 10:15 AM',
            description='MBBS from University of Health Sciences, Lahore, FCPS (Medicine) from College of '
                        'Physicians and Surgeons, Pakistan and MRCP (UK) from Royal College Of Physicians '
                        'and has 11 years of experience in this field.',
            image='wp10434441.png'),
        Facility(
            id=3, hospital_id=3, name='Radiance Imaging Center',
            description='Radiance Imaging Center is a leading radiology facility equipped with advanced '
                        'imaging technologies and a team of experienced radiologists. We provide '
                        'high-quality diagnostic imaging services, enabling accurate visualization and '
                        'interpretation of internal',
            services='X-rays, Ultrasound, CT Scan, MRI', fee='1500, 800, 2500, 3000', contact='03778899456'),
        _user(id=1, name='User', email='user@yahoo.com', password='user', phone='03108899456',
              city='Islamabad', role='user'),
        _user(id=2, name='Salman', email='admin@yahoo.com', password='admin', phone='03998844444',
              city='Gujranwala', role='admin'),
        DoctorBooking(id=1, doctor_id=3, user_id=1, date=datetime.date(2023, 8, 1), slot='10:00 AM'),
        FacilityBooking(id=1, facility_id=3, user_id=1, service='as', image='chest-xray.jpg',
                        date=datetime.date(2023, 8, 1), result='-', status=0),
    ]


def init_db(reset=False):
    """Create tables; load sample data if the users table is empty. Needs an app context."""
    if reset:
        db.drop_all()
    db.create_all()
    upgrade_schema()
    if db.session.query(User).count() == 0:
        db.session.add_all(sample_data())
        db.session.commit()
        return True
    return False


def register_cli(app):
    @app.cli.command('init-db')
    @click.option('--reset', is_flag=True, help='Drop all tables first.')
    def init_db_command(reset):
        """Create tables and load sample data."""
        seeded = init_db(reset=reset)
        url = db.engine.url.render_as_string(hide_password=True)
        click.echo(f'Database ready: {url}' + ('' if seeded else ' (already had data)'))
        current_app.logger.info('init-db done')

    @app.cli.command('upgrade-db')
    def upgrade_db_command():
        """Add columns introduced by newer versions to an existing database."""
        added = upgrade_schema()
        click.echo('Added: ' + ', '.join(added) if added else 'Database is up to date.')

    @app.cli.command('seed-demo')
    @click.option('--reset', is_flag=True, help='Recreate the database with only the demo data.')
    def seed_demo_command(reset):
        """Load demo hospitals, doctors, facilities, users and bookings."""
        from .demo import load_demo
        init_db(reset=reset)  # creates/upgrades tables; sample data only if empty
        summary = load_demo()
        click.echo(summary)

    @app.cli.command('create-admin')
    @click.option('--email', prompt=True)
    @click.option('--name', prompt=True)
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin_command(email, name, password):
        """Create an admin account, or make an existing account admin."""
        email = email.strip().lower()
        if len(password) < current_app.config['MIN_PASSWORD_LENGTH']:
            raise click.ClickException(f"Password must be at least {current_app.config['MIN_PASSWORD_LENGTH']} characters.")
        user = db.session.scalar(db.select(User).filter_by(email=email))
        if user is None:
            user = User(email=email, name=name, phone='-', city='-')
            db.session.add(user)
        user.role = 'admin'
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
