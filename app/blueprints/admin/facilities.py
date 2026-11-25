"""Admin: manage the facilities (tests and scans) of each hospital, clinic or lab."""
from flask import render_template, request

from ...extensions import db
from ...forms import FacilityForm
from ...models import Appointment, Facility
from ...services import appointments, catalog
from ...utils import int_arg, paginate, search_term
from . import bp, delete, save, upcoming_note

NEW_FACILITY = {'days': 'Mon,Tue,Wed,Thu,Fri,Sat', 'slot_minutes': 15}


@bp.get('/facilities')
def facilities():
    query = catalog.facilities(search_term(), category=request.args.get('category', ''),
                               hospital_id=int_arg('hospital'))
    return render_template('admin/facilities.html', page=paginate(query), hospitals=catalog.hospital_list(),
                           categories=Facility.CATEGORIES)


@bp.route('/facilities/new', methods=['GET', 'POST'], endpoint='facility_new')
@bp.route('/facilities/<int:id>/edit', methods=['GET', 'POST'], endpoint='facility_edit')
def facility_form(id=None):
    facility = db.get_or_404(Facility, id) if id else Facility(**NEW_FACILITY)
    form = FacilityForm(facility)
    return (save(form, facility, 'Facility', 'admin.facilities')
            or render_template('admin/facility_form.html', form=form))


@bp.post('/facilities/<int:id>/delete')
def facility_delete(id):
    facility = db.get_or_404(Facility, id)
    blocked_by = upcoming_note(appointments.upcoming_count(Appointment.facility_id == id), facility.name)
    return delete(facility, 'Facility', 'admin.facilities', blocked_by)
