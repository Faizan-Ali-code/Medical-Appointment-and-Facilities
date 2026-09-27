"""
Security behaviour from Step 5 that needs the real CSRF check switched on
(the rest of the suite runs with WTF_CSRF_ENABLED = False for simplicity).
"""
import re

import pytest

from conftest import ADMIN, USER


@pytest.fixture
def csrf_app(app):
    app.config['WTF_CSRF_ENABLED'] = True
    yield app
    app.config['WTF_CSRF_ENABLED'] = False


def token_from(html):
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, 'no CSRF token on the page'
    return match.group(1)


def csrf_login(client, email, password):
    token = token_from(client.get('/login').get_data(as_text=True))
    return client.post('/login', data={'email': email, 'password': password, 'csrf_token': token},
                       follow_redirects=False)


def test_login_without_token_is_rejected(csrf_app):
    c = csrf_app.test_client()
    r = c.post('/login', data={'email': USER[0], 'password': USER[1]})
    assert r.status_code == 400 and b'form has expired or is invalid' in r.data


def test_login_with_token_works(csrf_app):
    c = csrf_app.test_client()
    assert csrf_login(c, *USER).status_code == 302


def test_forged_delete_from_another_site_is_blocked(csrf_app, rows):
    """A logged-in admin visits an evil page that auto-submits a form to /hospitals/delete/3."""
    c = csrf_app.test_client()
    csrf_login(c, *ADMIN)
    r = c.post('/hospitals/delete/3')  # no token: the attacker can't read it
    assert r.status_code == 400
    assert len(rows('SELECT * FROM hospitals')) == 1


def test_wrong_token_is_rejected(csrf_app, rows):
    c = csrf_app.test_client()
    csrf_login(c, *ADMIN)
    assert c.post('/hospitals/delete/3', data={'csrf_token': 'forged'}).status_code == 400
    assert len(rows('SELECT * FROM hospitals')) == 1


def test_delete_with_page_token_works(csrf_app, rows):
    c = csrf_app.test_client()
    csrf_login(c, *ADMIN)
    token = token_from(c.get('/hospitals').get_data(as_text=True))
    r = c.post('/hospitals/delete/3', data={'csrf_token': token})
    assert b'Hospital deleted' in r.data
    assert rows('SELECT * FROM hospitals') == []


def test_booking_with_token_works(csrf_app, rows):
    c = csrf_app.test_client()
    csrf_login(c, *USER)
    token = token_from(c.get('/book_doctor/3').get_data(as_text=True))
    r = c.post('/book_doctor/3', data={'date': '2030-01-01', 'slot': '10:10 AM', 'csrf_token': token})
    assert b'Booking Successful' in r.data


def test_logout_needs_token(csrf_app):
    c = csrf_app.test_client()
    csrf_login(c, *USER)
    assert c.post('/logout').status_code == 400
    token = token_from(c.get('/account').get_data(as_text=True))
    assert c.post('/logout', data={'csrf_token': token}, follow_redirects=False).status_code == 302
    assert c.get('/account').status_code == 302


def test_search_forms_are_get_and_need_no_token(csrf_app):
    assert b'Sadaf' in csrf_app.test_client().get('/fdoctors?search_query=sadaf').data


# ------------------------------------------------------------ headers / cookies

@pytest.mark.parametrize('url', ['/', '/login', '/does-not-exist'])
def test_security_headers(client, url):
    r = client.get(url)
    assert r.headers['X-Content-Type-Options'] == 'nosniff'
    assert r.headers['X-Frame-Options'] == 'DENY'
    assert r.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'


def test_session_cookie_flags(client):
    from conftest import login
    r = login(client, *USER)
    cookie = r.headers['Set-Cookie']
    assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie


def test_password_hash_never_rendered(admin_client, rows):
    stored = rows('SELECT password FROM users WHERE id = 1')[0]['password']
    for url in ('/users', '/user_edit/1', '/dashboard', '/account'):
        assert stored not in admin_client.get(url).get_data(as_text=True)
