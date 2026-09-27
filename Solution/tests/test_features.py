"""Step 6 features: pagination, filters, working days, availability API, booking status, reschedule,
schema upgrade and demo data."""
import datetime
import os
import re

import pytest
import sqlalchemy as sa

from app import create_app
from app.demo import load_demo
from app.extensions import db
from app.migrations import upgrade_schema
from app.models import Doctor, DoctorBooking, Hospital
from conftest import _check_engine, login

TODAY = datetime.date.today()


def next_weekday(weekday, start=None):
    """Next date (after start/today) that falls on weekday (0 = Monday)."""
    d = (start or TODAY) + datetime.timedelta(days=1)
    while d.weekday() != weekday:
        d += datetime.timedelta(days=1)
    return d


def sql(statement, **params):
    with _check_engine.begin() as conn:
        conn.execute(sa.text(statement), params)


@pytest.fixture
def demo(app):
    with app.app_context():
        load_demo()


# ------------------------------------------------------------ demo data

def test_demo_data_counts_and_is_idempotent(app, demo, rows, upload_dir):
    assert len(rows('SELECT * FROM hospitals')) == 21      # 20 demo + 1 original
    assert len(rows('SELECT * FROM doctors')) == 41
    assert len(rows('SELECT * FROM facilities')) == 25
    assert len(rows("SELECT * FROM users WHERE email LIKE '%@demo.com'")) == 6
    assert len(rows('SELECT * FROM doctor_bookings')) > 10
    with app.app_context():
        assert load_demo() == 'Demo data is already loaded.'
    assert len(rows('SELECT * FROM hospitals')) == 21
    with open(os.path.join(upload_dir, 'demo', 'hospital-12.svg'), encoding='utf-8') as f:
        svg = f.read()
    assert 'Clifton Heart &amp; Lung Institute' in svg  # names are XML-escaped


def test_demo_patient_can_login(demo, client):
    assert login(client, 'patient1@demo.com', 'patient123').status_code == 302


def test_demo_images_render(demo, client):
    html = client.get('/').get_data(as_text=True)
    assert '/static/images/demo/hospital-' in html


def test_seed_demo_cli(monkeypatch, tmp_path):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'demo.db'))
    app = create_app('testing', UPLOAD_FOLDER=str(tmp_path / 'up'))
    runner = app.test_cli_runner()
    first = runner.invoke(args=['seed-demo'])
    assert 'Demo data loaded: 20 hospitals, 40 doctors, 24 facilities' in first.output
    assert 'already loaded' in runner.invoke(args=['seed-demo']).output
    assert 'Demo data loaded' in runner.invoke(args=['seed-demo', '--reset']).output
    with app.app_context():
        assert db.session.query(Hospital).count() == 21
        db.engine.dispose()


# ------------------------------------------------------------ pagination

def test_hospital_list_is_paginated(demo, client):
    html = client.get('/').get_data(as_text=True)
    assert html.count('class="card h-100 shadow-sm card-hover"') == 9
    assert 'Showing 1&ndash;9 of 21 hospitals' in html
    page3 = client.get('/?page=3').get_data(as_text=True)
    assert 'Showing 19&ndash;21 of 21 hospitals' in page3


def test_page_beyond_the_end_shows_last_page(demo, client):
    assert 'Showing 19&ndash;21 of 21' in client.get('/?page=99').get_data(as_text=True)
    assert 'Showing 1&ndash;9 of 21' in client.get('/?page=-4').get_data(as_text=True)


def test_page_links_keep_filters(demo, client):
    html = client.get('/fdoctors?specialization=Cardiologist&search_query=dr').get_data(as_text=True)
    assert 'Showing 1&ndash;3 of 3 doctors' in html
    html = client.get('/fdoctors?search_query=dr').get_data(as_text=True)
    assert re.search(r'href="/fdoctors\?search_query=dr&amp;page=2"', html)


@pytest.mark.parametrize('url,noun', [('/hospitals', 'hospitals'), ('/doctors', 'doctors'),
                                      ('/facilities', 'facilities')])
def test_admin_lists_are_paginated(demo, admin_client, url, noun):
    html = admin_client.get(url).get_data(as_text=True)
    assert f'Showing 1&ndash;10 of' in html and f' {noun}</span>' in html
    assert re.search(r'href="%s\?page=2"' % url, html)


def test_row_numbers_continue_on_next_page(demo, admin_client):
    html = admin_client.get('/doctors?page=2').get_data(as_text=True)
    assert '<td>11</td>' in html and '<td>1</td>' not in html


# ------------------------------------------------------------ filters

def test_city_filter(demo, client):
    html = client.get('/?city=karachi').get_data(as_text=True)
    assert 'Sea Breeze General Hospital' in html and 'Crescent Care Hospital' not in html
    assert re.search(r'3 results\s+in karachi', html)
    assert '<option value="Karachi" selected>' in html


def test_doctor_filters(demo, client):
    html = client.get('/fdoctors?specialization=dentist').get_data(as_text=True)
    cards = html.split('</form>', 1)[1]  # after the filter form (its dropdown lists every specialization)
    assert 'Showing 1&ndash;2 of 2 doctors' in html and 'Cardiologist' not in cards and 'Dentist' in cards
    hospital_page = client.get('/fdoctors?hospital_id=3').get_data(as_text=True)
    assert 'Sadaf' in hospital_page and 'Showing 1&ndash;1 of 1 doctor' in hospital_page


def test_facility_hospital_filter(demo, client):
    html = client.get('/ffacilities?hospital_id=3').get_data(as_text=True)
    assert 'Radiance Imaging Center' in html and 'Showing 1&ndash;1 of 1 facility' in html


# ------------------------------------------------------------ working days

def test_doctor_days_model():
    d = Doctor(days='Fri, Mon,Xyz')
    assert d.day_list == ['Mon', 'Fri'] and not d.works_every_day
    assert d.works_on(next_weekday(0)) and not d.works_on(next_weekday(1))
    assert Doctor(days='').works_every_day and Doctor(days=None).works_on(TODAY)


def test_booking_on_non_working_day_is_rejected(user_client, rows):
    sql("UPDATE doctors SET days = 'Mon' WHERE id = 3")
    tuesday = next_weekday(1)
    r = user_client.post('/book_doctor/3', data={'date': tuesday.isoformat(), 'slot': '10:10 AM'})
    assert b'not available on Tuesdays' in r.data and b'Working days: Mon' in r.data
    monday = next_weekday(0)
    r = user_client.post('/book_doctor/3', data={'date': monday.isoformat(), 'slot': '10:10 AM'})
    assert b'Booking Successful' in r.data


def test_working_days_shown(client, user_client):
    assert b'Every day' in client.get('/fdoctors').data
    sql("UPDATE doctors SET days = 'Mon,Wed,Fri' WHERE id = 3")
    assert 'Mon, Wed, Fri' in client.get('/book_doctor/3').get_data(as_text=True)
    assert 'Working days: Mon, Wed, Fri' in user_client.get('/book_doctor/3').get_data(as_text=True)


@pytest.mark.parametrize('days,stored', [(['Mon', 'Wed'], 'Mon,Wed'), ([], ''),
                                         (['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], ''),
                                         (['Sun', 'Mon', 'Bad'], 'Mon,Sun')])
def test_admin_sets_working_days(admin_client, rows, days, stored):
    data = {'name': 'Sadaf', 'hospital_id': '3', 'specialization': 'MBBS', 'fee': '1600',
            'slots': '10:00 AM', 'description': 'x', 'days': days}
    assert b'Doctor Info is Updated' in admin_client.post('/doctors/edit/3', data=data).data
    assert rows('SELECT days FROM doctors WHERE id = 3')[0]['days'] == stored


def test_admin_doctor_form_shows_day_checkboxes(admin_client):
    sql("UPDATE doctors SET days = 'Tue' WHERE id = 3")
    html = admin_client.get('/doctors/edit/3').get_data(as_text=True)
    assert re.search(r'value="Tue" id="day-Tue" autocomplete="off"\s+checked', html)
    assert not re.search(r'value="Mon" id="day-Mon" autocomplete="off"\s+checked', html)


# ------------------------------------------------------------ availability API

def test_availability_api(client, user_client):
    day = next_weekday(2).isoformat()
    user_client.post('/book_doctor/3', data={'date': day, 'slot': '10:10 AM'})
    data = client.get(f'/api/doctors/3/availability?date={day}').get_json()
    assert data['works'] is True and data['past'] is False and data['date'] == day
    assert data['slots'] == [{'slot': '10:00 AM', 'free': True}, {'slot': '10:10 AM', 'free': False},
                             {'slot': '10:15 AM', 'free': True}]


def test_availability_api_past_and_non_working(client):
    sql("UPDATE doctors SET days = 'Mon' WHERE id = 3")
    data = client.get(f'/api/doctors/3/availability?date={next_weekday(1).isoformat()}').get_json()
    assert data['works'] is False and data['days'] == ['Mon']
    assert client.get('/api/doctors/3/availability?date=2020-01-01').get_json()['past'] is True


def test_availability_api_errors(client):
    assert client.get('/api/doctors/3/availability?date=bad').status_code == 400
    assert client.get('/api/doctors/999/availability?date=2030-01-01').status_code == 404


def test_availability_exclude_only_for_own_booking(user_client, other_user_client, client, rows):
    day = next_weekday(3).isoformat()
    user_client.post('/book_doctor/3', data={'date': day, 'slot': '10:00 AM'})
    bid = rows(f"SELECT id FROM doctor_bookings WHERE date = '{day}'")[0]['id']
    own = user_client.get(f'/api/doctors/3/availability?date={day}&exclude={bid}').get_json()
    assert own['slots'][0] == {'slot': '10:00 AM', 'free': True}
    assert other_user_client.get(f'/api/doctors/3/availability?date={day}&exclude={bid}').status_code == 404
    assert client.get(f'/api/doctors/3/availability?date={day}&exclude={bid}').status_code == 404


def test_booking_page_has_live_slot_picker(user_client):
    html = user_client.get('/book_doctor/3').get_data(as_text=True)
    assert 'data-slot-picker' in html and 'data-url="/api/doctors/3/availability"' in html


# ------------------------------------------------------------ booking status

def _book(client, rows, day, slot='10:10 AM'):
    client.post('/book_doctor/3', data={'date': day.isoformat(), 'slot': slot})
    return rows(f"SELECT id FROM doctor_bookings WHERE date = '{day.isoformat()}' AND slot = '{slot}'")[0]['id']


def test_cancelled_slot_can_be_booked_again(user_client, other_user_client, rows):
    day = next_weekday(4)
    bid = _book(user_client, rows, day)
    user_client.post(f'/deluser_docbookings/{bid}')
    r = other_user_client.post('/book_doctor/3', data={'date': day.isoformat(), 'slot': '10:10 AM'})
    assert b'Booking Successful' in r.data


def test_cancelled_bookings_are_not_upcoming(user_client, admin_client, rows):
    bid = _book(user_client, rows, next_weekday(4))
    assert 'Upcoming appointments</div>' in admin_client.get('/dashboard').get_data(as_text=True)
    user_client.post(f'/deluser_docbookings/{bid}')
    assert 'No upcoming appointments' in admin_client.get('/dashboard').get_data(as_text=True)


@pytest.mark.parametrize('status,label', [('completed', 'Completed'), ('cancelled', 'Cancelled')])
def test_admin_sets_booking_status(admin_client, user_client, rows, status, label):
    bid = _book(user_client, rows, next_weekday(4))
    r = admin_client.post(f'/docbookings/status/{bid}/{status}')
    assert f'Appointment marked as {label}'.encode() in r.data
    assert rows(f'SELECT status FROM doctor_bookings WHERE id = {bid}')[0]['status'] == status
    assert label.encode() in user_client.get('/user_docbookings').data


def test_admin_unknown_status(admin_client, rows):
    assert b'Unknown status' in admin_client.post('/docbookings/status/1/lost').data
    assert rows('SELECT status FROM doctor_bookings WHERE id = 1')[0]['status'] == 'booked'


@pytest.mark.parametrize('next_url,expected', [('/dashboard', '/dashboard'),
                                               ('https://evil.example/x', '/docbookings/3'),
                                               ('//evil.example', '/docbookings/3'),
                                               ('/\\evil.example', '/docbookings/3')])
def test_status_redirect_is_safe(admin_client, next_url, expected):
    r = admin_client.post('/docbookings/status/1/completed', data={'next': next_url}, follow_redirects=False)
    assert r.headers['Location'] == expected


def test_user_cannot_set_booking_status(user_client, rows):
    user_client.post('/docbookings/status/1/cancelled')
    assert rows('SELECT status FROM doctor_bookings WHERE id = 1')[0]['status'] == 'booked'


def test_status_badges_and_actions(user_client, rows):
    _book(user_client, rows, next_weekday(4))
    html = user_client.get('/user_docbookings').get_data(as_text=True)
    assert 'bi-calendar-check me-1"></i>Booked' in html
    assert html.count('/reschedule"') == 1  # only the upcoming booking, not the 2023 one


# ------------------------------------------------------------ reschedule

def test_reschedule_flow(user_client, rows):
    bid = _book(user_client, rows, next_weekday(4))
    page = user_client.get(f'/user_docbookings/{bid}/reschedule').get_data(as_text=True)
    assert 'Reschedule Appointment' in page and f'exclude={bid}' in page
    new_day = next_weekday(4, next_weekday(4))
    r = user_client.post(f'/user_docbookings/{bid}/reschedule', data={'date': new_day.isoformat(), 'slot': '10:15 AM'})
    assert b'Appointment rescheduled' in r.data
    saved = rows(f'SELECT date, slot FROM doctor_bookings WHERE id = {bid}')[0]
    assert str(saved['date']) == new_day.isoformat() and saved['slot'] == '10:15 AM'


def test_reschedule_to_same_slot_is_allowed(user_client, rows):
    day = next_weekday(4)
    bid = _book(user_client, rows, day)
    r = user_client.post(f'/user_docbookings/{bid}/reschedule', data={'date': day.isoformat(), 'slot': '10:10 AM'})
    assert b'Appointment rescheduled' in r.data


def test_reschedule_to_taken_slot(user_client, other_user_client, rows):
    day = next_weekday(4)
    bid = _book(user_client, rows, day, '10:00 AM')
    _book(other_user_client, rows, day, '10:15 AM')
    r = user_client.post(f'/user_docbookings/{bid}/reschedule', data={'date': day.isoformat(), 'slot': '10:15 AM'})
    assert b'Someone already booked' in r.data
    assert rows(f'SELECT slot FROM doctor_bookings WHERE id = {bid}')[0]['slot'] == '10:00 AM'


def test_reschedule_bad_date(user_client, rows):
    bid = _book(user_client, rows, next_weekday(4))
    assert b'valid date' in user_client.post(f'/user_docbookings/{bid}/reschedule', data={'date': 'x'}).data


def test_reschedule_past_or_cancelled_booking_redirects(user_client, rows):
    r = user_client.get('/user_docbookings/1/reschedule')  # 2023 booking
    assert r.status_code == 302
    assert b'Only upcoming booked appointments' in user_client.get('/user_docbookings').data


def test_reschedule_service_rejects_inactive(app):
    from app.services import bookings as booking_service
    with app.app_context():
        booking = db.session.get(DoctorBooking, 1)
        with pytest.raises(booking_service.BookingError):
            booking_service.reschedule(booking, next_weekday(4), '10:00 AM')


def test_cannot_reschedule_other_users_booking(user_client, other_user_client, rows):
    bid = _book(user_client, rows, next_weekday(4))
    assert other_user_client.get(f'/user_docbookings/{bid}/reschedule').status_code == 404


# ------------------------------------------------------------ schema upgrade

def test_upgrade_schema_adds_missing_columns(tmp_path, monkeypatch):
    url = 'sqlite:///' + str(tmp_path / 'old.db')
    engine = sa.create_engine(url)
    with engine.begin() as conn:  # tables as in the ORIGINAL project (no days / status)
        conn.execute(sa.text('CREATE TABLE doctors (id INTEGER PRIMARY KEY, name VARCHAR(255))'))
        conn.execute(sa.text('CREATE TABLE doctor_bookings (id INTEGER PRIMARY KEY, slot VARCHAR(100))'))
        conn.execute(sa.text("INSERT INTO doctor_bookings (id, slot) VALUES (1, '10:00 AM')"))
    engine.dispose()
    monkeypatch.setenv('DATABASE_URL', url)
    app = create_app('testing')
    with app.app_context():
        assert sorted(upgrade_schema()) == ['doctor_bookings.status', 'doctors.days']
        assert upgrade_schema() == []
        status = db.session.execute(sa.text('SELECT status FROM doctor_bookings')).scalar()
        assert status == 'booked'  # old rows get the default
        db.engine.dispose()


def test_upgrade_db_cli(monkeypatch, tmp_path):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'cli.db'))
    app = create_app('testing')
    runner = app.test_cli_runner()
    assert 'up to date' in runner.invoke(args=['upgrade-db']).output  # no tables yet: nothing to add
    with app.app_context():
        db.session.execute(sa.text('CREATE TABLE doctors (id INTEGER PRIMARY KEY)'))
        db.session.commit()
    assert 'Added: doctors.days' in runner.invoke(args=['upgrade-db']).output
    with app.app_context():
        db.engine.dispose()
