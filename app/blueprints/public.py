"""Pages everyone can open: home, search, and the hospitals, doctors and facilities with their free slots."""
from flask import Blueprint, current_app, render_template, request, send_from_directory

from ..extensions import db
from ..models import Doctor, Facility, Hospital
from ..services import appointments, catalog, stats
from ..utils import int_arg, paginate, search_term

bp = Blueprint('public', __name__)

SEARCH_PREVIEW = 6   # results shown per group on the search page


@bp.get('/')
def index():
    return render_template('public/home.html', cities=catalog.city_list(), counts=stats.site_counts())


@bp.get('/search')
def search():
    """Search everything at once by city, hospital name, type of service or specialist name."""
    term, city_id = search_term(), int_arg('city')
    groups = []
    if term or city_id:
        for title, endpoint, query in (
                ('Hospitals, clinics and labs', 'public.hospitals', catalog.hospitals(term, city_id)),
                ('Doctors', 'public.doctors', catalog.doctors(term, city_id)),
                ('Facilities', 'public.facilities', catalog.facilities(term, city_id))):
            groups.append({'title': title, 'endpoint': endpoint, 'total': catalog.count(query),
                           'rows': db.session.scalars(query.limit(SEARCH_PREVIEW)).unique().all()})
    return render_template('public/search.html', groups=groups, cities=catalog.city_list(),
                           found=sum(group['total'] for group in groups))


@bp.get('/hospitals')
def hospitals():
    query = catalog.hospitals(search_term(), int_arg('city'), request.args.get('type', ''))
    return render_template('public/hospitals.html', page=paginate(query, 'CARDS_PER_PAGE'),
                           cities=catalog.city_list(), kinds=Hospital.KINDS)


@bp.get('/hospitals/<int:id>')
def hospital(id):
    return render_template('public/hospital.html', hospital=db.get_or_404(Hospital, id),
                           categories=Facility.CATEGORIES)


@bp.get('/doctors')
def doctors():
    query = catalog.doctors(search_term(), int_arg('city'), request.args.get('specialization', ''),
                            int_arg('hospital'))
    return render_template('public/doctors.html', page=paginate(query, 'CARDS_PER_PAGE'),
                           cities=catalog.city_list(), specializations=catalog.specializations())


@bp.get('/doctors/<int:id>')
def doctor(id):
    """Doctor details with the free slots of the day chosen by ?date= (default: the next working day)."""
    doctor = db.get_or_404(Doctor, id)
    return render_template('public/doctor.html', doctor=doctor,
                           **appointments.day_view(doctor, request.args.get('date')))


@bp.get('/facilities')
def facilities():
    query = catalog.facilities(search_term(), int_arg('city'), request.args.get('category', ''),
                               int_arg('hospital'))
    return render_template('public/facilities.html', page=paginate(query, 'CARDS_PER_PAGE'),
                           cities=catalog.city_list(), categories=Facility.CATEGORIES)


@bp.get('/facilities/<int:id>')
def facility(id):
    facility = db.get_or_404(Facility, id)
    return render_template('public/facility.html', facility=facility,
                           **appointments.day_view(facility, request.args.get('date')))


@bp.get('/uploads/<path:filename>')
def upload(filename):
    """A picture of a hospital or doctor."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
