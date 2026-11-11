"""Admin area: hospitals, doctors, facilities, users, bookings management."""
import io

import pytest

from conftest import png as img

ADMIN_ONLY_GET = ['/addhospital', '/addfacility', '/add_doctor', '/hospitals/edit/3',
                  '/facilities/edit/3', '/doctors/edit/3']
ADMIN_ONLY_DELETE = ['/hospitals/delete/3', '/doctors/delete/3', '/facilities/delete/3']
# every URL that changes data: POST only (a GET link can be triggered by another website)
POST_ONLY = ADMIN_ONLY_DELETE + ['/user_delete/1', '/del_docbookings/1', '/del_facbookings/1',
                                 '/res_positive/1', '/res_negitive/1', '/deluser_docbookings/1', '/logout']


# ------------------------------------------------------------ access control

@pytest.mark.parametrize('url', ADMIN_ONLY_GET + ['/hospitals', '/doctors', '/users'])
def test_guest_is_sent_to_login(client, url):
    assert b'Login Form' in client.get(url, follow_redirects=True).data


@pytest.mark.parametrize('url', POST_ONLY)
def test_state_changing_urls_reject_get(admin_client, rows, url):
    r = admin_client.get(url)
    assert r.status_code == 405 and b'submitted with a button' in r.data
    assert len(rows('SELECT * FROM hospitals')) == 1 and len(rows('SELECT * FROM users')) == 2


@pytest.mark.parametrize('url', ADMIN_ONLY_DELETE)
def test_guest_cannot_delete(client, rows, url):
    assert b'Login Form' in client.post(url).data
    assert len(rows('SELECT * FROM hospitals')) == 1


@pytest.mark.parametrize('url', ADMIN_ONLY_GET)
def test_user_cannot_open_admin_forms(user_client, url):
    r = user_client.get(url)
    assert r.status_code == 302


@pytest.mark.parametrize('url,table', [
    ('/hospitals/delete/3', 'hospitals'),
    ('/doctors/delete/3', 'doctors'),
    ('/facilities/delete/3', 'facilities'),
])
def test_user_cannot_delete_catalog(user_client, rows, url, table):
    user_client.post(url)
    assert len(rows(f'SELECT * FROM {table}')) == 1


def test_user_cannot_delete_users(user_client, rows):
    user_client.post('/user_delete/2')
    assert len(rows('SELECT * FROM users WHERE id = 2')) == 1


@pytest.mark.parametrize('url', ['/users', '/doctors', '/hospitals', '/facilities', '/docbookings/3',
                                 '/facbookings/3', '/user_edit/1'])
def test_user_cannot_open_admin_listings(user_client, url):
    r = user_client.get(url)
    assert r.status_code == 302 and r.headers['Location'].endswith('/account')
    assert b'Admin access required' in user_client.get('/account').data


@pytest.mark.parametrize('url', ['/res_positive/1', '/res_negitive/1', '/del_facbookings/1'])
def test_user_cannot_manage_test_bookings(user_client, rows, url):
    user_client.post(url)
    saved = rows('SELECT * FROM facility_bookings WHERE id = 1')
    assert len(saved) == 1 and saved[0]['result'] == '-'


def test_user_cannot_delete_doctor_booking_as_admin(user_client, rows):
    user_client.post('/del_docbookings/1')
    assert len(rows('SELECT * FROM doctor_bookings')) == 1


@pytest.mark.parametrize('url', ['/hospitals/edit/999', '/doctors/edit/999', '/facilities/edit/999',
                                 '/user_edit/999', '/docbookings/999', '/facbookings/999'])
def test_unknown_ids_return_404(admin_client, url):
    assert admin_client.get(url).status_code == 404


@pytest.mark.parametrize('url', ['/hospitals/delete/999', '/doctors/delete/999', '/facilities/delete/999',
                                 '/user_delete/999', '/del_docbookings/999', '/del_facbookings/999',
                                 '/res_positive/999'])
def test_unknown_ids_return_404_on_post(admin_client, url):
    assert admin_client.post(url).status_code == 404


# ------------------------------------------------------------ hospitals

def test_hospitals_list(admin_client):
    r = admin_client.get('/hospitals')
    assert r.status_code == 200 and b'General Hospital' in r.data


def test_hospitals_search(admin_client):
    assert b'General Hospital' in admin_client.post('/hospitals', data={'search_query': 'gen'}).data
    assert b'No Record' in admin_client.post('/hospitals', data={'search_query': 'zzz'}).data
    assert b'General Hospital' in admin_client.post('/hospitals', data={'search_query': ''}).data


def test_search_works_with_get_query_string(admin_client, client):
    assert b'No Record' in admin_client.get('/hospitals?search_query=zzz').data
    assert b'No Record' in client.get('/fdoctors?search_query=zzz').data
    assert b'Sadaf' in client.get('/fdoctors?search_query=sadaf').data


HOSPITAL = {'name': 'City Hospital', 'city': 'Karachi', 'address': 'Main Road', 'phone': '021',
            'description': 'A new hospital'}


def test_add_hospital(admin_client, rows, upload_dir):
    import os
    r = admin_client.post('/addhospital', data={**HOSPITAL, 'image': img('city.png')},
                          content_type='multipart/form-data')
    assert b'Hospital Is Added' in r.data
    saved = rows("SELECT * FROM hospitals WHERE name = 'City Hospital'")
    assert len(saved) == 1
    stored = saved[0]['image']
    assert stored.endswith('.png') and stored != 'city.png'  # random name, original name not reused
    assert os.path.exists(os.path.join(upload_dir, stored))


@pytest.mark.parametrize('upload,message', [
    ((io.BytesIO(b'MZ\x90\x00 not an image'), 'virus.png'), b'does not match its type'),
    ((io.BytesIO(b'<script>'), 'page.html'), b'Only these file types are allowed'),
    ((io.BytesIO(b'%PDF-1.4'), 'report.pdf'), b'Only these file types are allowed'),
    ((io.BytesIO(b'\x89PNG\r\n\x1a\n'), 'noext'), b'Only these file types are allowed'),
])
def test_add_hospital_rejects_bad_uploads(admin_client, rows, upload, message):
    r = admin_client.post('/addhospital', data={**HOSPITAL, 'image': upload}, content_type='multipart/form-data')
    assert message in r.data
    assert len(rows('SELECT * FROM hospitals')) == 1


def test_add_hospital_duplicate(admin_client, rows):
    r = admin_client.post('/addhospital', data={**HOSPITAL, 'name': 'General Hospital', 'image': img()},
                          content_type='multipart/form-data')
    assert b'Already Added' in r.data
    assert len(rows('SELECT * FROM hospitals')) == 1


def test_edit_hospital_page(admin_client):
    r = admin_client.get('/hospitals/edit/3')
    assert r.status_code == 200 and b'value="General Hospital"' in r.data


def test_add_hospital_missing_field(admin_client, rows):
    r = admin_client.post('/addhospital', data={**HOSPITAL, 'city': '', 'image': img()},
                          content_type='multipart/form-data')
    assert b'Please Fill All The Fields' in r.data
    assert b'value="City Hospital"' in r.data  # form keeps what was typed
    assert len(rows('SELECT * FROM hospitals')) == 1


def test_add_hospital_requires_image(admin_client, rows):
    r = admin_client.post('/addhospital', data=HOSPITAL)
    assert b'Please upload an image' in r.data
    assert len(rows('SELECT * FROM hospitals')) == 1


def test_edit_hospital_can_keep_its_own_name(admin_client, rows):
    r = admin_client.post('/hospitals/edit/3', data={**HOSPITAL, 'name': 'General Hospital'})
    assert b'Hospital Info is Updated' in r.data


def test_edit_hospital_form_has_file_upload(admin_client):
    assert b'multipart/form-data' in admin_client.get('/hospitals/edit/3').data


def test_edit_hospital_keeps_old_image(admin_client, rows):
    data = {**HOSPITAL, 'hid': '3', 'old_image': 'lahore-general-hos-1.jpg'}
    r = admin_client.post('/hospitals/edit/3', data=data)
    assert b'Hospital Info is Updated' in r.data
    saved = rows('SELECT * FROM hospitals WHERE id = 3')[0]
    assert saved['name'] == 'City Hospital' and saved['image'] == 'lahore-general-hos-1.jpg'


def test_edit_hospital_with_new_image(admin_client, rows):
    data = {**HOSPITAL, 'image': img('new.png')}
    admin_client.post('/hospitals/edit/3', data=data, content_type='multipart/form-data')
    image = rows('SELECT image FROM hospitals WHERE id = 3')[0]['image']
    assert image != 'lahore-general-hos-1.jpg' and image.endswith('.png')


def test_delete_hospital_also_deletes_its_doctors_facilities_and_bookings(admin_client, rows):
    r = admin_client.post('/hospitals/delete/3', follow_redirects=False)
    assert r.status_code == 302
    for table in ('hospitals', 'doctors', 'facilities', 'doctor_bookings', 'facility_bookings'):
        assert rows(f'SELECT * FROM {table}') == [], table


# ------------------------------------------------------------ doctors

def test_doctors_list(admin_client):
    r = admin_client.get('/doctors')
    assert r.status_code == 200
    assert b'Sadaf' in r.data and b'General Hospital' in r.data


def test_doctors_search(admin_client):
    assert b'Sadaf' in admin_client.post('/doctors', data={'search_query': 'sad'}).data
    assert b'No Record' in admin_client.post('/doctors', data={'search_query': 'zzz'}).data
    assert b'Sadaf' in admin_client.post('/doctors', data={'search_query': ''}).data


def test_doctor_hospital_missing_in_db_shows_not_found(admin_client, rows):
    # data imported from an old MySQL dump may have doctors without a hospital
    from conftest import _check_engine
    import sqlalchemy as sa
    with _check_engine.begin() as conn:
        conn.execute(sa.text('UPDATE doctors SET hospital_id = 999'))
    assert b'Not Found' in admin_client.get('/doctors').data


DOCTOR = {'name': 'Dr Ahmed', 'specialization': 'Cardiology', 'fee': '2000',
          'slots': '09:00 AM, 09:30 AM', 'hospital_id': '3', 'description': 'Heart specialist'}


def test_add_doctor_page_lists_hospitals(admin_client):
    r = admin_client.get('/add_doctor')
    assert r.status_code == 200 and b'General Hospital' in r.data


def test_add_doctor(admin_client, rows):
    r = admin_client.post('/add_doctor', data={**DOCTOR, 'image': img('ahmed.png')},
                          content_type='multipart/form-data')
    assert b'Your Doctor Is Added' in r.data
    saved = rows("SELECT * FROM doctors WHERE name = 'Dr Ahmed'")
    assert len(saved) == 1 and saved[0]['hospital_id'] == 3


def test_add_doctor_duplicate(admin_client, rows):
    r = admin_client.post('/add_doctor', data={**DOCTOR, 'name': 'Sadaf', 'image': img()},
                          content_type='multipart/form-data')
    assert b'Already Added' in r.data
    assert len(rows('SELECT * FROM doctors')) == 1


def test_edit_doctor_page(admin_client):
    assert b'value="Sadaf"' in admin_client.get('/doctors/edit/3').data


def test_edit_doctor_page_selects_current_hospital(admin_client):
    assert b'value="3" selected' in admin_client.get('/doctors/edit/3').data


@pytest.mark.parametrize('hospital_id', ['999', 'abc', ''])
def test_add_doctor_invalid_hospital(admin_client, rows, hospital_id):
    r = admin_client.post('/add_doctor', data={**DOCTOR, 'hospital_id': hospital_id, 'image': img()},
                          content_type='multipart/form-data')
    assert b'Please choose a hospital' in r.data or b'Please Fill All The Fields' in r.data
    assert len(rows('SELECT * FROM doctors')) == 1


def test_delete_doctor_also_deletes_its_bookings(admin_client, rows):
    admin_client.post('/doctors/delete/3')
    assert rows('SELECT * FROM doctor_bookings') == []


def test_edit_doctor(admin_client, rows):
    data = {**DOCTOR, 'did': '3', 'old_image': 'wp10434441.png'}
    r = admin_client.post('/doctors/edit/3', data=data)
    assert b'Doctor Info is Updated' in r.data
    saved = rows('SELECT * FROM doctors WHERE id = 3')[0]
    assert saved['name'] == 'Dr Ahmed' and saved['image'] == 'wp10434441.png'


def test_edit_doctor_with_new_image(admin_client, rows):
    data = {**DOCTOR, 'image': img('d.png')}
    admin_client.post('/doctors/edit/3', data=data, content_type='multipart/form-data')
    image = rows('SELECT image FROM doctors WHERE id = 3')[0]['image']
    assert image != 'wp10434441.png' and image.endswith('.png')


def test_delete_doctor(admin_client, rows):
    assert admin_client.post('/doctors/delete/3', follow_redirects=False).status_code == 302
    assert rows('SELECT * FROM doctors') == []


# ------------------------------------------------------------ facilities

def test_facilities_list(admin_client):
    r = admin_client.get('/facilities')
    assert r.status_code == 200 and b'Radiance Imaging Center' in r.data


def test_facilities_search(admin_client):
    assert b'Radiance' in admin_client.post('/facilities', data={'search_query': 'CT Scan'}).data
    assert b'No Record' in admin_client.post('/facilities', data={'search_query': 'zzz'}).data
    assert b'Radiance' in admin_client.post('/facilities', data={'search_query': ''}).data


FACILITY = {'hospital_id': '3', 'name': 'City Lab', 'description': 'Blood tests',
            'services': 'CBC, LFT', 'fee': '500, 900', 'contact': '0300'}


def test_add_facility_page(admin_client):
    r = admin_client.get('/addfacility')
    assert r.status_code == 200 and b'General Hospital' in r.data


def test_add_facility(admin_client, rows):
    r = admin_client.post('/addfacility', data=FACILITY)
    assert b'Facility added successfully' in r.data
    assert len(rows("SELECT * FROM facilities WHERE name = 'City Lab'")) == 1


def test_add_facility_duplicate(admin_client, rows):
    r = admin_client.post('/addfacility', data={**FACILITY, 'name': 'Radiance Imaging Center'})
    assert b'already exists' in r.data
    assert len(rows('SELECT * FROM facilities')) == 1


def test_edit_facility_page(admin_client):
    assert b'value="Radiance Imaging Center"' in admin_client.get('/facilities/edit/3').data


def test_edit_facility_page_selects_current_hospital(admin_client):
    assert b'value="3" selected' in admin_client.get('/facilities/edit/3').data


def test_edit_facility(admin_client, rows):
    r = admin_client.post('/facilities/edit/3', data={**FACILITY, 'fid': '3'})
    assert b'Facility Info is Updated' in r.data
    assert rows('SELECT name FROM facilities WHERE id = 3')[0]['name'] == 'City Lab'


def test_delete_facility(admin_client, rows):
    assert admin_client.post('/facilities/delete/3', follow_redirects=False).status_code == 302
    assert rows('SELECT * FROM facilities') == []


# ------------------------------------------------------------ users

def test_users_list_only_normal_users(admin_client):
    r = admin_client.get('/users')
    assert r.status_code == 200
    assert b'user@yahoo.com' in r.data
    assert b'admin@yahoo.com' not in r.data


@pytest.mark.parametrize('query', ['Us', 'user@yahoo.com', 'Islamabad'])
def test_users_search(admin_client, query):
    assert b'user@yahoo.com' in admin_client.post('/users', data={'search_query': query}).data


def test_users_search_no_match_and_empty(admin_client):
    assert b'No Record' in admin_client.post('/users', data={'search_query': 'zzz'}).data
    assert b'user@yahoo.com' in admin_client.post('/users', data={'search_query': ''}).data


def test_user_edit_page(admin_client):
    assert b'value="user@yahoo.com"' in admin_client.get('/user_edit/1').data


def test_user_edit(admin_client, rows):
    data = {'name': 'Changed', 'email': 'user@yahoo.com', 'city': 'Quetta', 'password': '',
            'phone': '1'}
    r = admin_client.post('/user_edit/1', data=data)
    assert b'Your User Is Updated' in r.data
    assert rows('SELECT city FROM users WHERE id = 1')[0]['city'] == 'Quetta'


def test_user_edit_cannot_change_email(admin_client, rows):
    data = {'name': 'U', 'email': 'hacked@x.com', 'city': 'C', 'password': '', 'phone': '1'}
    admin_client.post('/user_edit/1', data=data)
    assert rows('SELECT email FROM users WHERE id = 1')[0]['email'] == 'user@yahoo.com'


def test_user_edit_empty_field(admin_client, rows):
    r = admin_client.post('/user_edit/1', data={'name': '', 'email': 'e', 'city': 'c',
                                               'password': 'p', 'phone': '1'})
    assert b'Please Fill All The Fields' in r.data
    assert rows('SELECT name FROM users WHERE id = 1')[0]['name'] == 'User'


def test_user_delete(admin_client, rows):
    assert admin_client.post('/user_delete/1', follow_redirects=False).status_code == 302
    assert rows('SELECT * FROM users WHERE id = 1') == []


# ------------------------------------------------------------ doctor bookings

def test_doctor_bookings_list(admin_client):
    r = admin_client.get('/docbookings/3')
    assert r.status_code == 200
    for text in (b'Sadaf', b'User', b'01 August, 2023', b'10:00 AM'):
        assert text in r.data


def test_delete_user_also_deletes_their_bookings(admin_client, rows):
    admin_client.post('/user_delete/1')
    assert rows('SELECT * FROM doctor_bookings') == []
    assert rows('SELECT * FROM facility_bookings') == []
    assert b'No Record' in admin_client.get('/docbookings/3').data


def test_deleted_user_is_logged_out(admin_client, user_client):
    admin_client.post('/user_delete/1')
    assert b'Login Form' in user_client.get('/account', follow_redirects=True).data


def test_delete_doctor_booking(admin_client, rows):
    r = admin_client.post('/del_docbookings/1', follow_redirects=False)
    assert r.status_code == 302 and r.headers['Location'].endswith('/docbookings/3')
    assert rows('SELECT * FROM doctor_bookings') == []


# ------------------------------------------------------------ facility bookings / results

def test_facility_bookings_list(admin_client):
    r = admin_client.get('/facbookings/3')
    assert r.status_code == 200
    for text in (b'User', b'chest-xray.jpg', b'01 August, 2023', b'Pending'):
        assert text in r.data


@pytest.mark.parametrize('url,result', [('/res_positive/1', 'Positive'), ('/res_negitive/1', 'Negative')])
def test_set_test_result(admin_client, rows, url, result):
    r = admin_client.post(url, follow_redirects=False)
    assert r.status_code == 302 and r.headers['Location'].endswith('/facbookings/3')
    saved = rows('SELECT * FROM facility_bookings WHERE id = 1')[0]
    assert saved['result'] == result and saved['status'] == 1
    assert b'Approved' in admin_client.get('/facbookings/3').data


def test_result_visible_to_user(admin_client, user_client):
    admin_client.post('/res_positive/1')
    r = user_client.get('/user_facbookings')
    assert b'Positive' in r.data and b'Approved' in r.data


def test_delete_facility_booking(admin_client, rows):
    assert admin_client.post('/del_facbookings/1', follow_redirects=False).status_code == 302
    assert rows('SELECT * FROM facility_bookings') == []


# ------------------------------------------------------------ other guards (logged-out)

@pytest.mark.parametrize('url', ['/user_edit/1', '/docbookings/3', '/facbookings/3', '/facilities'])
def test_guest_cannot_open_management_pages(client, url):
    assert b'Login Form' in client.get(url, follow_redirects=True).data


@pytest.mark.parametrize('url', ['/user_delete/1', '/del_docbookings/1', '/del_facbookings/1', '/res_positive/1',
                                 '/res_negitive/1', '/deluser_docbookings/1'])
def test_guest_cannot_use_management_actions(client, rows, url):
    assert b'Login Form' in client.post(url).data
    assert len(rows('SELECT * FROM doctor_bookings')) == 1
    assert len(rows('SELECT * FROM users')) == 2
    assert rows('SELECT result FROM facility_bookings')[0]['result'] == '-'


def test_admin_cannot_delete_own_account(admin_client, rows):
    r = admin_client.post('/user_delete/2')
    assert b'cannot delete your own account' in r.data
    assert len(rows('SELECT * FROM users WHERE id = 2')) == 1
