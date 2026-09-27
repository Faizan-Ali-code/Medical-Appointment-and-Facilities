"""Logged-in user area: account, settings, own bookings."""
import pytest

PROTECTED = ['/account', '/setting', '/user_docbookings', '/user_facbookings']


@pytest.mark.parametrize('url', PROTECTED)
def test_pages_require_login(client, url):
    r = client.get(url, follow_redirects=True)
    assert b'Login Form' in r.data


def test_account_shows_user_details(user_client):
    r = user_client.get('/account')
    assert r.status_code == 200
    for text in (b'User Account', b'user@yahoo.com', b'03108899456', b'Islamabad'):
        assert text in r.data
    assert b'Doctor Bookings' in r.data  # user navigation


def test_admin_account_shows_admin_nav(admin_client):
    r = admin_client.get('/account')
    assert b'Admin Account' in r.data
    assert b'Add Hospital' in r.data


# ------------------------------------------------------------ settings

def test_setting_page_prefilled(user_client):
    r = user_client.get('/setting')
    assert r.status_code == 200
    assert b'value="user@yahoo.com"' in r.data


def test_setting_updates_profile_and_keeps_password(user_client, rows, app):
    before = rows('SELECT password FROM users WHERE id = 1')[0]['password']
    data = {'name': 'New Name', 'email': 'user@yahoo.com', 'city': 'Multan', 'password': '',
            'phone': '0311'}
    r = user_client.post('/setting', data=data)
    assert b'Your Profile Is Updated' in r.data
    saved = rows('SELECT * FROM users WHERE id = 1')[0]
    assert saved['name'] == 'New Name' and saved['city'] == 'Multan'
    assert saved['password'] == before  # empty field keeps the password


def test_setting_changes_password(user_client, app):
    from conftest import login
    data = {'name': 'User', 'city': 'X', 'phone': '1', 'password': 'newpass123'}
    assert b'Your Profile Is Updated' in user_client.post('/setting', data=data).data
    assert login(app.test_client(), 'user@yahoo.com', 'user').status_code == 200  # old password rejected
    assert login(app.test_client(), 'user@yahoo.com', 'newpass123').status_code == 302


def test_setting_rejects_short_password(user_client):
    r = user_client.post('/setting', data={'name': 'U', 'city': 'X', 'phone': '1', 'password': '123'})
    assert b'at least 6 characters' in r.data


def test_settings_page_never_shows_password(user_client, rows):
    stored = rows('SELECT password FROM users WHERE id = 1')[0]['password']
    html = user_client.get('/setting').get_data(as_text=True)
    assert stored not in html and 'value="user"' not in html


def test_setting_rejects_empty_fields(user_client, rows):
    r = user_client.post('/setting', data={'name': '', 'email': 'user@yahoo.com', 'city': 'X',
                                           'password': 'user', 'phone': '1'})
    assert b'Please Fill All The Fields' in r.data
    assert rows('SELECT name FROM users WHERE id = 1')[0]['name'] == 'User'


# ------------------------------------------------------------ doctor bookings

def test_my_doctor_bookings(user_client):
    r = user_client.get('/user_docbookings')
    assert r.status_code == 200
    assert b'Sadaf' in r.data
    assert b'01 August, 2023' in r.data
    assert b'10:00 AM' in r.data


def test_my_doctor_bookings_empty(admin_client):
    assert b'No Record' in admin_client.get('/user_docbookings').data


def test_cancel_my_doctor_booking_keeps_history(user_client, rows):
    user_client.post('/book_doctor/3', data={'date': '2030-01-01', 'slot': '10:10 AM'})
    booking_id = rows("SELECT id FROM doctor_bookings WHERE date = '2030-01-01'")[0]['id']
    r = user_client.post(f'/deluser_docbookings/{booking_id}', follow_redirects=False)
    assert r.status_code == 302
    assert rows(f'SELECT status FROM doctor_bookings WHERE id = {booking_id}')[0]['status'] == 'cancelled'
    assert b'Cancelled' in user_client.get('/user_docbookings').data


def test_past_booking_cannot_be_cancelled(user_client, rows):
    r = user_client.post('/deluser_docbookings/1')  # seed booking is on 2023-08-01
    assert b'Only upcoming booked appointments can be cancelled' in r.data
    assert rows('SELECT status FROM doctor_bookings WHERE id = 1')[0]['status'] == 'booked'


def test_book_doctor_page_shows_form_for_user(user_client):
    r = user_client.get('/book_doctor/3')
    assert b'Choose Time Slot' in r.data
    assert b'Please Login As User' not in r.data


def test_book_doctor_success(user_client, rows):
    data = {'doctor_id': '3', 'user_id': '1', 'date': '2030-01-01', 'slot': '10:10 AM'}
    r = user_client.post('/book_doctor/3', data=data, follow_redirects=True)
    assert b'Booking Successful' in r.data
    saved = rows("SELECT * FROM doctor_bookings WHERE date = '2030-01-01'")
    assert len(saved) == 1 and saved[0]['slot'] == '10:10 AM' and saved[0]['user_id'] == 1


FUTURE = {'date': '2030-01-01', 'slot': '10:10 AM'}


def test_book_doctor_slot_taken_by_someone_else(user_client, other_user_client, rows):
    user_client.post('/book_doctor/3', data=FUTURE)
    r = other_user_client.post('/book_doctor/3', data=FUTURE)
    assert b'Someone already booked' in r.data
    assert len(rows("SELECT * FROM doctor_bookings WHERE date = '2030-01-01'")) == 1


def test_book_doctor_same_slot_twice(user_client, rows):
    user_client.post('/book_doctor/3', data=FUTURE)
    r = user_client.post('/book_doctor/3', data=FUTURE)
    assert b'You already booked' in r.data
    assert len(rows("SELECT * FROM doctor_bookings WHERE date = '2030-01-01'")) == 1


@pytest.mark.parametrize('data,message', [
    ({'date': '2020-01-01', 'slot': '10:10 AM'}, b'today or a future date'),
    ({'date': 'not-a-date', 'slot': '10:10 AM'}, b'valid date'),
    ({'date': '', 'slot': '10:10 AM'}, b'valid date'),
    ({'date': '2030-01-01', 'slot': '11:59 PM'}, b'available time slots'),
])
def test_book_doctor_invalid_input(user_client, rows, data, message):
    r = user_client.post('/book_doctor/3', data=data)
    assert message in r.data
    assert len(rows('SELECT * FROM doctor_bookings')) == 1


def test_book_doctor_ignores_forged_user_id(user_client, rows):
    user_client.post('/book_doctor/3', data={**FUTURE, 'user_id': '2'})
    assert rows("SELECT user_id FROM doctor_bookings WHERE date = '2030-01-01'")[0]['user_id'] == 1


def test_guest_cannot_book_doctor(client, rows):
    r = client.post('/book_doctor/3', data=FUTURE)
    assert b'Login Form' in r.data
    assert len(rows('SELECT * FROM doctor_bookings')) == 1


def test_admin_cannot_book_doctor(admin_client, rows):
    r = admin_client.post('/book_doctor/3', data=FUTURE)
    assert b'Please Login As User' in r.data
    assert len(rows('SELECT * FROM doctor_bookings')) == 1


def test_cannot_cancel_other_users_booking(other_user_client, rows):
    assert other_user_client.post('/deluser_docbookings/1', follow_redirects=False).status_code == 404
    assert len(rows('SELECT * FROM doctor_bookings')) == 1


# ------------------------------------------------------------ facility (test) bookings

def test_my_facility_bookings(user_client):
    r = user_client.get('/user_facbookings')
    assert r.status_code == 200
    assert b'Radiance Imaging Center' in r.data
    assert b'Pending' in r.data


def test_my_facility_bookings_empty(admin_client):
    assert b'No Record' in admin_client.get('/user_facbookings').data


def _facility_form(service='MRI'):
    from conftest import png
    return {'facility_id': '3', 'user_id': '1', 'date': '2030-01-01', 'service': service,
            'image': png('scan.png')}


def test_book_facility_success(user_client, rows, upload_dir):
    import os
    r = user_client.post('/book_facilities/3', data=_facility_form(), follow_redirects=True,
                         content_type='multipart/form-data')
    assert b'Service Booking Successful' in r.data
    saved = rows("SELECT * FROM facility_bookings WHERE service = 'MRI'")
    assert len(saved) == 1 and saved[0]['status'] == 0 and saved[0]['result'] == '-'
    assert os.path.exists(os.path.join(upload_dir, saved[0]['image']))


def test_book_facility_with_pdf_report(user_client, rows):
    import io
    from conftest import PDF_BYTES
    data = {'service': 'MRI', 'image': (io.BytesIO(PDF_BYTES), 'prescription.pdf')}
    r = user_client.post('/book_facilities/3', data=data, content_type='multipart/form-data')
    assert b'Service Booking Successful' in r.data
    assert rows("SELECT image FROM facility_bookings WHERE service = 'MRI'")[0]['image'].endswith('.pdf')
    assert b'bi-file-earmark-pdf' in user_client.get('/user_facbookings').data


def test_book_facility_rejects_fake_file(user_client, rows):
    import io
    data = {'service': 'MRI', 'image': (io.BytesIO(b'not really a pdf'), 'x.pdf')}
    r = user_client.post('/book_facilities/3', data=data, content_type='multipart/form-data')
    assert b'does not match its type' in r.data
    assert len(rows('SELECT * FROM facility_bookings')) == 1


def test_rejected_facility_booking_saves_no_file(user_client, upload_dir):
    import os
    before = set(os.listdir(upload_dir))
    user_client.post('/book_facilities/3', data=_facility_form('Heart Transplant'), content_type='multipart/form-data')
    assert set(os.listdir(upload_dir)) == before


def test_book_facility_duplicate_pending(user_client, rows):
    user_client.post('/book_facilities/3', data=_facility_form(), content_type='multipart/form-data')
    r = user_client.post('/book_facilities/3', data=_facility_form(), follow_redirects=True,
                         content_type='multipart/form-data')
    assert b'wait for result' in r.data
    assert len(rows("SELECT * FROM facility_bookings WHERE service = 'MRI'")) == 1


def test_book_facility_without_image(user_client, rows):
    r = user_client.post('/book_facilities/3', data={'service': 'MRI'})
    assert b'Service Booking Successful' in r.data
    assert rows("SELECT image FROM facility_bookings WHERE service = 'MRI'")[0]['image'] is None


def test_book_facility_unknown_service(user_client, rows):
    r = user_client.post('/book_facilities/3', data={'service': 'Heart Transplant'})
    assert b'available services' in r.data
    assert len(rows('SELECT * FROM facility_bookings')) == 1


def test_book_facility_can_rebook_after_result(user_client, admin_client, rows):
    user_client.post('/book_facilities/3', data={'service': 'MRI'})
    booking_id = rows("SELECT id FROM facility_bookings WHERE service = 'MRI'")[0]['id']
    admin_client.post(f'/res_positive/{booking_id}')
    r = user_client.post('/book_facilities/3', data={'service': 'MRI'})
    assert b'Service Booking Successful' in r.data


def test_guest_and_admin_cannot_book_facility(client, admin_client, rows):
    assert b'Login Form' in client.post('/book_facilities/3', data={'service': 'MRI'}).data
    assert b'Please Login As User' in admin_client.post('/book_facilities/3', data={'service': 'MRI'}).data
    assert len(rows('SELECT * FROM facility_bookings')) == 1
