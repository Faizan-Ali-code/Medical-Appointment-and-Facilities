"""Step 7 (portfolio review): concurrency, session revocation, brute-force protection,
private patient files, browser security headers and the schema upgrade for them."""
import datetime
import io
import os
import re
import time

import pytest
import sqlalchemy as sa

from app import create_app
from app.extensions import db
from app.migrations import upgrade_schema
from conftest import ADMIN, DB_URL, PDF_BYTES, USER, _check_engine, login, png, register

FUTURE = '2030-01-07'  # a Monday


def sql(statement, **params):
    with _check_engine.begin() as conn:
        conn.execute(sa.text(statement), params)


# ------------------------------------------------------------ double bookings are stopped by the database

def test_lost_race_for_a_slot_is_rejected_by_the_database(user_client, other_user_client, rows, monkeypatch):
    """Both requests pass the Python check (simulated); the unique constraint still allows only one."""
    from app.services import bookings
    monkeypatch.setattr(bookings, '_slot_holder', lambda *args, **kwargs: None)
    user_client.post('/book_doctor/3', data={'date': FUTURE, 'slot': '10:00 AM'})
    r = other_user_client.post('/book_doctor/3', data={'date': FUTURE, 'slot': '10:00 AM'})
    assert b'Someone already booked' in r.data
    assert len(rows(f"SELECT * FROM doctor_bookings WHERE date = '{FUTURE}'")) == 1


def test_cancelled_booking_frees_the_slot_in_the_database(user_client, other_user_client, rows):
    user_client.post('/book_doctor/3', data={'date': FUTURE, 'slot': '10:00 AM'})
    booking_id = rows(f"SELECT id FROM doctor_bookings WHERE date = '{FUTURE}'")[0]['id']
    user_client.post(f'/deluser_docbookings/{booking_id}')
    assert rows(f'SELECT holds_slot FROM doctor_bookings WHERE id = {booking_id}')[0]['holds_slot'] is None
    r = other_user_client.post('/book_doctor/3', data={'date': FUTURE, 'slot': '10:00 AM'})
    assert b'Booking Successful' in r.data


def test_reopening_a_cancelled_booking_whose_slot_was_retaken(admin_client, user_client, other_user_client, rows):
    user_client.post('/book_doctor/3', data={'date': FUTURE, 'slot': '10:00 AM'})
    first = rows(f"SELECT id FROM doctor_bookings WHERE date = '{FUTURE}'")[0]['id']
    user_client.post(f'/deluser_docbookings/{first}')
    other_user_client.post('/book_doctor/3', data={'date': FUTURE, 'slot': '10:00 AM'})
    r = admin_client.post(f'/docbookings/status/{first}/booked')
    assert b'booked by someone else' in r.data
    assert rows(f'SELECT status FROM doctor_bookings WHERE id = {first}')[0]['status'] == 'cancelled'


def test_lost_race_for_a_facility_test_is_rejected(user_client, rows, monkeypatch):
    from app.services import bookings
    user_client.post('/book_facilities/3', data={'service': 'MRI'})
    monkeypatch.setattr(bookings, 'check_facility_booking', lambda *args: None)
    r = user_client.post('/book_facilities/3', data={'service': 'MRI'})
    assert b'already booked the service' in r.data
    assert len(rows("SELECT * FROM facility_bookings WHERE service = 'MRI'")) == 1


def test_bookings_sort_by_time_of_day_not_text(admin_client, user_client, rows):
    sql("UPDATE doctors SET slots = '9:00 AM, 10:00 AM' WHERE id = 3")
    user_client.post('/book_doctor/3', data={'date': FUTURE, 'slot': '10:00 AM'})
    user_client.post('/book_doctor/3', data={'date': FUTURE, 'slot': '9:00 AM'})
    html = admin_client.get('/docbookings/3').get_data(as_text=True)
    assert html.index('9:00 AM') < html.index('10:00 AM')  # as text, '10:...' would sort first


def test_slot_that_already_passed_today_cannot_be_booked(user_client, client, rows):
    sql("UPDATE doctors SET slots = '12:00 AM, 11:59 PM', days = '' WHERE id = 3")
    today = datetime.date.today().isoformat()
    r = user_client.post('/book_doctor/3', data={'date': today, 'slot': '12:00 AM'})
    assert b'already passed today' in r.data
    slots = client.get(f'/api/doctors/3/availability?date={today}').get_json()['slots']
    assert slots[0] == {'slot': '12:00 AM', 'free': True, 'passed': True}


# ------------------------------------------------------------ sessions

def test_copied_session_cookie_stops_working_after_logout(app, user_client):
    cookie = user_client.get_cookie('session').value
    user_client.post('/logout')
    thief = app.test_client()
    thief.set_cookie('session', cookie)
    assert thief.get('/account').status_code == 302


def test_new_password_ends_other_sessions_but_not_this_one(app, user_client):
    other_device = app.test_client()
    login(other_device, *USER)
    user_client.post('/setting', data={'name': 'User', 'city': 'X', 'phone': '1', 'password': 'brand-new-pass'})
    assert user_client.get('/account').status_code == 200
    assert other_device.get('/account').status_code == 302


def test_admin_password_reset_logs_the_user_out(admin_client, user_client):
    admin_client.post('/user_edit/1', data={'name': 'User', 'city': 'X', 'phone': '1', 'password': 'reset-by-admin'})
    assert user_client.get('/account').status_code == 302
    assert admin_client.get('/dashboard').status_code == 200


def test_session_expires_after_absolute_lifetime(user_client):
    with user_client.session_transaction() as s:
        s['login_at'] = int(time.time()) - 13 * 3600
    assert user_client.get('/account').status_code == 302


def test_session_cookie_is_permanent_with_idle_timeout(app, client):
    login(client, *USER)
    with client.session_transaction() as s:
        assert s.permanent
    assert app.permanent_session_lifetime == datetime.timedelta(minutes=30)


def test_logout_without_session_is_harmless(client):
    assert client.post('/logout', follow_redirects=False).status_code == 302


# ------------------------------------------------------------ brute-force protection

def test_account_locks_after_repeated_failures(client, rows):
    for _ in range(5):
        login(client, USER[0], 'wrong-password')
    r = login(client, *USER)  # even the right password is refused while locked
    assert r.status_code == 429 and b'locked' in r.data
    sql("UPDATE users SET locked_until = :t WHERE id = 1", t=datetime.datetime(2000, 1, 1))
    assert login(client, *USER).status_code == 302
    assert rows('SELECT failed_logins, locked_until FROM users WHERE id = 1')[0] == {
        'failed_logins': 0, 'locked_until': None}


def test_failed_logins_are_counted_in_the_database(client, rows):
    login(client, USER[0], 'wrong-password')
    login(client, USER[0], 'wrong-password')
    assert rows('SELECT failed_logins FROM users WHERE id = 1')[0]['failed_logins'] == 2


def test_rate_limit_per_client_ip():
    app = create_app('testing', SQLALCHEMY_DATABASE_URI=DB_URL, RATELIMIT_ENABLED=True,
                     LOGIN_RATE_LIMIT='3 per minute')
    client = app.test_client()
    codes = [client.post('/login', data={'email': 'x@y.com', 'password': 'nope'}).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    assert b'Too many attempts' in client.post('/login', data={}).data
    assert client.get('/login').status_code == 200  # only POSTs are limited


# ------------------------------------------------------------ password policy

@pytest.mark.parametrize('password,message', [
    ('password123', b'too common'),
    ('newuser', b'at least 8 characters'),
    ('newuser@test.com', b'must not be your name or email'),
    ('Newuser', b'at least 8 characters'),
])
def test_weak_passwords_are_rejected(client, rows, password, message):
    r = register(client, 'newuser@test.com', password, name='Newuser')
    assert message in r.data
    assert rows("SELECT * FROM users WHERE email = 'newuser@test.com'") == []


def test_password_equal_to_name_is_rejected(client):
    assert b'must not be your name' in register(client, 'n@test.com', 'Long Name Here', name='Long Name Here').data


def test_duplicate_email_race_is_caught(client, rows, monkeypatch):
    from app.blueprints import auth
    monkeypatch.setattr(auth, 'find_user_by_email', lambda email: None)
    r = register(client, 'user@yahoo.com')
    assert b'Already In Use' in r.data
    assert len(rows("SELECT * FROM users WHERE email = 'user@yahoo.com'")) == 1


def test_seeded_accounts_have_no_fixed_passwords(app):
    app2 = create_app('development', SQLALCHEMY_DATABASE_URI=DB_URL)
    with app2.app_context():
        from app.seed import seed_passwords
        first, second = seed_passwords(), seed_passwords()
    assert first != second and all(len(p) >= 12 for p in first.values())


# ------------------------------------------------------------ patient files are private

def _book_with_file(client, rows, data=None, name='scan.png'):
    data = data or png(name)
    client.post('/book_facilities/3', data={'service': 'MRI', 'image': data}, content_type='multipart/form-data')
    return rows("SELECT id, image FROM facility_bookings WHERE service = 'MRI'")[0]


def test_patient_file_is_not_a_static_url(client, user_client, rows):
    booking = _book_with_file(user_client, rows)
    assert client.get(f"/static/images/{booking['image']}").status_code == 404


def test_patient_file_only_for_owner_and_admin(client, user_client, other_user_client, admin_client, rows):
    booking = _book_with_file(user_client, rows)
    url = f"/bookings/files/{booking['id']}"
    own = user_client.get(url)
    assert own.status_code == 200 and own.mimetype == 'image/png'
    assert 'sandbox' in own.headers['Content-Security-Policy'] and own.headers['Cache-Control'] == 'private, no-store'
    assert admin_client.get(url).status_code == 200
    assert other_user_client.get(url).status_code == 404
    assert client.get(url).status_code == 302  # login first


def test_patient_pdf_is_downloaded_not_rendered(user_client, rows):
    booking = _book_with_file(user_client, rows, (io.BytesIO(PDF_BYTES), 'report.pdf'))
    r = user_client.get(f"/bookings/files/{booking['id']}")
    assert r.status_code == 200 and r.headers['Content-Disposition'].startswith('attachment')


def test_patient_file_link_uses_the_protected_route(user_client, rows):
    booking = _book_with_file(user_client, rows)
    html = user_client.get('/user_facbookings').get_data(as_text=True)
    assert f"/bookings/files/{booking['id']}" in html and '/static/images/' + booking['image'] not in html


def test_missing_or_absent_patient_file_is_404(user_client, private_upload_dir, rows):
    assert user_client.get('/bookings/files/1').status_code == 404       # seed booking has no file
    assert user_client.get('/bookings/files/999').status_code == 404
    booking = _book_with_file(user_client, rows)
    os.remove(os.path.join(private_upload_dir, booking['image']))
    assert user_client.get(f"/bookings/files/{booking['id']}").status_code == 404


def test_legacy_public_files_are_served_and_can_be_moved(app, user_client, upload_dir, private_upload_dir, rows):
    from conftest import PNG_BYTES
    for name in ('legacy.png', 'shared.png'):
        with open(os.path.join(upload_dir, name), 'wb') as f:
            f.write(PNG_BYTES)
    sql("UPDATE facility_bookings SET image = 'legacy.png' WHERE id = 1")
    sql("INSERT INTO facility_bookings (id, facility_id, user_id, service, image, date, result, status) "
        "VALUES (2, 3, 1, 'CT Scan', 'shared.png', '2023-08-01', '-', 1)")
    sql("UPDATE hospitals SET image = 'shared.png' WHERE id = 3")
    assert user_client.get('/bookings/files/1').status_code == 200  # still found in the old folder
    out = app.test_cli_runner().invoke(args=['secure-uploads']).output
    assert 'Moved 1 patient file(s)' in out
    assert os.path.exists(os.path.join(private_upload_dir, 'legacy.png'))
    assert not os.path.exists(os.path.join(upload_dir, 'legacy.png'))
    assert os.path.exists(os.path.join(upload_dir, 'shared.png'))  # also a hospital picture: left in place
    assert user_client.get('/bookings/files/1').status_code == 200


# ------------------------------------------------------------ browser security headers

def test_content_security_policy_with_nonce(client):
    r = client.get('/')
    csp = r.headers['Content-Security-Policy']
    nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
    html = r.get_data(as_text=True)
    assert f'<script nonce="{nonce}">' in html
    for directive in ("object-src 'none'", "frame-ancestors 'none'", "base-uri 'self'", "form-action 'self'"):
        assert directive in csp
    assert "'unsafe-inline'" not in csp
    assert client.get('/').headers['Content-Security-Policy'] != csp  # a fresh nonce per response


def test_cdn_assets_have_subresource_integrity(client):
    html = client.get('/').get_data(as_text=True)
    cdn_tags = re.findall(r'<(?:link|script)[^>]+cdn\.jsdelivr\.net[^>]*>', html)
    assert len(cdn_tags) == 3
    assert all('integrity="sha384-' in tag and 'crossorigin="anonymous"' in tag for tag in cdn_tags)


def test_hsts_only_over_https(client):
    assert 'Strict-Transport-Security' not in client.get('/').headers
    secure = client.get('/', base_url='https://localhost')
    assert secure.headers['Strict-Transport-Security'] == 'max-age=31536000; includeSubDomains'


def test_permissions_policy(client):
    assert 'camera=()' in client.get('/').headers['Permissions-Policy']


# ------------------------------------------------------------ configuration

def test_production_refuses_weak_secret_keys(monkeypatch):
    for weak in ('change-this-secret-key', 'short'):
        monkeypatch.setenv('SECRET_KEY', weak)
        with pytest.raises(RuntimeError):
            create_app('production', SQLALCHEMY_DATABASE_URI=DB_URL)
    monkeypatch.setenv('SECRET_KEY', 'x' * 64)
    assert create_app('production', SQLALCHEMY_DATABASE_URI=DB_URL).config['SESSION_COOKIE_SECURE'] is True


def test_debugger_is_opt_in(monkeypatch):
    monkeypatch.delenv('FLASK_DEBUG', raising=False)
    assert create_app('development', SQLALCHEMY_DATABASE_URI=DB_URL).debug is False
    monkeypatch.setenv('FLASK_DEBUG', '1')
    assert create_app('development', SQLALCHEMY_DATABASE_URI=DB_URL).debug is True


def test_search_treats_wildcards_literally(client):
    assert b'General Hospital' not in client.get('/?search_query=%25').data  # '%' is not "match everything"


# ------------------------------------------------------------ schema upgrade of an existing database

def test_upgrade_adds_unique_indexes_and_reports_duplicates(tmp_path, monkeypatch, caplog):
    url = 'sqlite:///' + str(tmp_path / 'previous.db')
    engine = sa.create_engine(url)
    with engine.begin() as conn:  # tables as the previous version created them: no constraints
        conn.execute(sa.text('CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(150))'))
        conn.execute(sa.text('CREATE TABLE doctor_bookings (id INTEGER PRIMARY KEY, doctor_id INTEGER, user_id '
                             "INTEGER, date DATE, slot VARCHAR(100), status VARCHAR(20) DEFAULT 'booked')"))
        conn.execute(sa.text('CREATE TABLE facility_bookings (id INTEGER PRIMARY KEY, facility_id INTEGER, '
                             'user_id INTEGER, service VARCHAR(100), status INTEGER DEFAULT 0)'))
        conn.execute(sa.text("INSERT INTO users (id, email) VALUES (1, 'a@x.com'), (2, 'a@x.com')"))
        conn.execute(sa.text("INSERT INTO doctor_bookings (id, doctor_id, user_id, date, slot, status) VALUES "
                             "(1, 3, 1, '2030-01-07', '10:00 AM', 'cancelled'), "
                             "(2, 3, 2, '2030-01-07', '10:00 AM', 'booked'), "
                             "(3, 3, 2, '2030-01-08', 'later', 'booked')"))
        conn.execute(sa.text('INSERT INTO facility_bookings (id, facility_id, user_id, service, status) VALUES '
                             "(1, 3, 1, 'MRI', 1), (2, 3, 1, 'MRI', 0)"))
    engine.dispose()
    monkeypatch.setenv('DATABASE_URL', url)
    app = create_app('testing')
    with app.app_context():
        added = upgrade_schema()
        assert 'uq_doctor_bookings_active_slot' in added and 'uq_facility_bookings_open' in added
        assert 'uq_users_email' not in added  # two rows share an email
        assert 'uq_users_email' in caplog.text and 'Remove the duplicate rows' in caplog.text
        holds = db.session.execute(sa.text('SELECT holds_slot FROM doctor_bookings ORDER BY id')).scalars().all()
        assert holds == [None, 1, 1]                      # the cancelled booking no longer holds its slot
        starts = db.session.execute(sa.text('SELECT starts_at FROM doctor_bookings ORDER BY id')).scalars().all()
        assert starts[1].startswith('10:00') and starts[2] is None  # 'later' is not a time
        db.session.execute(sa.text("DELETE FROM users WHERE id = 2"))
        db.session.commit()
        assert upgrade_schema() == ['uq_users_email']    # fixed data: the next run adds it
        db.engine.dispose()
