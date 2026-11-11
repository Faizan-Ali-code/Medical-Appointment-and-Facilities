"""Login, register, logout."""
import pytest

from conftest import ADMIN, USER, login

NEW_USER = {'name': 'Ali', 'email': 'ali@test.com', 'password': 'secret1', 'phone': '0300',
            'city': 'Karachi', 'role': 'user'}


def test_login_page(client):
    r = client.get('/login')
    assert r.status_code == 200
    assert b'Login Form' in r.data


@pytest.mark.parametrize('creds', [USER, ADMIN])
def test_login_success_redirects_to_account(client, creds):
    r = login(client, *creds)
    assert r.status_code == 302
    assert r.headers['Location'].endswith('/account')


@pytest.mark.parametrize('email,password', [
    ('user@yahoo.com', 'wrong'),
    ('nobody@yahoo.com', 'user'),
])
def test_login_failure(client, email, password):
    r = login(client, email, password)
    assert r.status_code == 200
    assert b'Email or Password is Incorrect' in r.data


def test_register_page(client):
    r = client.get('/register')
    assert r.status_code == 200
    assert b'Register Form' in r.data


def test_register_creates_user_and_can_login(client, rows):
    r = client.post('/register', data=NEW_USER)
    assert b'Your Account Is Created' in r.data
    saved = rows('SELECT * FROM users WHERE email = :e', e='ali@test.com')
    assert len(saved) == 1 and saved[0]['city'] == 'Karachi'
    assert login(client, 'ali@test.com', 'secret1').status_code == 302


def test_register_missing_field_keeps_input(client, rows):
    r = client.post('/register', data={**NEW_USER, 'city': ''})
    assert b'Please Fill All The Fields' in r.data
    assert b'value="ali@test.com"' in r.data
    assert rows("SELECT * FROM users WHERE email = 'ali@test.com'") == []


def test_register_duplicate_email(client, rows):
    r = client.post('/register', data={**NEW_USER, 'email': 'user@yahoo.com'})
    assert b'Already In Use' in r.data
    assert len(rows("SELECT * FROM users WHERE email = 'user@yahoo.com'")) == 1


def test_logout_clears_session(user_client):
    r = user_client.post('/logout', follow_redirects=False)
    assert r.status_code == 302 and r.headers['Location'].endswith('/login')
    r = user_client.get('/account')
    assert r.status_code == 302  # no longer logged in


def test_register_cannot_choose_admin_role(client, rows):
    client.post('/register', data={**NEW_USER, 'role': 'admin'})
    assert rows("SELECT role FROM users WHERE email = 'ali@test.com'")[0]['role'] == 'user'
    assert b'name="role"' not in client.get('/register').data


def test_password_is_not_stored_in_plain_text(client, rows):
    client.post('/register', data=NEW_USER)
    stored = rows("SELECT password FROM users WHERE email = 'ali@test.com'")[0]['password']
    assert stored != 'secret1' and stored.startswith(('scrypt:', 'pbkdf2:'))


def test_seed_passwords_are_hashed(rows):
    assert all(r['password'].startswith(('scrypt:', 'pbkdf2:')) for r in rows('SELECT password FROM users'))


def test_register_rejects_short_password(client, rows):
    r = client.post('/register', data={**NEW_USER, 'password': '12345'})
    assert b'at least 6 characters' in r.data
    assert rows("SELECT * FROM users WHERE email = 'ali@test.com'") == []


def test_email_is_case_insensitive(client, rows):
    client.post('/register', data={**NEW_USER, 'email': 'Ali@Test.COM'})
    assert rows("SELECT email FROM users WHERE name = 'Ali'")[0]['email'] == 'ali@test.com'
    assert b'Already In Use' in client.post('/register', data={**NEW_USER, 'email': 'ALI@test.com'}).data
    assert login(client, 'ALI@TEST.com', 'secret1').status_code == 302


def test_old_plain_text_password_is_upgraded_on_login(client, rows):
    """Rows imported from the original MySQL dump still hold plain-text passwords."""
    from conftest import _check_engine
    import sqlalchemy as sa
    with _check_engine.begin() as conn:
        conn.execute(sa.text("UPDATE users SET password = 'user' WHERE id = 1"))
    assert login(client, 'user@yahoo.com', 'wrong').status_code == 200
    assert rows('SELECT password FROM users WHERE id = 1')[0]['password'] == 'user'  # unchanged on failure
    assert login(client, 'user@yahoo.com', 'user').status_code == 302
    assert rows('SELECT password FROM users WHERE id = 1')[0]['password'].startswith('pbkdf2:')
    assert login(client.application.test_client(), 'user@yahoo.com', 'user').status_code == 302


def test_user_with_empty_password_cannot_login(client):
    from conftest import _check_engine
    import sqlalchemy as sa
    with _check_engine.begin() as conn:
        conn.execute(sa.text("UPDATE users SET password = NULL WHERE id = 1"))
    assert login(client, 'user@yahoo.com', '').status_code == 200


def test_login_starts_a_fresh_session(client):
    with client.session_transaction() as s:
        s['planted'] = 'x'  # e.g. a fixated session from an attacker
    login(client, 'user@yahoo.com', 'user')
    with client.session_transaction() as s:
        assert 'planted' not in s and 'user_id' in s
