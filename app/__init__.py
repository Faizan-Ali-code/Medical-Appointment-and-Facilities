"""MediBook: book doctors, lab tests and scans at hospitals, clinics and laboratories."""
from flask import Flask, g, render_template, request, url_for
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException

from .config import Config
from .extensions import csrf, db
from .utils import timeslots
from .utils.auth import load_current_user

ERROR_TEXT = {
    403: ('Not allowed', 'You do not have permission to open this page.'),
    404: ('Page not found', 'The page you are looking for does not exist or has been removed.'),
    405: ('Not allowed', 'This page cannot be opened that way.'),
    413: ('File too large', 'The file is larger than 5 MB. Please choose a smaller one.'),
    500: ('Something went wrong', 'An unexpected error happened. Please try again.'),
}


def create_app(**overrides):
    """Build the application. `overrides` replace settings from Config (the tests use this)."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(overrides)

    db.init_app(app)
    csrf.init_app(app)

    from .blueprints import account, admin, auth, public
    for blueprint in (public.bp, auth.bp, account.bp, admin.bp):
        app.register_blueprint(blueprint)

    from .seed import register_commands
    register_commands(app)

    app.before_request(load_current_user)
    _register_template_helpers(app)
    _register_error_pages(app)
    return app


def _register_template_helpers(app):
    @app.context_processor
    def current_user():
        return {'current_user': g.get('user')}

    @app.template_filter()
    def longdate(date):
        """Mon, 03 Mar 2025"""
        return date.strftime('%a, %d %b %Y')

    @app.template_filter()
    def money(amount):
        """Rs. 1,500"""
        return f'Rs. {amount:,}'

    def page_url(number):
        """The current list page with all its filters, at another page number."""
        return url_for(request.endpoint, **{**request.view_args, **request.args.to_dict(), 'page': number})

    app.add_template_filter(timeslots.format_time, 'clock')
    app.add_template_global(page_url)
    app.add_template_global(timeslots.today, 'today')


def _register_error_pages(app):
    def error_page(code, title=None, text=None):
        default_title, default_text = ERROR_TEXT.get(code, ERROR_TEXT[500])
        return render_template('errors/error.html', code=code, title=title or default_title,
                               text=text or default_text), code

    @app.errorhandler(CSRFError)
    def csrf_error(_error):
        return error_page(400, 'Form expired', 'Please go back, refresh the page and send the form again.')

    @app.errorhandler(HTTPException)   # includes 500, which Flask raises for any unexpected error
    def http_error(error):
        return error_page(error.code, *ERROR_TEXT.get(error.code, (error.name, error.description)))
