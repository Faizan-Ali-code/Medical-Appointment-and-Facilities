"""Helpers shared by the blueprints."""
from flask import request


def search_term():
    """The search box value from a GET (?search_query=) or POST form, stripped."""
    return request.values.get('search_query', '').strip()


def safe_next(fallback):
    """The form's `next` URL if it is a path on this site, else `fallback` (prevents open redirects)."""
    target = request.form.get('next', '')
    if target.startswith('/') and not target.startswith('//') and '\\' not in target:
        return target
    return fallback


def form_values(*names):
    """Stripped values of the given form fields, as a dict."""
    return {name: request.form.get(name, '').strip() for name in names}
