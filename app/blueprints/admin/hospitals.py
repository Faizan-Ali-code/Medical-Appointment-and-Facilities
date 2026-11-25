"""Admin: manage hospitals, clinics and laboratories."""
from flask import render_template, request

from ...extensions import db
from ...forms import HospitalForm
from ...models import Hospital
from ...services import appointments, catalog
from ...utils import int_arg, paginate, search_term
from ...utils.uploads import delete_image
from . import bp, delete, save, upcoming_note


@bp.get('/hospitals')
def hospitals():
    query = catalog.hospitals(search_term(), int_arg('city'), request.args.get('type', ''))
    return render_template('admin/hospitals.html', page=paginate(query), cities=catalog.city_list(),
                           kinds=Hospital.KINDS)


@bp.route('/hospitals/new', methods=['GET', 'POST'], endpoint='hospital_new')
@bp.route('/hospitals/<int:id>/edit', methods=['GET', 'POST'], endpoint='hospital_edit')
def hospital_form(id=None):
    hospital = db.get_or_404(Hospital, id) if id else Hospital()
    form = HospitalForm(hospital)
    return (save(form, hospital, form.kind.data, 'admin.hospitals')
            or render_template('admin/hospital_form.html', form=form))


@bp.post('/hospitals/<int:id>/delete')
def hospital_delete(id):
    """Deleting a hospital also deletes its doctors and facilities, so none of them may have open bookings."""
    hospital = db.get_or_404(Hospital, id)
    blocked_by = upcoming_note(appointments.upcoming_count(appointments.in_hospital(hospital)), hospital.name)
    if not blocked_by:
        for picture in [hospital.image, *(doctor.image for doctor in hospital.doctors)]:
            delete_image(picture)
    return delete(hospital, hospital.kind, 'admin.hospitals', blocked_by)
