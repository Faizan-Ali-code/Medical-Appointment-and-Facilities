"""
Online Booking of Medical Appointments & Services.

Application factory: create_app() builds and configures a Flask app.
"""
import os
import secrets

from dotenv import load_dotenv
from flask import Flask, g, render_template, request, url_for

from .config import BASE_DIR, CONFIGS
from .extensions import csrf, db, limiter

load_dotenv(os.path.join(BASE_DIR, '.env'))

CDN = 'https://cdn.jsdelivr.net'


def create_app(config_name=None, **overrides):
    app = Flask(__name__, instance_path=os.path.join(BASE_DIR, 'instance'))
    config_name = config_name or os.getenv('APP_ENV', 'development')
    app.config.from_object(CONFIGS[config_name]())
    app.config.update(overrides)

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    _register_blueprints(app)
    _register_hooks(app)
    _register_error_handlers(app)

    from .seed import register_cli
    register_cli(app)
    return app


def _register_blueprints(app):
    from .blueprints import ALL
    for bp in ALL:
        app.register_blueprint(bp)


def content_security_policy(nonce):
    """Scripts and styles only from this site and the pinned CDN files; the one inline script needs the nonce."""
    return '; '.join((
        "default-src 'self'",
        f"script-src 'self' {CDN} 'nonce-{nonce}'",
        f"style-src 'self' {CDN}",
        f"font-src 'self' {CDN}",
        "img-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ))


def _register_hooks(app):
    from .utils.auth import load_current_user

    @app.before_request
    def make_csp_nonce():
        g.csp_nonce = secrets.token_urlsafe(16)

    app.before_request(load_current_user)

    @app.context_processor
    def inject_globals():
        return {'current_user': g.get('user'), 'csp_nonce': g.get('csp_nonce', '')}

    @app.template_filter('longdate')
    def longdate(value):
        return value.strftime('%d %B, %Y') if value else '-'

    @app.template_global()
    def page_url(number):
        """Current URL with ?page=number, keeping the search and filter parameters."""
        args = {k: v for k, v in request.args.items() if k != 'page' and v}
        return url_for(request.endpoint, **(request.view_args or {}), **args, page=number)

    @app.template_test('pdf')
    def is_pdf(filename):
        return bool(filename) and filename.lower().endswith('.pdf')

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('Content-Security-Policy', content_security_policy(g.get('csp_nonce', '')))
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if request.is_secure:  # HSTS is only meaningful (and only honoured) over HTTPS
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response


def _register_error_handlers(app):
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return render_template('errors/error.html', code=400,
                               message='Your form has expired or is invalid. Please go back, refresh and try again.'), 400

    @app.errorhandler(405)
    def method_not_allowed(e):
        return render_template('errors/error.html', code=405,
                               message='This action must be submitted with a button, not opened as a link.'), 405

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template('errors/error.html', code=413,
                               message='The uploaded file is too large (max 5 MB).'), 413

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template('errors/error.html', code=429,
                               message='Too many attempts from your network. Please wait a few minutes and try '
                                       'again.'), 429

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template('errors/error.html', code=500,
                               message='Something went wrong. Please try again.'), 500
