"""Start the local development server:  venv\\Scripts\\python run.py

For a real deployment use wsgi.py with a production server (see README, "Deployment").
"""
import ipaddress
import os

from app import create_app
from app.extensions import db
from app.migrations import upgrade_schema

app = create_app()

# bring an older database up to date (adds new columns and constraints; never deletes data)
with app.app_context():
    db.create_all()
    for change in upgrade_schema():
        app.logger.warning('Database upgraded: added %s', change)


def is_loopback(host):
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    if app.debug and not is_loopback(host):
        raise SystemExit('Refusing to start: FLASK_DEBUG=1 enables the Werkzeug debugger, which must never be '
                         f'reachable from other machines (HOST={host}). Use 127.0.0.1 or turn debug off.')
    app.run(host=host, port=int(os.getenv('PORT', '5000')))
