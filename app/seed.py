"""
Creates the database tables and, in an empty database, loads sample data so the app can be tried at once:
cities, hospitals, clinics and laboratories with their doctors and facilities, a few accounts and appointments.

Every name, address and phone number is made up. The pictures are small generated SVG files.

    flask --app run init-db            create the tables; load the sample data if the database is empty
    flask --app run init-db --reset    delete everything and start again from the sample data
"""
import datetime
import html
import os
import random

import click
from flask import current_app

from .extensions import db
from .models import Appointment, City, Doctor, Facility, Hospital, User
from .utils import timeslots

ADMIN_LOGIN = ('admin@medibook.test', 'admin123')
USER_LOGIN = ('patient@medibook.test', 'patient123')

# (city, phone area code)
CITIES = [('Lahore', '042'), ('Karachi', '021'), ('Islamabad', '051'), ('Rawalpindi', '051'),
          ('Faisalabad', '041'), ('Multan', '061'), ('Peshawar', '091'), ('Quetta', '081')]

OPEN_ALWAYS = 'Open 24 hours, every day'
CLINIC_HOURS = 'Mon to Sat, 09:00 AM to 09:00 PM'
LAB_HOURS = 'Every day, 07:00 AM to 10:00 PM'

# (name, type, city, timings, about and other facilities)
PLACES = [
    ('Crescent Care Hospital', Hospital.HOSPITAL, 'Lahore', OPEN_ALWAYS,
     'A 250-bed hospital known for its heart and emergency departments. Pharmacy, ambulance and car parking.'),
    ('Ravi Riverside Hospital', Hospital.HOSPITAL, 'Lahore', OPEN_ALWAYS,
     'Teaching hospital with strong child health, gynaecology and general surgery units. Pharmacy and cafeteria.'),
    ('Gulberg Family Clinic', Hospital.CLINIC, 'Lahore', CLINIC_HOURS,
     'Neighbourhood clinic for the whole family. Vaccination, minor procedures and an in-house pharmacy.'),
    ('Canal View Diagnostic Lab', Hospital.LAB, 'Lahore', LAB_HOURS,
     'Pathology and imaging laboratory. Home sample collection and reports by email.'),
    ('Sea Breeze General Hospital', Hospital.HOSPITAL, 'Karachi', OPEN_ALWAYS,
     'Community hospital near the coast with round-the-clock emergency care. Blood bank and ambulance.'),
    ('Clifton Heart & Chest Clinic', Hospital.CLINIC, 'Karachi', CLINIC_HOURS,
     'Specialist clinic for heart and lung problems with ECG and echocardiography on site.'),
    ('Harbour Diagnostic Laboratory', Hospital.LAB, 'Karachi', LAB_HOURS,
     'Full-service diagnostic laboratory with CT and MRI. Wheelchair access and free parking.'),
    ('Green Valley Medical Center', Hospital.HOSPITAL, 'Islamabad', OPEN_ALWAYS,
     'Modern medical centre with advanced diagnostics and day-care surgery. Pharmacy and prayer area.'),
    ('Margalla Heights Hospital', Hospital.HOSPITAL, 'Islamabad', OPEN_ALWAYS,
     'Specialist hospital at the foot of the hills, focused on nerve, bone and joint care. Physiotherapy gym.'),
    ('Pine Grove Clinic', Hospital.CLINIC, 'Islamabad', CLINIC_HOURS,
     'Calm, patient-friendly clinic with general medicine, ENT and mental health services.'),
    ('Saddar City Hospital', Hospital.HOSPITAL, 'Rawalpindi', OPEN_ALWAYS,
     'City hospital with fast outpatient clinics and a modern intensive care unit. Pharmacy and ambulance.'),
    ('Blue Sky Children Clinic', Hospital.CLINIC, 'Rawalpindi', CLINIC_HOURS,
     'Clinic for children only: check-ups, vaccination and growth monitoring. Play area in the waiting room.'),
    ('Chenab Health Center', Hospital.HOSPITAL, 'Faisalabad', OPEN_ALWAYS,
     'Busy health centre with laboratory, radiology and specialist outpatient departments.'),
    ('Chenab Clinical Laboratory', Hospital.LAB, 'Faisalabad', LAB_HOURS,
     'Clinical laboratory for routine and special blood tests. Home sample collection.'),
    ('Five Rivers Medical Complex', Hospital.HOSPITAL, 'Multan', OPEN_ALWAYS,
     'Large medical complex with a dedicated kidney and dialysis centre. Pharmacy and blood bank.'),
    ('Sunrise Diagnostic Laboratory', Hospital.LAB, 'Multan', LAB_HOURS,
     'Diagnostic laboratory with X-ray, ultrasound and a wide range of blood tests.'),
    ('Khyber Hills Hospital', Hospital.HOSPITAL, 'Peshawar', OPEN_ALWAYS,
     'Regional hospital with burns, trauma and bone services. Ambulance and attendant rooms.'),
    ('Bolan Valley Hospital', Hospital.HOSPITAL, 'Quetta', OPEN_ALWAYS,
     'General hospital providing internal medicine, chest and child health services. Pharmacy on site.'),
]

STREETS = ['Main Boulevard', 'Jail Road', 'University Road', 'Canal Road', 'Mall Road', 'Airport Road',
           'GT Road', 'Link Road', 'Club Road', 'Service Road']

# specialization: (qualification, about)
SPECIALTIES = {
    'Cardiologist': ('MBBS, FCPS (Cardiology)', 'Treats heart disease, high blood pressure and chest pain.'),
    'Dermatologist': ('MBBS, FCPS (Dermatology)', 'Skin, hair and nail problems, acne and allergies.'),
    'Pediatrician': ('MBBS, FCPS (Pediatrics)', 'Child health, growth, vaccination and newborn care.'),
    'Gynecologist': ('MBBS, FCPS (Gynae & Obs)', 'Pregnancy care, women\'s health and infertility.'),
    'Orthopedic Surgeon': ('MBBS, FCPS (Orthopedics)', 'Bone, joint and sports injuries, fractures and back pain.'),
    'Neurologist': ('MBBS, FCPS (Neurology)', 'Headache, epilepsy, stroke and nerve disorders.'),
    'ENT Specialist': ('MBBS, FCPS (ENT)', 'Ear, nose and throat problems, sinus and hearing loss.'),
    'Eye Specialist': ('MBBS, FCPS (Ophthalmology)', 'Eye check-ups, cataract, glaucoma and vision problems.'),
    'General Physician': ('MBBS, MCPS (Medicine)', 'Fever, infections, diabetes and routine check-ups.'),
    'Psychiatrist': ('MBBS, FCPS (Psychiatry)', 'Anxiety, depression, sleep and stress problems.'),
    'Dentist': ('BDS, FCPS (Dentistry)', 'Tooth pain, root canal, braces and dental cleaning.'),
    'Urologist': ('MBBS, FCPS (Urology)', 'Kidney stones, urinary and prostate problems.'),
    'Gastroenterologist': ('MBBS, FCPS (Gastroenterology)', 'Stomach, liver and digestive problems, endoscopy.'),
    'Pulmonologist': ('MBBS, FCPS (Pulmonology)', 'Asthma, chest infections and breathing problems.'),
    'Endocrinologist': ('MBBS, FCPS (Endocrinology)', 'Diabetes, thyroid and hormone disorders.'),
}

# The specialists of each clinic; hospitals get three specialists each, taken in turn from SPECIALTIES.
CLINIC_DOCTORS = {
    'Gulberg Family Clinic': ['General Physician', 'Pediatrician', 'Dermatologist'],
    'Clifton Heart & Chest Clinic': ['Cardiologist', 'Pulmonologist'],
    'Pine Grove Clinic': ['Psychiatrist', 'General Physician', 'ENT Specialist'],
    'Blue Sky Children Clinic': ['Pediatrician', 'Pediatrician'],
}

FIRST_NAMES = ['Ayesha', 'Bilal', 'Fatima', 'Hamza', 'Zainab', 'Usman', 'Maryam', 'Ali', 'Sana', 'Imran',
               'Hira', 'Faisal', 'Amna', 'Kamran', 'Nida', 'Saad', 'Rabia', 'Tariq', 'Mehwish', 'Asad']
LAST_NAMES = ['Khan', 'Ahmed', 'Qureshi', 'Malik', 'Siddiqui', 'Butt', 'Chaudhry', 'Raza', 'Sheikh', 'Hussain']

# (working days, from, to, minutes per patient)
DOCTOR_HOURS = [
    ('Mon,Tue,Wed,Thu,Fri', '09:00', '12:00', 30),
    ('Mon,Wed,Fri', '17:00', '20:00', 20),
    ('Tue,Thu,Sat', '10:00', '13:00', 30),
    ('Mon,Tue,Wed,Thu,Fri,Sat', '14:00', '17:00', 30),
    ('Sat,Sun', '11:00', '14:00', 20),
    ('Mon,Tue,Wed,Thu,Fri,Sat,Sun', '18:00', '21:00', 30),
]

FASTING = 'Do not eat or drink anything except water for 8 to 10 hours before the test.'
NO_PREPARATION = 'No preparation is needed.'

# name: (fee, details and preparation)
PATHOLOGY = {
    'Complete Blood Count (CBC)': (800, f'Counts red cells, white cells and platelets. {NO_PREPARATION}'),
    'Lipid Profile': (1500, f'Cholesterol and triglycerides. {FASTING}'),
    'Liver Function Test (LFT)': (1800, f'Checks how well the liver is working. {NO_PREPARATION}'),
    'Renal Function Test (RFT)': (1600, f'Urea, creatinine and electrolytes for kidney health. {NO_PREPARATION}'),
    'HbA1c': (1400, f'Average blood sugar over the last three months. {NO_PREPARATION}'),
    'Thyroid Profile': (2200, f'T3, T4 and TSH hormone levels. {NO_PREPARATION}'),
    'Vitamin D': (3000, f'Vitamin D level in the blood. {NO_PREPARATION}'),
    'Urine Complete Examination': (400, 'Bring a morning urine sample in the container given by the lab.'),
    'Fasting Blood Sugar': (300, f'Blood sugar level. {FASTING}'),
    'ECG': (600, 'Records the electrical activity of the heart. Wear loose clothing.'),
    'Physiotherapy Session': (2000, 'A 30-minute session with a physiotherapist. Wear comfortable clothing.'),
}
RADIOLOGY = {
    'Chest X-Ray': (1200, 'Remove jewellery and metal objects before the X-ray.'),
    'Abdominal Ultrasound': (2000, 'Do not eat for 6 hours before the scan. Drink water and keep a full bladder.'),
    'CT Scan (Brain)': (8000, 'Tell the staff about any allergies. Remove metal objects.'),
    'MRI (Lumbar Spine)': (15000, 'Not suitable for patients with a pacemaker or metal implants. '
                                  'The scan takes about 30 minutes.'),
    'Mammography': (4500, 'Do not use deodorant or powder on the day of the scan.'),
    'Echocardiography': (4500, f'Ultrasound scan of the heart. {NO_PREPARATION}'),
    'Dental X-Ray (OPG)': (1500, 'Panoramic X-ray of the teeth and jaw. Remove jewellery and dentures.'),
}
CLINIC_FACILITIES = {'Clifton Heart & Chest Clinic': ['ECG', 'Echocardiography']}   # other clinics: two tests
PATHOLOGY_HOURS = ('08:00', '12:00', 15)
RADIOLOGY_HOURS = ('10:00', '16:00', 30)

# (name, city) of the sample users besides USER_LOGIN
USERS = [('Sara Iqbal', 'Karachi'), ('Hassan Ali', 'Islamabad'), ('Mahnoor Tariq', 'Multan'),
         ('Zeeshan Akhtar', 'Peshawar'), ('Iqra Nadeem', 'Faisalabad')]

PATHOLOGY_RESULTS = ['All values are within the normal range.',
                     'Slightly raised values. Please discuss the report with your doctor.',
                     'Normal. No further tests are needed.']
RADIOLOGY_RESULTS = ['Normal study. No abnormality detected.',
                     'Mild changes seen. Please discuss the report with your doctor.']

HUES = [174, 199, 211, 190, 162, 262, 330, 24, 141, 280, 4, 226]


# ---------------------------------------------------------------- pictures

def _hospital_svg(name, city, hue):
    name, city = html.escape(name), html.escape(city)
    windows = ''.join(
        f'<rect x="{x}" y="{y}" width="26" height="20" rx="3" fill="#fff" opacity=".85"/>'
        for y in (190, 235, 280) for x in (300, 345, 390, 435, 480))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" role="img" aria-label="{name}">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="hsl({hue},70%,45%)"/><stop offset="1" stop-color="hsl({(hue + 40) % 360},70%,35%)"/>
  </linearGradient></defs>
  <rect width="800" height="450" fill="url(#g)"/>
  <circle cx="680" cy="80" r="140" fill="#fff" opacity=".07"/><circle cx="90" cy="420" r="160" fill="#fff" opacity=".06"/>
  <rect x="270" y="150" width="260" height="190" rx="8" fill="#fff" opacity=".25"/>
  {windows}
  <rect x="375" y="300" width="50" height="40" rx="4" fill="#fff" opacity=".9"/>
  <rect x="372" y="98" width="56" height="56" rx="10" fill="#fff"/>
  <rect x="394" y="106" width="12" height="40" rx="2" fill="hsl({hue},70%,45%)"/>
  <rect x="380" y="120" width="40" height="12" rx="2" fill="hsl({hue},70%,45%)"/>
  <text x="400" y="392" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="30" font-weight="700" fill="#fff">{name}</text>
  <text x="400" y="424" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="20" fill="#fff" opacity=".85">{city}</text>
</svg>'''


def _doctor_svg(name, hue):
    initials = html.escape(''.join(part[0] for part in name.replace('Dr. ', '').split()[:2]).upper())
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" role="img" aria-label="{html.escape(name)}">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="hsl({hue},65%,55%)"/><stop offset="1" stop-color="hsl({(hue + 30) % 360},65%,40%)"/>
  </linearGradient></defs>
  <rect width="400" height="400" fill="url(#g)"/>
  <circle cx="200" cy="150" r="70" fill="#fff" opacity=".9"/>
  <path d="M70 400c0-80 58-130 130-130s130 50 130 130z" fill="#fff" opacity=".9"/>
  <path d="M160 290v40a40 40 0 0 0 80 0v-40" fill="none" stroke="hsl({hue},65%,45%)" stroke-width="8" stroke-linecap="round"/>
  <circle cx="240" cy="345" r="10" fill="hsl({hue},65%,45%)"/>
  <text x="200" y="172" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="62" font-weight="700" fill="hsl({hue},65%,40%)">{initials}</text>
</svg>'''


def _save_picture(filename, svg):
    folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, filename), 'w', encoding='utf-8') as file:
        file.write(svg)
    return filename


# ---------------------------------------------------------------- sample data

def _hours(start, end):
    return {'start_time': timeslots.parse_time(start), 'end_time': timeslots.parse_time(end)}


def _places(rng):
    cities = {name: City(name=name) for name, _code in CITIES}
    codes = dict(CITIES)
    places = []
    for number, (name, kind, city, timings, about) in enumerate(PLACES, start=1):
        places.append(Hospital(
            name=name, kind=kind, city=cities[city], timings=timings, description=about,
            address=f'{rng.randint(1, 250)} {rng.choice(STREETS)}, {city}',
            phone=f'{codes[city]}-3{number:02d}{rng.randint(10000, 99999)}',
            image=_save_picture(f'hospital-{number:02d}.svg', _hospital_svg(name, city, HUES[number % len(HUES)]))))
    return list(cities.values()), places


def _doctors(rng, places):
    wanted, turn = [], 0   # (place, specialization)
    names = list(SPECIALTIES)
    for place in places:
        if place.kind == Hospital.HOSPITAL:
            wanted += [(place, names[(turn + step) % len(names)]) for step in range(3)]
            turn += 3
        for specialization in CLINIC_DOCTORS.get(place.name, []):
            wanted.append((place, specialization))

    people = [f'Dr. {first} {last}' for first in FIRST_NAMES for last in LAST_NAMES]
    rng.shuffle(people)
    doctors = []
    for number, ((place, specialization), name) in enumerate(zip(wanted, people), start=1):
        qualification, about = SPECIALTIES[specialization]
        days, start, end, minutes = rng.choice(DOCTOR_HOURS)
        doctors.append(Doctor(
            hospital=place, name=name, specialization=specialization, qualification=qualification,
            fee=rng.choice([1000, 1500, 2000, 2500, 3000, 3500]), days=days, slot_minutes=minutes,
            description=f'{about} {rng.randint(4, 25)} years of experience.',
            image=_save_picture(f'doctor-{number:02d}.svg', _doctor_svg(name, HUES[(number * 5) % len(HUES)])),
            **_hours(start, end)))
    return doctors


def _facilities(rng, places):
    def offered(place):
        """(pathology names, radiology names) offered at this place."""
        if place.kind == Hospital.HOSPITAL:
            return rng.sample(list(PATHOLOGY), 4), rng.sample(list(RADIOLOGY), 3)
        if place.kind == Hospital.LAB:
            return rng.sample(list(PATHOLOGY)[:9], 7), rng.sample(list(RADIOLOGY), 4)
        names = CLINIC_FACILITIES.get(place.name) or rng.sample(list(PATHOLOGY)[:9], 2)
        return [n for n in names if n in PATHOLOGY], [n for n in names if n in RADIOLOGY]

    facilities = []
    for place in places:
        days = 'Mon,Tue,Wed,Thu,Fri,Sat' + (',Sun' if place.kind != Hospital.CLINIC else '')
        for names, source, category, (start, end, minutes) in zip(
                offered(place), (PATHOLOGY, RADIOLOGY), Facility.CATEGORIES, (PATHOLOGY_HOURS, RADIOLOGY_HOURS)):
            for name in names:
                fee, details = source[name]
                facilities.append(Facility(hospital=place, name=name, category=category, fee=fee,
                                           description=details, days=days, slot_minutes=minutes,
                                           **_hours(start, end)))
    return facilities


def _users(cities):
    by_name = {city.name: city for city in cities}
    admin = User(name='Administrator', email=ADMIN_LOGIN[0], password=ADMIN_LOGIN[1], phone='0300-1000000',
                 city=by_name['Lahore'], role=User.ADMIN)
    users = [User(name='Ahmed Raza', email=USER_LOGIN[0], password=USER_LOGIN[1], phone='0300-1000001',
                  city=by_name['Lahore'])]
    for number, (name, city) in enumerate(USERS, start=2):
        users.append(User(name=name, email=f'{name.split()[0].lower()}@medibook.test', password=USER_LOGIN[1],
                          phone=f'0300-100000{number}', city=by_name[city]))
    return admin, users


class _Diary:
    """Hands out appointments so that no slot is used twice."""

    def __init__(self, rng):
        self.rng = rng
        self.today = timeslots.today()
        self.used = set()
        self.appointments = []

    def add(self, user, subject, days_from_today, status=Appointment.BOOKED):
        """An appointment on the working day of `subject` nearest to today + `days_from_today`."""
        date = self.today + datetime.timedelta(days=days_from_today)
        step = datetime.timedelta(days=1 if days_from_today > 0 else -1)
        while not subject.works_on(date):
            date += step
        free = [time for time in subject.slots if (id(subject), date, time) not in self.used]
        time = self.rng.choice(free)
        if status != Appointment.CANCELLED:
            self.used.add((id(subject), date, time))
        booked_on = min(date, self.today) - datetime.timedelta(days=self.rng.randint(1, 6))
        appointment = Appointment(user=user, subject=subject, date=date, time=time, status=status,
                                  created_at=datetime.datetime.combine(booked_on, datetime.time(10, 30)))
        if status == Appointment.COMPLETED and appointment.is_test:
            results = PATHOLOGY_RESULTS if subject.category == Facility.PATHOLOGY else RADIOLOGY_RESULTS
            appointment.result = self.rng.choice(results)
        self.appointments.append(appointment)


def _appointments(rng, users, doctors, facilities):
    booked, completed, cancelled = Appointment.STATUSES
    diary = _Diary(rng)
    first = users[0]   # the documented sample user gets one appointment of every kind
    lahore_doctors = [doctor for doctor in doctors if doctor.hospital.city.name == 'Lahore']
    lahore_tests = [facility for facility in facilities if facility.hospital.city.name == 'Lahore']
    diary.add(first, lahore_doctors[0], 2)
    diary.add(first, lahore_tests[0], 4)
    diary.add(first, lahore_doctors[1], -12, completed)
    diary.add(first, lahore_tests[1], -9, completed)
    diary.add(first, lahore_tests[-1], -20, completed)
    diary.add(first, lahore_doctors[2], -5, cancelled)

    for _ in range(40):
        user, subject = rng.choice(users), rng.choice(doctors + facilities)
        days = rng.randint(-30, 14)
        if days > 0:
            status = rng.choice([booked] * 5 + [cancelled])
        elif days > -3 and isinstance(subject, Facility):
            status = booked   # recent tests that still wait for their result
        else:
            status = rng.choice([completed] * 4 + [cancelled])
        diary.add(user, subject, days, status)
    return diary.appointments


def load_sample_data():
    rng = random.Random(7)   # the same data every time
    cities, places = _places(rng)
    doctors = _doctors(rng, places)
    facilities = _facilities(rng, places)
    admin, users = _users(cities)
    appointments = _appointments(rng, users, doctors, facilities)
    db.session.add_all([*cities, *places, *doctors, *facilities, admin, *users, *appointments])
    db.session.commit()
    return (f'Sample data loaded: {len(cities)} cities, {len(places)} hospitals, clinics and labs, '
            f'{len(doctors)} doctors, {len(facilities)} facilities and {len(appointments)} appointments.')


def init_db(reset=False):
    """Create the tables; in an empty database also load the sample data. Returns what was done."""
    if reset:
        db.drop_all()
    db.create_all()
    if db.session.scalar(db.select(User.id).limit(1)) is not None:
        return 'The database is ready (existing data was kept).'
    return load_sample_data()


def register_commands(app):
    @app.cli.command('init-db')
    @click.option('--reset', is_flag=True, help='Delete all existing data first.')
    def init_db_command(reset):
        """Create the tables and load the sample data."""
        click.echo(init_db(reset))
        click.echo('Admin login: {} / {}'.format(*ADMIN_LOGIN))
        click.echo('User login:  {} / {}'.format(*USER_LOGIN))
