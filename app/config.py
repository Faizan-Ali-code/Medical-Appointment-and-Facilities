"""Configuration classes. Pick one with the APP_ENV environment variable."""
import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DEV_SECRET = 'dev-secret-change-me'
# Placeholder values that must never be used as a real SECRET_KEY.
WEAK_SECRETS = {DEV_SECRET, 'change-this-secret-key', 'secret', 'changeme'}


def _database_url():
    url = os.getenv('DATABASE_URL')
    if url:
        return url
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    return 'sqlite:///' + os.path.join(INSTANCE_DIR, 'medical.db')


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    # Public pictures (hospital covers, doctor photos): served as static files.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'images')
    # Patient files (prescriptions, reports): outside static/, served only through an authorised route.
    PRIVATE_UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB uploads
    MIN_PASSWORD_LENGTH = 8
    PASSWORD_HASH_METHOD = 'scrypt'  # werkzeug default: slow on purpose, hard to brute-force

    # login protection: per account (database) and per client IP (Flask-Limiter)
    LOGIN_MAX_FAILURES = 5          # failed logins in a row before the account is locked
    LOGIN_LOCK_MINUTES = 15         # how long the lock lasts
    LOGIN_RATE_LIMIT = '10 per minute; 50 per hour'
    RATELIMIT_STORAGE_URI = 'memory://'   # use a shared store (e.g. redis://) when running several processes
    RATELIMIT_HEADERS_ENABLED = True

    # cookies / sessions / CSRF
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(minutes=30)  # idle timeout: refreshed on every request
    SESSION_ABSOLUTE_HOURS = 12     # a login never lasts longer than this, active or not
    WTF_CSRF_TIME_LIMIT = None      # token valid for the whole session

    # seeded accounts: None = a random password is generated and printed by `flask init-db`
    SEED_ADMIN_PASSWORD = None
    SEED_USER_PASSWORD = None
    DEMO_PATIENT_PASSWORD = None

    def __init__(self):
        # evaluated on instantiation so .env / test env vars are respected
        self.SQLALCHEMY_DATABASE_URI = _database_url()
        self.SECRET_KEY = os.getenv('SECRET_KEY', DEV_SECRET)


class DevelopmentConfig(BaseConfig):
    def __init__(self):
        super().__init__()
        # The Werkzeug debugger allows code execution; it is opt-in (FLASK_DEBUG=1) and run.py refuses to expose it.
        self.DEBUG = os.getenv('FLASK_DEBUG') == '1'


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False  # CSRF has its own tests that switch it back on
    RATELIMIT_ENABLED = False  # the rate-limit test switches it back on
    PASSWORD_HASH_METHOD = 'pbkdf2:sha256:1000'  # fast hashing so the test suite stays quick
    SEED_ADMIN_PASSWORD = 'admin-pass-1'
    SEED_USER_PASSWORD = 'user-pass-1'
    DEMO_PATIENT_PASSWORD = 'patient-pass-1'


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    def __init__(self):
        super().__init__()
        if self.SECRET_KEY in WEAK_SECRETS or len(self.SECRET_KEY) < 32:
            raise RuntimeError('Set a random SECRET_KEY of at least 32 characters before running in production '
                               '(setup.bat writes one to .env).')


CONFIGS = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}
