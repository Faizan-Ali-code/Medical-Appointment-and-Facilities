"""
Admin area: manage hospitals, doctors, facilities, users and bookings.

Every route in this blueprint requires an admin (see `guard`). Add and edit
share one view function and one template per entity. "Delete" archives
hospitals, doctors, facilities and users (they disappear from every list) so
that patients' booking history is never lost.
"""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..extensions import db
from ..models import WEEKDAYS, Doctor, DoctorBooking, Facility, FacilityBooking, Hospital, User
from ..services import bookings as booking_service
from ..services import catalog, stats
from ..services.bookings import BookingError
from ..utils import form_values, safe_next, search_term
from ..utils.auth import admin_required, end_all_sessions
from ..utils.timeslots import format_slot, parse_slot, sort_key
from ..utils.uploads import UploadError, save_upload
from .account import update_profile

bp = Blueprint('admin', __name__)


@bp.before_request
@admin_required
def guard():
    """Runs before every admin route; admin_required redirects non-admins."""


def _save(obj, fields, duplicate_query, messages, image_required=False, extra=None, clean=None):
    """
    Shared add/edit logic. Returns True when the object was saved.
    `duplicate_query` finds another active row that would clash with this one (or None).
    `clean(form)` may normalise the form values in place and returns an error message or None.
    """
    is_new = obj.id is None
    form = form_values(*fields)
    if not all(form.values()):
        flash('Please Fill All The Fields', 'warning')
        return False
    if 'hospital_id' in form:
        hospital = db.session.get(Hospital, int(form['hospital_id'])) if form['hospital_id'].isdigit() else None
        if hospital is None or hospital.archived:
            flash('Please choose a hospital', 'warning')
            return False
        form['hospital_id'] = int(form['hospital_id'])
    problem = clean(form) if clean else None
    if problem:
        flash(problem, 'warning')
        return False
    duplicate = db.session.scalar(duplicate_query(form))
    if duplicate is not None and duplicate is not obj:
        flash(messages['duplicate'], 'danger')
        return False

    try:
        image = save_upload(request.files.get('image')) if hasattr(obj, 'image') else None
    except UploadError as e:
        flash(str(e), 'danger')
        return False
    if image_required and not image and not getattr(obj, 'image', None):
        flash('Please upload an image', 'warning')
        return False

    for field, value in form.items():
        setattr(obj, field, value)
    if extra:
        extra(obj)
    if image:
        obj.image = image
    if is_new:
        db.session.add(obj)
    db.session.commit()
    flash(messages['added' if is_new else 'updated'], 'success')
    return True


# ------------------------------------------------------------ form value checks

def _is_amount(text):
    try:
        return float(text) >= 0
    except ValueError:
        return False


def clean_doctor(form):
    """Slots must be times (stored as '09:30 AM', in time order, no repeats); the fee must be a number."""
    slots = [s.strip() for s in form['slots'].split(',') if s.strip()]
    parsed = [parse_slot(s) for s in slots]
    if not slots or None in parsed:
        bad = ', '.join(s for s, p in zip(slots, parsed) if p is None) or '(none)'
        return f'Time slots must be times such as 09:30 AM or 14:30, separated by commas. Not understood: {bad}'
    form['slots'] = ', '.join(sorted({format_slot(p) for p in parsed}, key=sort_key))
    if not _is_amount(form['fee']):
        return 'The fee must be a number (e.g. 1500).'
    return None


def clean_facility(form):
    """One fee per service, every fee a number."""
    services = [s.strip() for s in form['services'].split(',') if s.strip()]
    fees = [f.strip() for f in form['fee'].split(',') if f.strip()]
    if len(services) != len(fees):
        return f'Enter one fee per service: {len(services)} service(s) but {len(fees)} fee(s).'
    if not all(_is_amount(f) for f in fees):
        return 'Every fee must be a number (e.g. 1500, 800).'
    form['services'], form['fee'] = ', '.join(services), ', '.join(fees)
    return None


# ------------------------------------------------------------ dashboard

@bp.route('/dashboard')
def dashboard():
    return render_template('admin/dashboard.html', **stats.admin_overview())


# ------------------------------------------------------------ hospitals

HOSPITAL_FIELDS = ('name', 'city', 'address', 'phone', 'description')
HOSPITAL_MESSAGES = {'duplicate': 'This Hospital Is Already Added', 'added': 'Congrats, Hospital Is Added',
                     'updated': 'Hospital Info is Updated'}


@bp.route('/hospitals', methods=['GET', 'POST'])
def hospitals():
    term = search_term()
    return render_template('admin/hospitals/list.html', page=catalog.paginate(catalog.hospitals_query(term)),
                           term=term)


@bp.route('/addhospital', methods=['GET', 'POST'], endpoint='add_hospital')
@bp.route('/hospitals/edit/<int:id>', methods=['GET', 'POST'], endpoint='edit_hospital')
def hospital_form(id=None):
    hospital = catalog.get_active_or_404(Hospital, id) if id else Hospital()
    if request.method == 'POST':
        saved = _save(hospital, HOSPITAL_FIELDS,
                      lambda f: db.select(Hospital).filter_by(name=f['name'], archived=False),
                      HOSPITAL_MESSAGES, image_required=True)
        if saved:
            return redirect(url_for('admin.hospitals'))
    return render_template('admin/hospitals/form.html', hospital=hospital)


@bp.route('/hospitals/delete/<int:id>', methods=['POST'])
def delete_hospital(id):
    catalog.get_active_or_404(Hospital, id).archive()
    db.session.commit()
    flash('Hospital archived with its doctors and facilities; their bookings are kept', 'info')
    return redirect(url_for('admin.hospitals'))


# ------------------------------------------------------------ doctors

DOCTOR_FIELDS = ('name', 'hospital_id', 'specialization', 'fee', 'slots', 'description')
DOCTOR_MESSAGES = {'duplicate': 'This Doctor Is Already Added', 'added': 'Congrats, Your Doctor Is Added',
                   'updated': 'Doctor Info is Updated'}


def _set_days(doctor):
    chosen = [d for d in WEEKDAYS if d in request.form.getlist('days')]
    doctor.days = '' if len(chosen) in (0, len(WEEKDAYS)) else ','.join(chosen)


@bp.route('/doctors', methods=['GET', 'POST'])
def doctors():
    term = search_term()
    return render_template('admin/doctors/list.html', page=catalog.paginate(catalog.doctors_query(term)),
                           term=term)


@bp.route('/add_doctor', methods=['GET', 'POST'], endpoint='add_doctor')
@bp.route('/doctors/edit/<int:id>', methods=['GET', 'POST'], endpoint='edit_doctor')
def doctor_form(id=None):
    doctor = catalog.get_active_or_404(Doctor, id) if id else Doctor()
    if request.method == 'POST':
        saved = _save(doctor, DOCTOR_FIELDS,
                      lambda f: db.select(Doctor).filter_by(name=f['name'], hospital_id=f['hospital_id'],
                                                            archived=False),
                      DOCTOR_MESSAGES, image_required=True, extra=_set_days, clean=clean_doctor)
        if saved:
            return redirect(url_for('admin.doctors'))
    return render_template('admin/doctors/form.html', doctor=doctor, hospitals=catalog.hospital_choices(),
                           weekdays=WEEKDAYS)


@bp.route('/doctors/delete/<int:id>', methods=['POST'])
def delete_doctor(id):
    catalog.get_active_or_404(Doctor, id).archived = True
    db.session.commit()
    flash('Doctor archived; their bookings are kept', 'info')
    return redirect(url_for('admin.doctors'))


# ------------------------------------------------------------ facilities

FACILITY_FIELDS = ('hospital_id', 'name', 'description', 'services', 'fee', 'contact')
FACILITY_MESSAGES = {'duplicate': 'Facility already exists in the same hospital.',
                     'added': 'Facility added successfully!', 'updated': 'Facility Info is Updated'}


@bp.route('/facilities', methods=['GET', 'POST'])
def facilities():
    term = search_term()
    return render_template('admin/facilities/list.html',
                           page=catalog.paginate(catalog.facilities_query(term)), term=term)


@bp.route('/addfacility', methods=['GET', 'POST'], endpoint='add_facility')
@bp.route('/facilities/edit/<int:id>', methods=['GET', 'POST'], endpoint='edit_facility')
def facility_form(id=None):
    facility = catalog.get_active_or_404(Facility, id) if id else Facility()
    if request.method == 'POST':
        saved = _save(facility, FACILITY_FIELDS,
                      lambda f: db.select(Facility).filter_by(name=f['name'], hospital_id=f['hospital_id'],
                                                              archived=False),
                      FACILITY_MESSAGES, clean=clean_facility)
        if saved:
            return redirect(url_for('admin.facilities'))
    return render_template('admin/facilities/form.html', facility=facility,
                           hospitals=catalog.hospital_choices())


@bp.route('/facilities/delete/<int:id>', methods=['POST'])
def delete_facility(id):
    catalog.get_active_or_404(Facility, id).archived = True
    db.session.commit()
    flash('Facility archived; its bookings are kept', 'info')
    return redirect(url_for('admin.facilities'))


# ------------------------------------------------------------ users

@bp.route('/users', methods=['GET', 'POST'])
def users():
    term = search_term()
    return render_template('admin/users/list.html', page=catalog.paginate(catalog.normal_users_query(term)),
                           term=term)


@bp.route('/user_edit/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    user = catalog.get_active_or_404(User, id)
    if request.method == 'POST' and update_profile(user):
        flash('Congrats, Your User Is Updated', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/users/form.html', user=user)


@bp.route('/user_delete/<int:id>', methods=['POST'])
def delete_user(id):
    user = catalog.get_active_or_404(User, id)
    if user.id == g.user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    user.archived = True
    end_all_sessions(user)  # logged out everywhere, and login is refused from now on
    db.session.commit()
    flash('User account closed; their bookings are kept', 'info')
    return redirect(url_for('admin.users'))


# ------------------------------------------------------------ doctor bookings

@bp.route('/docbookings/<int:id>')
def doctor_bookings(id):
    doctor = db.get_or_404(Doctor, id)
    query = (db.select(DoctorBooking).filter_by(doctor_id=id)
             .order_by(DoctorBooking.date.desc(), DoctorBooking.starts_at, DoctorBooking.id))
    return render_template('admin/bookings/doctor_bookings.html', doctor=doctor, page=catalog.paginate(query))


@bp.route('/docbookings/status/<int:id>/<status>', methods=['POST'])
def set_doctor_booking_status(id, status):
    booking = db.get_or_404(DoctorBooking, id)
    try:
        booking_service.set_doctor_booking_status(booking, status)
        flash(f'Appointment marked as {booking.status_label}', 'success')
    except BookingError as e:
        flash(str(e), 'danger')
    return redirect(safe_next(url_for('admin.doctor_bookings', id=booking.doctor_id)))


@bp.route('/del_docbookings/<int:id>', methods=['POST'])
def delete_doctor_booking(id):
    booking = db.get_or_404(DoctorBooking, id)
    doctor_id = booking.doctor_id
    db.session.delete(booking)
    db.session.commit()
    flash('Booking removed', 'info')
    return redirect(url_for('admin.doctor_bookings', id=doctor_id))


# ------------------------------------------------------------ facility bookings / results

@bp.route('/facbookings/<int:id>')
def facility_bookings(id):
    facility = db.get_or_404(Facility, id)
    query = (db.select(FacilityBooking).filter_by(facility_id=id)
             .order_by(FacilityBooking.date.desc(), FacilityBooking.id.desc()))
    return render_template('admin/bookings/facility_bookings.html', facility=facility,
                           page=catalog.paginate(query))


@bp.route('/facbookings/<int:id>/result', methods=['POST'])
def set_result(id):
    booking = db.get_or_404(FacilityBooking, id)
    try:
        booking_service.set_result(booking, request.form.get('result'))
        flash(f'Result saved: {booking.result}', 'success')
    except BookingError as e:
        flash(str(e), 'danger')
    return redirect(safe_next(url_for('admin.facility_bookings', id=booking.facility_id)))


@bp.route('/del_facbookings/<int:id>', methods=['POST'])
def delete_facility_booking(id):
    booking = db.get_or_404(FacilityBooking, id)
    facility_id = booking.facility_id
    db.session.delete(booking)
    db.session.commit()
    flash('Booking removed', 'info')
    return redirect(url_for('admin.facility_bookings', id=facility_id))
