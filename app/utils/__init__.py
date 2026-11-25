"""Small helpers shared by the views."""
from flask import current_app, request

from ..extensions import db


def search_term():
    """The search box value (?q=), stripped."""
    return request.args.get('q', '').strip()


def int_arg(name):
    """A whole-number filter from the query string (?city=3), or None."""
    return request.args.get(name, type=int)


def is_safe_path(target):
    """True for a path on this site, so a login can never redirect to another website."""
    return bool(target) and target.startswith('/') and not target.startswith('//') and '\\' not in target


def back_to(default):
    """Where to go after a button on a list was used: the list page it was pressed on (the form's hidden
    `next` field), or `default`."""
    target = request.form.get('next')
    return target if is_safe_path(target) else default


def paginate(query, size='ROWS_PER_PAGE'):
    """One page of a SELECT, chosen by ?page=N. A page number past the end shows the last page."""
    number = max(request.args.get('page', 1, type=int), 1)
    per_page = current_app.config[size]
    page = db.paginate(query, page=number, per_page=per_page, error_out=False)
    if page.pages and number > page.pages:
        page = db.paginate(query, page=page.pages, per_page=per_page, error_out=False)
    return page
