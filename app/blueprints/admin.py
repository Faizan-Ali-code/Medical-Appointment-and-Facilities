"""
Admin area: manage hospitals, doctors, facilities, users and bookings.

Every route in this blueprint requires an admin (see `guard`). Add and edit
share one view function and one template per entity.
"""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..extensions import db
from ..models import WEEKDAYS, Doctor, DoctorBooking, Facility, FacilityBooking, Hospital, User
from ..services import bookings as booking_service
from ..services import catalog, stats
from ..services.bookings import BookingError
from ..utils import form_values, safe_next, search_term
from ..utils.auth import admin_required
from ..utils.uploads import UploadError, save_upload
from .account import update_profile

bp = Blueprint('admin', __name__)


@bp.before_request
@admin_required
def guard():
    """Runs before every admin route; admin_required redirects non-admins."""


def _save(obj, fields, duplicate_query, messages, image_required=False, extra=None):
    """
    Shared add/edit logic. Returns True when the object was saved.
    `duplicate_query` finds another row that would clash with this one (or None).
    """
    is_new = obj.id is None
    form = form_values(*fields)
    if not all(form.values()):
        flash('Please Fill All The Fields', 'warning')
        return False
    if 'hospital_id' in form:
        if not form['hospital_id'].isdigit() or db.session.get(Hospital, int(form['hospital_id'])) is None:
            flash('Please choose a hospital', 'warning')
            return False
        form['hospital_id'] = int(form['hospital_id'])
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
    hospital = db.get_or_404(Hospital, id) if id else Hospital()
    if request.method == 'POST':
        saved = _save(hospital, HOSPITAL_FIELDS,
                      lambda f: db.select(Hospital).filter_by(name=f['name']),
                      HOSPITAL_MESSAGES, image_required=True)
        if saved:
            return redirect(url_for('admin.hospitals'))
    return render_template('admin/hospitals/form.html', hospital=hospital)


@bp.route('/hospitals/delete/<int:id>', methods=['POST'])
def delete_hospital(id):
    db.session.delete(db.get_or_404(Hospital, id))
    db.session.commit()
    flash('Hospital deleted (with its doctors and facilities)', 'info')
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
    doctor = db.get_or_404(Doctor, id) if id else Doctor()
    if request.method == 'POST':
        saved = _save(doctor, DOCTOR_FIELDS,
                      lambda f: db.select(Doctor).filter_by(name=f['name'], hospital_id=f['hospital_id']),
                      DOCTOR_MESSAGES, image_required=True, extra=_set_days)
        if saved:
            return redirect(url_for('admin.doctors'))
    return render_template('admin/doctors/form.html', doctor=doctor, hospitals=catalog.hospital_choices(),
                           weekdays=WEEKDAYS)


@bp.route('/doctors/delete/<int:id>', methods=['POST'])
def delete_doctor(id):
    db.session.delete(db.get_or_404(Doctor, id))
    db.session.commit()
    flash('Doctor deleted', 'info')
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
    facility = db.get_or_404(Facility, id) if id else Facility()
    if request.method == 'POST':
        saved = _save(facility, FACILITY_FIELDS,
                      lambda f: db.select(Facility).filter_by(name=f['name'], hospital_id=f['hospital_id']),
                      FACILITY_MESSAGES)
        if saved:
            return redirect(url_for('admin.facilities'))
    return render_template('admin/facilities/form.html', facility=facility,
                           hospitals=catalog.hospital_choices())


@bp.route('/facilities/delete/<int:id>', methods=['POST'])
def delete_facility(id):
    db.session.delete(db.get_or_404(Facility, id))
    db.session.commit()
    flash('Facility deleted', 'info')
    return redirect(url_for('admin.facilities'))


# ------------------------------------------------------------ users

@bp.route('/users', methods=['GET', 'POST'])
def users():
    term = search_term()
    return render_template('admin/users/list.html', page=catalog.paginate(catalog.normal_users_query(term)),
                           term=term)


@bp.route('/user_edit/<int:id>', methods=['GET', 'POST'])
def edit_user(id):
    user = db.get_or_404(User, id)
    if request.method == 'POST' and update_profile(user):
        flash('Congrats, Your User Is Updated', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/users/form.html', user=user)


@bp.route('/user_delete/<int:id>', methods=['POST'])
def delete_user(id):
    user = db.get_or_404(User, id)
    if user.id == g.user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    db.session.delete(user)
    db.session.commit()
    flash('User deleted (with their bookings)', 'info')
    return redirect(url_for('admin.users'))


# ------------------------------------------------------------ doctor bookings

@bp.route('/docbookings/<int:id>')
def doctor_bookings(id):
    doctor = db.get_or_404(Doctor, id)
    query = db.select(DoctorBooking).filter_by(doctor_id=id).order_by(DoctorBooking.date.desc(), DoctorBooking.slot)
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


@bp.route('/res_positive/<int:id>', methods=['POST'], defaults={'result': 'Positive'})
@bp.route('/res_negitive/<int:id>', methods=['POST'], defaults={'result': 'Negative'})
def set_result(id, result):
    booking = db.get_or_404(FacilityBooking, id)
    booking_service.set_result(booking, result)
    flash(f'Result set to {result}', 'success')
    return redirect(url_for('admin.facility_bookings', id=booking.facility_id))


@bp.route('/del_facbookings/<int:id>', methods=['POST'])
def delete_facility_booking(id):
    booking = db.get_or_404(FacilityBooking, id)
    facility_id = booking.facility_id
    db.session.delete(booking)
    db.session.commit()
    flash('Booking removed', 'info')
    return redirect(url_for('admin.facility_bookings', id=facility_id))
