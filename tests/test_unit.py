"""Unit tests for models, services, config, error handlers and the CLI."""
import datetime
import io
import os

import pytest
from werkzeug.datastructures import FileStorage

from app import create_app
from app.config import CONFIGS
from app.extensions import db
from app.models import Doctor, Facility, FacilityBooking, User
from app.services import bookings as booking_service
from app.services.bookings import BookingError
from app.utils.uploads import IMAGES, IMAGES_AND_PDF, UploadError, save_upload
from conftest import PDF_BYTES, PNG_BYTES


# ------------------------------------------------------------ models

def test_facility_service_fees_pairs_and_pads():
    f = Facility(services='A, B ,C', fee='10, 20')
    assert f.service_list == ['A', 'B', 'C']
    assert f.service_fees == [('A', '10'), ('B', '20'), ('C', '')]


def test_empty_lists():
    assert Doctor(slots=None).slot_list == []
    assert Facility(services='', fee=None).service_fees == []


def test_hospital_name_fallback():
    assert Doctor().hospital_name == 'Not Found'
    assert Facility().hospital_name == 'Not Found'


def test_status_label():
    assert FacilityBooking(status=0).status_label == 'Pending'
    assert FacilityBooking(status=1).status_label == 'Approved'


def test_is_admin():
    assert User(role='admin').is_admin and not User(role='user').is_admin


# ------------------------------------------------------------ services

def test_parse_date():
    assert booking_service.parse_date('2030-05-06') == datetime.date(2030, 5, 6)
    for bad in ('', None, '06-05-2030', 'x'):
        with pytest.raises(BookingError):
            booking_service.parse_date(bad)


def test_book_doctor_today_is_allowed(app):
    with app.app_context():
        user, doctor = db.session.get(User, 1), db.session.get(Doctor, 3)
        booking = booking_service.book_doctor(user, doctor, datetime.date.today(), '10:15 AM')
        assert booking.id is not None


# ------------------------------------------------------------ uploads

def _file(name, content=b'x'):
    return FileStorage(stream=io.BytesIO(content), filename=name)


@pytest.mark.parametrize('value', [None, _file('')])
def test_save_upload_nothing_uploaded(app, value):
    with app.test_request_context():
        assert save_upload(value) is None


@pytest.mark.parametrize('name,content', [
    ('photo.png', PNG_BYTES),
    ('photo.JPG', b'\xff\xd8\xff\xe0rest'),
    ('photo.jpeg', b'\xff\xd8\xff\xe0rest'),
    ('anim.gif', b'GIF89a....'),
    ('pic.webp', b'RIFF\x00\x00\x00\x00WEBPVP8 '),
])
def test_save_upload_accepts_real_images(app, upload_dir, name, content):
    with app.test_request_context():
        stored = save_upload(_file(name, content))
    assert os.path.exists(os.path.join(upload_dir, stored))
    assert len(stored.split('.')[0]) == 32  # random uuid name
    assert stored.endswith('.jpg' if name.lower().endswith(('jpg', 'jpeg')) else name.rsplit('.', 1)[1])


def test_save_upload_ignores_path_in_filename(app, upload_dir):
    with app.test_request_context():
        stored = save_upload(_file('../../evil name.png', PNG_BYTES))
    assert '/' not in stored and '\\' not in stored and '..' not in stored


@pytest.mark.parametrize('name,content,allowed', [
    ('x.exe', b'MZ', IMAGES),
    ('x.png', b'not png', IMAGES),
    ('x.pdf', PDF_BYTES, IMAGES),          # PDF not allowed for hospital/doctor images
    ('x.pdf', b'<html>', IMAGES_AND_PDF),
    ('noextension', PNG_BYTES, IMAGES),
])
def test_save_upload_rejects_bad_files(app, name, content, allowed):
    with app.test_request_context():
        with pytest.raises(UploadError):
            save_upload(_file(name, content), allowed=allowed)


def test_save_upload_pdf_allowed_when_asked(app):
    with app.test_request_context():
        assert save_upload(_file('r.pdf', PDF_BYTES), allowed=IMAGES_AND_PDF).endswith('.pdf')


# ------------------------------------------------------------ passwords

def test_password_hashing_roundtrip(app):
    with app.app_context():
        u = User()
        u.set_password('secret1')
        assert u.has_hashed_password and u.check_password('secret1') and not u.check_password('secret2')
        assert not u.check_password('')


def test_production_uses_scrypt(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'x' * 32)
    assert CONFIGS['production']().PASSWORD_HASH_METHOD == 'scrypt'


# ------------------------------------------------------------ config / factory

def test_database_url_from_environment(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'x' * 32)
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///from-env.db')
    assert CONFIGS['production']().SQLALCHEMY_DATABASE_URI == 'sqlite:///from-env.db'


def test_default_database_is_sqlite_in_instance_folder(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    uri = CONFIGS['development']().SQLALCHEMY_DATABASE_URI
    assert uri.startswith('sqlite:///')
    assert os.path.normpath(uri).endswith(os.path.join('instance', 'medical.db'))


def test_config_selected_by_app_env(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'x' * 32)
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    app = create_app()
    assert app.debug is False and app.testing is False
    assert app.config['SESSION_COOKIE_SECURE'] is True
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True and app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


def test_production_refuses_default_secret_key(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        CONFIGS['production']()


# ------------------------------------------------------------ error pages

def test_upload_too_large_returns_413(app, admin_client):
    big = (io.BytesIO(b'x' * (app.config['MAX_CONTENT_LENGTH'] + 1)), 'big.jpg')
    r = admin_client.post('/addhospital', data={'image': big}, content_type='multipart/form-data')
    assert r.status_code == 413 and b'too large' in r.data


def test_server_error_page(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'x' * 32)
    monkeypatch.setenv('DATABASE_URL', 'sqlite://')
    app = create_app('production')

    @app.route('/boom')
    def boom():
        raise RuntimeError('boom')

    r = app.test_client().get('/boom')
    assert r.status_code == 500 and b'Something went wrong' in r.data


# ------------------------------------------------------------ CLI

def test_init_db_cli(monkeypatch, tmp_path):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'cli.db'))
    app = create_app('testing')
    runner = app.test_cli_runner()
    first = runner.invoke(args=['init-db'])
    assert first.exit_code == 0 and 'Database ready' in first.output and 'already' not in first.output
    second = runner.invoke(args=['init-db'])
    assert 'already had data' in second.output
    third = runner.invoke(args=['init-db', '--reset'])
    assert third.exit_code == 0 and 'already' not in third.output
    with app.app_context():
        assert db.session.query(User).count() == 2
        db.engine.dispose()


def test_create_admin_cli(monkeypatch, tmp_path):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'admin.db'))
    app = create_app('testing')
    runner = app.test_cli_runner()
    runner.invoke(args=['init-db'])
    short = runner.invoke(args=['create-admin', '--email', 'x@y.com', '--name', 'X', '--password', '123'])
    assert short.exit_code != 0 and 'at least' in short.output
    new = runner.invoke(args=['create-admin', '--email', 'Boss@Y.com', '--name', 'Boss', '--password', 'secret99'])
    assert new.exit_code == 0 and 'Admin ready: boss@y.com' in new.output
    promote = runner.invoke(args=['create-admin', '--email', 'user@yahoo.com', '--name', 'U', '--password', 'secret99'])
    assert promote.exit_code == 0
    with app.app_context():
        boss = db.session.scalar(db.select(User).filter_by(email='boss@y.com'))
        assert boss.is_admin and boss.check_password('secret99')
        assert db.session.get(User, 1).is_admin
        db.engine.dispose()


def test_hash_passwords_cli(monkeypatch, tmp_path):
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///' + str(tmp_path / 'hash.db'))
    app = create_app('testing')
    runner = app.test_cli_runner()
    runner.invoke(args=['init-db'])
    with app.app_context():
        db.session.get(User, 1).password = 'plain-old'
        db.session.commit()
    out = runner.invoke(args=['hash-passwords'])
    assert 'Hashed 1 password(s).' in out.output
    with app.app_context():
        assert db.session.get(User, 1).check_password('plain-old')
        db.engine.dispose()
