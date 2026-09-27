"""Configuration classes. Pick one with the APP_ENV environment variable."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DEV_SECRET = 'dev-secret-change-me'


def _database_url():
    url = os.getenv('DATABASE_URL')
    if url:
        return url
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    return 'sqlite:///' + os.path.join(INSTANCE_DIR, 'medical.db')


class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'images')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB uploads
    MIN_PASSWORD_LENGTH = 6
    PASSWORD_HASH_METHOD = 'scrypt'  # werkzeug default: slow on purpose, hard to brute-force

    # cookies / CSRF
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_TIME_LIMIT = None  # token valid for the whole session

    def __init__(self):
        # evaluated on instantiation so .env / test env vars are respected
        self.SQLALCHEMY_DATABASE_URI = _database_url()
        self.SECRET_KEY = os.getenv('SECRET_KEY', DEV_SECRET)


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False  # CSRF has its own tests that switch it back on
    PASSWORD_HASH_METHOD = 'pbkdf2:sha256:1000'  # fast hashing so the test suite stays quick


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    def __init__(self):
        super().__init__()
        if self.SECRET_KEY == DEV_SECRET:
            raise RuntimeError('Set a strong SECRET_KEY environment variable before running in production.')


CONFIGS = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}
