"""Admin: manage user and admin accounts."""
from flask import g, render_template, request

from ...extensions import db
from ...forms import UserForm
from ...models import Appointment, User
from ...services import appointments, catalog
from ...utils import paginate, search_term
from . import bp, delete, save, upcoming_note


@bp.get('/users')
def users():
    query = catalog.users(search_term(), request.args.get('role', ''))
    return render_template('admin/users.html', page=paginate(query), roles=User.ROLES)


@bp.route('/users/new', methods=['GET', 'POST'], endpoint='user_new')
@bp.route('/users/<int:id>/edit', methods=['GET', 'POST'], endpoint='user_edit')
def user_form(id=None):
    user = db.get_or_404(User, id) if id else User(role=User.USER)
    form = UserForm(user)
    return save(form, user, 'User', 'admin.users') or render_template('admin/user_form.html', form=form)


@bp.post('/users/<int:id>/delete')
def user_delete(id):
    user = db.get_or_404(User, id)
    if user.id == g.user.id:
        blocked_by = 'You cannot delete your own account.'
    else:
        blocked_by = upcoming_note(appointments.upcoming_count(Appointment.user_id == id), user.name)
    return delete(user, 'User', 'admin.users', blocked_by)
