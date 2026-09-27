"""Public pages: hospitals, doctors, facilities, hospital detail, and the slot availability API."""
from flask import Blueprint, abort, g, jsonify, render_template, request

from ..extensions import db
from ..models import Doctor, DoctorBooking, Hospital
from ..services import bookings as booking_service
from ..services import catalog, stats
from ..services.bookings import BookingError
from ..utils import search_term

bp = Blueprint('public', __name__)


@bp.route('/', methods=['GET', 'POST'])
def index():
    term, city = search_term(), request.values.get('city', '').strip()
    page = catalog.paginate(catalog.hospitals_query(term, city), catalog.CARDS_PER_PAGE)
    return render_template('public/hospitals.html', page=page, term=term, city=city,
                           cities=catalog.cities(), counts=stats.public_counts())


@bp.route('/fdoctors', methods=['GET', 'POST'])
def doctors():
    term = search_term()
    specialization = request.values.get('specialization', '').strip()
    hospital_id = request.values.get('hospital_id', type=int)
    page = catalog.paginate(catalog.doctors_query(term, specialization, hospital_id), catalog.CARDS_PER_PAGE)
    return render_template('public/doctors.html', page=page, term=term, specialization=specialization,
                           hospital_id=hospital_id, specializations=catalog.specializations(),
                           hospitals=catalog.hospital_choices())


@bp.route('/ffacilities', methods=['GET', 'POST'])
def facilities():
    term, hospital_id = search_term(), request.values.get('hospital_id', type=int)
    page = catalog.paginate(catalog.facilities_query(term, hospital_id))
    return render_template('public/facilities.html', page=page, term=term, hospital_id=hospital_id,
                           hospitals=catalog.hospital_choices())


@bp.route('/detail/<int:id>')
def hospital_detail(id):
    hospital = db.get_or_404(Hospital, id)
    return render_template('public/hospital_detail.html', hospital=hospital)


@bp.route('/api/doctors/<int:id>/availability')
def doctor_availability(id):
    """JSON for the booking form: which slots are free on ?date=YYYY-MM-DD."""
    doctor = db.get_or_404(Doctor, id)
    try:
        date = booking_service.parse_date(request.args.get('date'))
    except BookingError as e:
        return jsonify(error=str(e)), 400
    exclude_id = request.args.get('exclude', type=int)
    if exclude_id:  # when rescheduling, the user's own booking doesn't block its slot
        own = db.session.get(DoctorBooking, exclude_id)
        if own is None or g.user is None or own.user_id != g.user.id:
            abort(404)
    return jsonify(date=date.isoformat(), days=doctor.day_list,
                   **booking_service.availability(doctor, date, exclude_id))
