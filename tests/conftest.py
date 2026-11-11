"""
Shared pytest fixtures.

Tests talk to the app only through HTTP (Flask test client) and check the
database only through the `rows` helper (plain SQL). That way the same
tests keep working while the internals of the app are refactored.

Every test gets a fresh database with the sample data (app.seed).
"""
import os
import shutil
import sys
import tempfile

import pytest
import sqlalchemy as sa
from flask.testing import FlaskClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.seed import init_db  # noqa: E402

TMP_DIR = tempfile.mkdtemp(prefix='cs619-tests-')
DB_URL = 'sqlite:///' + os.path.join(TMP_DIR, 'test.db')
UPLOAD_DIR = os.path.join(TMP_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

USER = ('user@yahoo.com', 'user')
ADMIN = ('admin@yahoo.com', 'admin')


class Client(FlaskClient):
    """Test client whose POST follows redirects by default (the app uses Post/Redirect/Get)."""

    def post(self, *args, **kwargs):
        kwargs.setdefault('follow_redirects', True)
        return super().post(*args, **kwargs)


_app = create_app('testing', SQLALCHEMY_DATABASE_URI=DB_URL, UPLOAD_FOLDER=UPLOAD_DIR)
_app.test_client_class = Client
_check_engine = sa.create_engine(DB_URL)


def pytest_sessionfinish(session, exitstatus):
    _check_engine.dispose()
    with _app.app_context():
        db.engine.dispose()
    shutil.rmtree(TMP_DIR, ignore_errors=True)


# ---------------------------------------------------------------- fixtures

@pytest.fixture(autouse=True)
def fresh_db():
    with _app.app_context():
        init_db(reset=True)
    yield


@pytest.fixture
def app():
    return _app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, password):
    return client.post('/login', data={'email': email, 'password': password}, follow_redirects=False)


# smallest valid files, so uploads pass the content (magic bytes) check
PNG_BYTES = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4'
             b'\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
PDF_BYTES = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n'


def png(name='pic.png'):
    import io
    return (io.BytesIO(PNG_BYTES), name)


def register(client, email, password='secret1', **extra):
    data = {'name': 'Test', 'email': email, 'password': password, 'phone': '1', 'city': 'X'}
    data.update(extra)
    return client.post('/register', data=data)


@pytest.fixture
def user_client(app):
    c = app.test_client()
    assert login(c, *USER).status_code == 302
    return c


@pytest.fixture
def admin_client(app):
    c = app.test_client()
    assert login(c, *ADMIN).status_code == 302
    return c


@pytest.fixture
def other_user_client(app):
    """A second normal user (email other@test.com) who has no bookings."""
    c = app.test_client()
    register(c, 'other@test.com', 'other123')
    assert login(c, 'other@test.com', 'other123').status_code == 302
    return c


@pytest.fixture
def rows():
    """rows('SELECT ... WHERE x = :x', x=1) -> list of dicts."""
    def _rows(sql, **params):
        with _check_engine.connect() as conn:
            return [dict(r._mapping) for r in conn.execute(sa.text(sql), params)]
    return _rows


@pytest.fixture
def upload_dir():
    return UPLOAD_DIR
