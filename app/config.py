"""Application settings. SECRET_KEY and DATABASE_URL can be set in a .env file (see .env.example)."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-secret-key')

    # Without DATABASE_URL the app uses a SQLite file in the instance folder, so no database server is needed.
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'sqlite:///medibook.db'

    # Pictures of hospitals and doctors
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    CARDS_PER_PAGE = 9    # 3 x 3 grid on the public pages
    ROWS_PER_PAGE = 10    # tables
