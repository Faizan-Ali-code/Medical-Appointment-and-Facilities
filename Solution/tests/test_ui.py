"""UI features from Step 4: hero, dashboard, account overview, theme, confirm dialog, validation."""
import pathlib
import re

import pytest

TEMPLATES = pathlib.Path(__file__).resolve().parent.parent / 'app' / 'templates'
FUTURE = {'date': '2030-01-01', 'slot': '10:10 AM'}


# ------------------------------------------------------------ home page hero

def test_home_hero_shows_counts(client):
    html = client.get('/').get_data(as_text=True)
    assert 'Book doctors and medical tests online' in html
    counts = re.findall(r'<div class="fs-3 fw-bold">(\d+)</div>', html)
    assert counts == ['1', '1', '1']  # hospitals, doctors, facilities


def test_home_counts_follow_the_data(client, admin_client):
    admin_client.post('/doctors/delete/3')
    html = client.get('/').get_data(as_text=True)
    assert re.findall(r'<div class="fs-3 fw-bold">(\d+)</div>', html) == ['1', '0', '1']
    assert '0 doctors' in html and '1 facility<' in html


def test_home_search_shows_result_count(client):
    html = client.get('/?search_query=lahore').get_data(as_text=True)
    assert re.search(r'1 result\s+for "lahore"', html)
    assert re.search(r'0 results\s+for "zzz"', client.get('/?search_query=zzz').get_data(as_text=True))


# ------------------------------------------------------------ admin dashboard

def test_dashboard_requires_admin(client, user_client):
    assert b'Login Form' in client.get('/dashboard', follow_redirects=True).data
    assert user_client.get('/dashboard').status_code == 302


def _tiles(html):
    return dict((label, int(value)) for value, label in
                re.findall(r'<div class="stat-value">(\d+)</div>\s*<div class="stat-label">([^<]+)</div>', html))


def test_dashboard_stat_tiles(admin_client):
    html = admin_client.get('/dashboard').get_data(as_text=True)
    assert _tiles(html) == {'Hospitals': 1, 'Doctors': 1, 'Facilities': 1, 'Registered users': 1,
                            'Upcoming appointments': 0, 'Tests awaiting result': 1}


def test_dashboard_lists_upcoming_and_pending(admin_client, user_client):
    user_client.post('/book_doctor/3', data=FUTURE)
    html = admin_client.get('/dashboard').get_data(as_text=True)
    assert _tiles(html)['Upcoming appointments'] == 1
    assert '01 January, 2030' in html
    assert 'Radiance Imaging Center' in html  # the pending seed test booking


def test_dashboard_empty_states(admin_client):
    admin_client.post('/res_positive/1')
    html = admin_client.get('/dashboard').get_data(as_text=True)
    assert 'No upcoming appointments' in html
    assert 'All test results are up to date' in html


def test_dashboard_in_admin_menu_and_account(admin_client):
    assert b'href="/dashboard"' in admin_client.get('/account').data


# ------------------------------------------------------------ user account overview

def test_user_account_overview(user_client):
    user_client.post('/book_doctor/3', data=FUTURE)
    html = user_client.get('/account').get_data(as_text=True)
    assert 'Upcoming appointments' in html and '01 January, 2030' in html
    assert 'Latest test bookings' in html and 'Pending' in html


def test_user_account_overview_empty(other_user_client):
    html = other_user_client.get('/account').get_data(as_text=True)
    assert 'No upcoming appointments' in html and 'No test bookings yet' in html


def test_past_bookings_are_not_upcoming(user_client):
    # the seed doctor booking is on 2023-08-01, so it is not in the "Upcoming" card
    html = user_client.get('/account').get_data(as_text=True)
    upcoming_card = html.split('Upcoming appointments')[1].split('Latest test bookings')[0]
    assert 'No upcoming appointments' in upcoming_card and '2023' not in upcoming_card


def test_result_shown_in_account(admin_client, user_client):
    admin_client.post('/res_negitive/1')
    assert 'Negative' in user_client.get('/account').get_data(as_text=True)


# ------------------------------------------------------------ layout features

def test_layout_assets(client):
    html = client.get('/').get_data(as_text=True)
    assert 'data-theme-toggle' in html               # dark mode button
    assert "localStorage.getItem('theme')" in html    # theme applied before paint
    assert 'id="confirmModal"' in html                # shared confirm dialog
    assert '/static/js/app.js' in html and '/static/img/favicon.svg' in html
    assert 'Skip to content' in html


@pytest.mark.parametrize('path', ['/static/js/app.js', '/static/img/favicon.svg', '/static/css/main.css'])
def test_static_assets_served(client, path):
    assert client.get(path).status_code == 200


def test_delete_buttons_are_post_forms_with_confirm_dialog(admin_client):
    html = admin_client.get('/hospitals').get_data(as_text=True)
    assert re.search(r'<form method="post" action="/hospitals/delete/3" class="d-inline"\s+data-confirm="Delete this hospital', html)
    assert 'href="/hospitals/delete/3"' not in html
    assert 'onclick=' not in html


def test_logout_is_a_post_button(user_client):
    html = user_client.get('/').get_data(as_text=True)
    assert re.search(r'<form method="post" action="/logout">', html)
    assert 'href="/logout"' not in html


def test_admin_list_pluralization(admin_client):
    assert '1 hospital<' in admin_client.get('/hospitals').get_data(as_text=True)
    assert '1 facility<' in admin_client.get('/facilities').get_data(as_text=True)


def test_status_badge_has_icon_not_only_colour(user_client):
    assert 'bi-hourglass-split me-1"></i>Pending' in user_client.get('/user_facbookings').get_data(as_text=True)


def test_templates_have_no_light_only_classes():
    for path in TEMPLATES.rglob('*.html'):
        text = path.read_text(encoding='utf-8')
        assert 'table-light' not in text, path
        assert 'text-bg-light' not in text, path


def _post_forms():
    """(path, opening tag, body) for every POST form in the templates."""
    for path in TEMPLATES.rglob('*.html'):
        for tag, body in re.findall(r'(<form[^>]*method="post"[^>]*>)(.*?)</form>',
                                    path.read_text(encoding='utf-8'), re.S):
            yield path, tag, body


def test_all_post_forms_have_csrf_token():
    forms = list(_post_forms())
    assert len(forms) >= 10
    for path, tag, body in forms:
        assert 'csrf' in body, f'{path}: {tag}'


def test_data_entry_forms_use_client_validation():
    for path, tag, body in _post_forms():
        is_button_form = 'type="submit"' in body and '<input type="text"' not in body and 'ui.field' not in body
        if not is_button_form:
            assert 'needs-validation' in tag, path
