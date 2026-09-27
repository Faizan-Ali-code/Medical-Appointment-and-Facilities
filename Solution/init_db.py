"""
Create the database tables and load the sample data.

Usage:
    venv\\Scripts\\python init_db.py          # create tables + seed (only if empty)
    venv\\Scripts\\python init_db.py --reset  # drop everything and recreate

Same as:  venv\\Scripts\\flask --app run init-db [--reset]
"""
import sys

from app import create_app
from app.extensions import db
from app.seed import init_db


def main():
    app = create_app()
    with app.app_context():
        seeded = init_db(reset='--reset' in sys.argv)
        url = db.engine.url.render_as_string(hide_password=True)
    print(f'Database ready: {url}' + ('' if seeded else ' (already had data)'))


if __name__ == '__main__':
    main()
