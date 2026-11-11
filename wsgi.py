"""WSGI entry point for a production server, for example:

    set APP_ENV=production
    venv\\Scripts\\waitress-serve --listen=127.0.0.1:8080 wsgi:app

Run it behind a reverse proxy that terminates HTTPS (session cookies are Secure in production).
Run `flask --app run upgrade-db` after updating the code.
"""
from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app

app = create_app()
# Trust one proxy hop for the client address and scheme (rate limiting, HTTPS detection for HSTS).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
