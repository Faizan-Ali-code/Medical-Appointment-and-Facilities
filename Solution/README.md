# MediBook: Online Booking of Medical Appointments & Services

A Flask web app (CS-619 Final Project) for booking doctor appointments and hospital facility tests.

## Quick start (Windows)
```bat
setup.bat   :: creates venv\, installs requirements-dev.txt, creates instance\medical.db
run.bat     :: http://127.0.0.1:5000
test.bat    :: full test suite + coverage report (htmlcov\index.html)
```
All packages are installed in the project's own `venv\`, never globally.

## Default logins
| Role | Email | Password |
|---|---|---|
| Admin | admin@yahoo.com | admin |
| User | user@yahoo.com | user |
| Demo patients | patient1@demo.com … patient6@demo.com | patient123 |

## Demo data
`setup.bat` loads 20 fictional hospitals, 40 doctors, 24 facilities, 6 patients and sample bookings.
To load it into an existing database: `venv\Scripts\flask --app run seed-demo` (safe to run twice).

## Useful commands
```bat
venv\Scripts\flask --app run init-db [--reset]     :: tables + original sample data
venv\Scripts\flask --app run seed-demo [--reset]   :: demo data
venv\Scripts\flask --app run upgrade-db            :: add new columns to an old database
venv\Scripts\flask --app run create-admin          :: create an admin account
venv\Scripts\flask --app run hash-passwords        :: hash old plain-text passwords
```

New accounts from the Register page are always normal users. To create an admin:
```bat
venv\Scripts\flask --app run create-admin
```

## Database
- **Default:** SQLite at `instance/medical.db`. No server needed.
- **MySQL/XAMPP:** import `medicalappointmentsfinal.sql`, then set `DATABASE_URL` in `.env` (see `.env.example`).
  For a database created from the *old* dump, see "If you use MySQL" in [docs/changes/STEP-05-security.md](docs/changes/STEP-05-security.md).
- Reset the sample data: `venv\Scripts\python init_db.py --reset`

## Project layout
```
app/            the application (blueprints, services, models, templates, static)
tests/          pytest suite (100% coverage)
docs/           ARCHITECTURE.md + one file per enhancement step
run.py          start the server   (index.py still works too)
init_db.py      create tables + sample data
CHANGELOG.md    index of all changes
```
Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
