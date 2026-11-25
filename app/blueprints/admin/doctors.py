"""Admin: manage specialists (doctors) with their fee and timings."""
from flask import render_template, request

from ...extensions import db
from ...forms import DoctorForm
from ...models import Appointment, Doctor
from ...services import appointments, catalog
from ...utils import int_arg, paginate, search_term
from ...utils.uploads import delete_image
from . import bp, delete, save, upcoming_note

NEW_DOCTOR = {'days': 'Mon,Tue,Wed,Thu,Fri', 'slot_minutes': 30}


@bp.get('/doctors')
def doctors():
    query = catalog.doctors(search_term(), specialization=request.args.get('specialization', ''),
                            hospital_id=int_arg('hospital'))
    return render_template('admin/doctors.html', page=paginate(query), hospitals=catalog.hospital_list(),
                           specializations=catalog.specializations())


@bp.route('/doctors/new', methods=['GET', 'POST'], endpoint='doctor_new')
@bp.route('/doctors/<int:id>/edit', methods=['GET', 'POST'], endpoint='doctor_edit')
def doctor_form(id=None):
    doctor = db.get_or_404(Doctor, id) if id else Doctor(**NEW_DOCTOR)
    form = DoctorForm(doctor)
    return save(form, doctor, 'Doctor', 'admin.doctors') or render_template('admin/doctor_form.html', form=form)


@bp.post('/doctors/<int:id>/delete')
def doctor_delete(id):
    doctor = db.get_or_404(Doctor, id)
    blocked_by = upcoming_note(appointments.upcoming_count(Appointment.doctor_id == id), doctor.name)
    if not blocked_by:
        delete_image(doctor.image)
    return delete(doctor, 'Doctor', 'admin.doctors', blocked_by)
