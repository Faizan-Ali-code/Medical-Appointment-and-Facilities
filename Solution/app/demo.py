"""
Demo data so the app looks alive: 20 hospitals, 40 doctors, 24 facilities,
demo patients and bookings. All names, addresses and phone numbers are FICTIONAL.

Images are generated as small SVG files (hospital covers and doctor avatars)
into UPLOAD_FOLDER/demo/, so no photos of real places or people are used.

Run:  venv\\Scripts\\flask --app run seed-demo          (adds demo data once)
      venv\\Scripts\\flask --app run seed-demo --reset  (fresh database + demo data)
"""
import datetime
import html
import os
import random

from flask import current_app

from .extensions import db
from .models import Doctor, DoctorBooking, Facility, FacilityBooking, Hospital, User

DEMO_MARKER = 'Crescent Care Hospital'   # first demo hospital; if it exists, demo data is already loaded
DEMO_PASSWORD = 'patient123'

# (name, city, area code, short description)
HOSPITALS = [
    ('Crescent Care Hospital', 'Lahore', '042', 'A 250-bed multi-specialty hospital known for its cardiology and emergency departments.'),
    ('Green Valley Medical Center', 'Islamabad', '051', 'Modern tertiary care center with advanced diagnostics and day-care surgery.'),
    ('Sea Breeze General Hospital', 'Karachi', '021', 'Community general hospital serving families near the coast with 24/7 emergency care.'),
    ('Margalla Heights Hospital', 'Islamabad', '051', 'Specialist hospital at the foot of the hills, focused on neurology and orthopedics.'),
    ('Ravi Riverside Hospital', 'Lahore', '042', 'Teaching hospital with strong pediatrics, gynecology and general surgery units.'),
    ('Mehran Family Hospital', 'Hyderabad', '022', 'Affordable family hospital offering outpatient clinics and maternity care.'),
    ('Five Rivers Medical Complex', 'Multan', '061', 'Large medical complex with a dedicated kidney and dialysis center.'),
    ('Khyber Hills Hospital', 'Peshawar', '091', 'Regional referral hospital with burns, trauma and orthopedic services.'),
    ('Bolan Valley Hospital', 'Quetta', '081', 'General hospital providing internal medicine, pulmonology and child health.'),
    ('Chenab Health Center', 'Faisalabad', '041', 'Busy health center with laboratory, radiology and specialist OPDs.'),
    ('Saddar City Hospital', 'Rawalpindi', '051', 'City hospital with fast-track outpatient clinics and a modern ICU.'),
    ('Clifton Heart & Lung Institute', 'Karachi', '021', 'Specialized institute for heart and lung diseases with a cath lab.'),
    ('Gulberg Women & Children Hospital', 'Lahore', '042', 'Dedicated to mothers and children: maternity, NICU and pediatric wards.'),
    ('Canal View Eye & ENT Hospital', 'Lahore', '042', 'Eye and ENT hospital offering cataract, LASIK and hearing services.'),
    ('Pine Grove Hospital', 'Islamabad', '051', 'Calm, patient-friendly hospital with psychiatry and rehabilitation units.'),
    ('Sialkot Care Hospital', 'Sialkot', '052', 'Multi-specialty hospital with sports medicine and physiotherapy.'),
    ('Harbour Medical Center', 'Karachi', '021', 'Medical center with gastroenterology, endoscopy and liver clinics.'),
    ('Model Town Surgical Hospital', 'Lahore', '042', 'Surgical hospital with modern operation theaters and recovery wards.'),
    ('Blue Sky Children Hospital', 'Rawalpindi', '051', 'Children-only hospital with vaccination, pediatric surgery and NICU.'),
    ('Sunrise Diagnostic & General Hospital', 'Multan', '061', 'General hospital with a full diagnostic wing open 24 hours.'),
]

STREETS = ['Main Boulevard', 'Jail Road', 'University Road', 'Canal Road', 'Mall Road', 'Airport Road',
           'GT Road', 'Link Road', 'Club Road', 'Service Road']

# (specialization, description template)
SPECIALTIES = [
    ('Cardiologist', 'FCPS (Cardiology). Treats heart disease, high blood pressure and chest pain.'),
    ('Dermatologist', 'FCPS (Dermatology). Skin, hair and nail problems, acne and allergies.'),
    ('Pediatrician', 'FCPS (Pediatrics). Child health, growth, vaccination and newborn care.'),
    ('Gynecologist', 'FCPS (Gynae & Obs). Pregnancy care, women\'s health and infertility.'),
    ('Orthopedic Surgeon', 'FCPS (Orthopedics). Bone, joint and sports injuries, fractures and back pain.'),
    ('Neurologist', 'FCPS (Neurology). Headache, epilepsy, stroke and nerve disorders.'),
    ('ENT Specialist', 'FCPS (ENT). Ear, nose and throat problems, sinus and hearing loss.'),
    ('Eye Specialist', 'FCPS (Ophthalmology). Eye checkups, cataract, glaucoma and vision problems.'),
    ('General Physician', 'MBBS, MCPS. Fever, infections, diabetes and routine checkups.'),
    ('Psychiatrist', 'FCPS (Psychiatry). Anxiety, depression, sleep and stress problems.'),
    ('Dentist', 'BDS, FCPS. Tooth pain, root canal, braces and dental cleaning.'),
    ('Urologist', 'FCPS (Urology). Kidney stones, urinary and prostate problems.'),
    ('Gastroenterologist', 'FCPS (Gastro). Stomach, liver and digestive problems, endoscopy.'),
    ('Pulmonologist', 'FCPS (Pulmonology). Asthma, chest infections and breathing problems.'),
    ('Endocrinologist', 'FCPS (Endocrinology). Diabetes, thyroid and hormone disorders.'),
]

FIRST = ['Ayesha', 'Bilal', 'Fatima', 'Hamza', 'Zainab', 'Usman', 'Maryam', 'Ali', 'Sana', 'Imran',
         'Hira', 'Faisal', 'Amna', 'Kamran', 'Nida', 'Saad', 'Rabia', 'Tariq', 'Mehwish', 'Asad']
LAST = ['Khan', 'Ahmed', 'Qureshi', 'Malik', 'Siddiqui', 'Butt', 'Chaudhry', 'Raza', 'Sheikh', 'Hussain']

SLOT_SETS = [
    '09:00 AM, 09:30 AM, 10:00 AM, 10:30 AM, 11:00 AM',
    '11:00 AM, 11:30 AM, 12:00 PM, 12:30 PM',
    '02:00 PM, 02:30 PM, 03:00 PM, 03:30 PM, 04:00 PM',
    '05:00 PM, 05:30 PM, 06:00 PM, 06:30 PM, 07:00 PM',
    '07:00 PM, 07:30 PM, 08:00 PM, 08:30 PM',
]
DAY_SETS = ['', 'Mon,Tue,Wed,Thu,Fri', 'Mon,Wed,Fri', 'Tue,Thu,Sat', 'Mon,Tue,Wed,Thu,Fri,Sat', 'Sat,Sun']

# (facility type, services, fees)
FACILITY_TYPES = [
    ('Diagnostic Laboratory', 'CBC, Lipid Profile, LFT, RFT, HbA1c', '800, 1500, 1800, 1600, 1400'),
    ('Radiology & Imaging', 'X-ray, Ultrasound, CT Scan, MRI', '1200, 2000, 8000, 15000'),
    ('Cardiac Diagnostics', 'ECG, Echocardiography, Stress Test, Holter Monitoring', '600, 4500, 6000, 7000'),
    ('Physiotherapy Unit', 'Initial Assessment, Therapy Session, Sports Rehab', '1500, 2000, 3000'),
    ('Eye Testing Center', 'Vision Test, Eye Pressure Test, Retina Scan', '500, 800, 3500'),
    ('Pathology Lab', 'Urine Test, Thyroid Profile, Vitamin D, Dengue NS1', '400, 2200, 3000, 1800'),
]

HUES = [211, 190, 162, 262, 330, 24, 199, 141, 280, 4, 45, 226]


# ------------------------------------------------------------ SVG images

def _hospital_svg(name, city, hue):
    name, city = html.escape(name), html.escape(city.strip())
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


def _write(folder, filename, svg):
    with open(os.path.join(folder, filename), 'w', encoding='utf-8') as f:
        f.write(svg)
    return f'demo/{filename}'


# ------------------------------------------------------------ loader

def load_demo():
    """Insert demo data once. Returns a short summary. Needs an app context."""
    if db.session.scalar(db.select(Hospital).filter_by(name=DEMO_MARKER)):
        return 'Demo data is already loaded.'

    rng = random.Random(619)  # same data every time
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'demo')
    os.makedirs(folder, exist_ok=True)

    hospitals = []
    for i, (name, city, code, about) in enumerate(HOSPITALS, start=1):
        hue = HUES[i % len(HUES)]
        hospitals.append(Hospital(
            name=name, city=city, phone=f'{code}-3{i:02d}{rng.randint(10000, 99999)}',
            address=f'{rng.randint(1, 250)} {rng.choice(STREETS)}, {city}',
            description=about + ' (Demo record: fictional hospital.)',
            image=_write(folder, f'hospital-{i:02d}.svg', _hospital_svg(name, city, hue))))
    db.session.add_all(hospitals)
    db.session.flush()

    doctors, used_names = [], set()
    for i in range(40):
        while True:
            name = f'Dr. {rng.choice(FIRST)} {rng.choice(LAST)}'
            if name not in used_names:
                used_names.add(name)
                break
        specialization, about = SPECIALTIES[i % len(SPECIALTIES)]
        years = rng.randint(4, 25)
        doctors.append(Doctor(
            name=name, hospital=hospitals[i % len(hospitals)], specialization=specialization,
            fee=str(rng.choice([1000, 1500, 2000, 2500, 3000, 3500, 4000])),
            slots=rng.choice(SLOT_SETS), days=rng.choice(DAY_SETS),
            description=f'{about} {years} years of experience.',
            image=_write(folder, f'doctor-{i + 1:02d}.svg', _doctor_svg(name, HUES[(i * 5) % len(HUES)]))))
    db.session.add_all(doctors)

    facilities = []
    for i, hospital in enumerate(hospitals + hospitals[:4]):  # 24 facilities, some hospitals have two
        kind, services, fees = FACILITY_TYPES[i % len(FACILITY_TYPES)]
        facilities.append(Facility(
            hospital=hospital, name=f'{hospital.name.split()[0]} {kind}', services=services, fee=fees,
            contact=f'03{rng.randint(0, 4)}{rng.randint(0, 9)}-{rng.randint(1000000, 9999999)}',
            description=f'{kind} at {hospital.name}. Reports are usually ready within 24 hours.'))
    db.session.add_all(facilities)

    patients = []
    for i, (first, last, city) in enumerate([('Ahmed', 'Raza', 'Lahore'), ('Sara', 'Iqbal', 'Karachi'),
                                             ('Hassan', 'Ali', 'Islamabad'), ('Mahnoor', 'Tariq', 'Multan'),
                                             ('Zeeshan', 'Akhtar', 'Peshawar'), ('Iqra', 'Nadeem', 'Faisalabad')],
                                            start=1):
        user = User(name=f'{first} {last}', email=f'patient{i}@demo.com', phone=f'0300-000000{i}',
                    city=city, role='user')
        user.set_password(DEMO_PASSWORD)
        patients.append(user)
    db.session.add_all(patients)
    db.session.flush()

    today = datetime.date.today()
    appointments = {}  # keyed by (doctor, date, slot) so a slot is never booked twice
    for _ in range(36):
        doctor = rng.choice(doctors)
        date = today + datetime.timedelta(days=rng.randint(-30, 14))
        while not doctor.works_on(date):  # move to the doctor's next working day
            date += datetime.timedelta(days=1)
        slot = rng.choice(doctor.slot_list)
        if date < today:
            status = rng.choice([DoctorBooking.COMPLETED] * 3 + [DoctorBooking.CANCELLED])
        else:
            status = rng.choice([DoctorBooking.BOOKED] * 5 + [DoctorBooking.CANCELLED])
        appointments[(doctor.name, date, slot)] = DoctorBooking(
            doctor=doctor, user=rng.choice(patients), date=date, slot=slot, status=status)
    db.session.add_all(appointments.values())

    for _ in range(18):
        facility = rng.choice(facilities)
        done = rng.random() < 0.55
        db.session.add(FacilityBooking(
            facility=facility, user=rng.choice(patients), service=rng.choice(facility.service_list),
            date=today - datetime.timedelta(days=rng.randint(0, 20)),
            status=FacilityBooking.STATUS_DONE if done else FacilityBooking.STATUS_PENDING,
            result=rng.choice(['Positive', 'Negative', 'Normal']) if done else '-'))

    db.session.commit()
    return (f'Demo data loaded: {len(hospitals)} hospitals, {len(doctors)} doctors, {len(facilities)} facilities, '
            f'{len(patients)} patients (password: {DEMO_PASSWORD}), plus sample bookings.')
