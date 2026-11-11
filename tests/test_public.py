"""Public pages: hospitals, doctors, facilities, hospital detail, booking pages (guest view)."""
import pytest


# ------------------------------------------------------------ hospitals (home)

def test_home_lists_hospitals(client):
    r = client.get('/')
    assert r.status_code == 200
    assert b'General Hospital' in r.data
    assert b'lahore-general-hos-1.jpg' in r.data


@pytest.mark.parametrize('query', ['General', 'general', 'Lahore'])
def test_home_search_by_name_or_city(client, query):
    r = client.post('/', data={'search_query': query})
    assert b'General Hospital' in r.data


def test_home_search_no_match(client):
    r = client.post('/', data={'search_query': 'Nowhere'})
    assert b'General Hospital' not in r.data
    assert b'No Record' in r.data


def test_home_empty_search_shows_all(client):
    assert b'General Hospital' in client.post('/', data={'search_query': '  '}).data


# ------------------------------------------------------------ doctors

def test_doctors_list_shows_hospital_name(client):
    r = client.get('/fdoctors')
    assert r.status_code == 200
    assert b'Sadaf' in r.data
    assert b'General Hospital' in r.data


@pytest.mark.parametrize('query', ['Sadaf', 'MBBS', 'Royal College'])
def test_doctors_search_by_name_specialization_description(client, query):
    assert b'Sadaf' in client.post('/fdoctors', data={'search_query': query}).data


def test_doctors_search_no_match(client):
    r = client.post('/fdoctors', data={'search_query': 'zzz'})
    assert b'Sadaf' not in r.data
    assert b'No Record' in r.data


def test_doctors_empty_search_shows_all(client):
    assert b'Sadaf' in client.post('/fdoctors', data={'search_query': ''}).data


def test_deleted_hospital_removes_its_doctors_from_list(client, admin_client):
    admin_client.post('/hospitals/delete/3')
    r = client.get('/fdoctors')
    assert b'Sadaf' not in r.data and b'No Record' in r.data


# ------------------------------------------------------------ facilities

def test_facilities_list(client):
    r = client.get('/ffacilities')
    assert r.status_code == 200
    assert b'Radiance Imaging Center' in r.data
    assert b'MRI' in r.data
    assert b'General Hospital' in r.data


@pytest.mark.parametrize('query', ['Radiance', 'Ultrasound', 'radiologists'])
def test_facilities_search(client, query):
    assert b'Radiance' in client.post('/ffacilities', data={'search_query': query}).data


def test_facilities_search_no_match(client):
    r = client.post('/ffacilities', data={'search_query': 'zzz'})
    assert b'Radiance' not in r.data
    assert b'No Record' in r.data


def test_facilities_empty_search_shows_all(client):
    assert b'Radiance' in client.post('/ffacilities', data={'search_query': ''}).data


# ------------------------------------------------------------ hospital detail

def test_hospital_detail_shows_doctors_and_facilities(client):
    r = client.get('/detail/3')
    assert r.status_code == 200
    for text in (b'General Hospital', b'04299268801', b'Sadaf', b'Radiance Imaging Center'):
        assert text in r.data


def test_hospital_detail_unknown_id(client):
    r = client.get('/detail/999')
    assert r.status_code == 404
    assert b'Page Not Found' in r.data


def test_hospital_detail_without_doctors_or_facilities(client, admin_client):
    admin_client.post('/doctors/delete/3')
    admin_client.post('/facilities/delete/3')
    r = client.get('/detail/3')
    assert r.status_code == 200 and r.data.count(b'No Record') == 2


# ------------------------------------------------------------ booking pages (guest)

def test_book_doctor_page_as_guest_asks_to_login(client):
    r = client.get('/book_doctor/3')
    assert r.status_code == 200
    assert b'Sadaf' in r.data
    assert b'10:10 AM' in r.data
    assert b'Please Login As User' in r.data


def test_book_facility_page_as_guest_asks_to_login(client):
    r = client.get('/book_facilities/3')
    assert r.status_code == 200
    assert b'Radiance Imaging Center' in r.data
    assert b'Please Login As User' in r.data


@pytest.mark.parametrize('url', ['/book_doctor/999', '/book_facilities/999'])
def test_booking_page_unknown_id_is_404(client, url):
    assert client.get(url).status_code == 404


# ------------------------------------------------------------ navigation / errors

def test_guest_nav_shows_login_and_register(client):
    r = client.get('/')
    assert b'Login' in r.data and b'Register' in r.data


def test_logged_in_nav_shows_account(user_client):
    r = user_client.get('/')
    assert b'Account' in r.data
    assert b'>Login<' not in r.data


def test_unknown_url_shows_404_page(client):
    assert b'404' in client.get('/does-not-exist').data


def test_unknown_url_returns_404_status(client):
    assert client.get('/does-not-exist').status_code == 404


def test_page_titles(client):
    assert b'<title>Doctors' in client.get('/fdoctors').data
    assert b'<title>General Hospital' in client.get('/detail/3').data


def test_facility_services_are_paired_with_fees(client):
    r = client.get('/ffacilities')
    assert b'MRI &middot; 3000' in r.data and b'X-rays &middot; 1500' in r.data


def test_static_images_served(client):
    r = client.get('/static/images/doct.jpg')
    assert r.status_code == 200
    r.close()
