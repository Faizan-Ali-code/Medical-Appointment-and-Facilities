"""Admin: manage cities."""
from flask import render_template

from ...extensions import db
from ...forms import CityForm
from ...models import City
from ...services import catalog
from ...utils import paginate, search_term
from . import bp, delete, save


@bp.get('/cities')
def cities():
    return render_template('admin/cities.html', page=paginate(catalog.cities(search_term())))


@bp.route('/cities/new', methods=['GET', 'POST'], endpoint='city_new')
@bp.route('/cities/<int:id>/edit', methods=['GET', 'POST'], endpoint='city_edit')
def city_form(id=None):
    city = db.get_or_404(City, id) if id else City()
    form = CityForm(city)
    return save(form, city, 'City', 'admin.cities') or render_template('admin/city_form.html', form=form)


@bp.post('/cities/<int:id>/delete')
def city_delete(id):
    city = db.get_or_404(City, id)
    count = len(city.hospitals)
    blocked_by = count and (f'{city.name} still has {count} hospital(s), clinic(s) or lab(s). '
                            'Move or delete them first.')
    return delete(city, 'City', 'admin.cities', blocked_by)
