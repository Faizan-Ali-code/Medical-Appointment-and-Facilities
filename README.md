# MediBook: Medical Appointments & Facilities

Flask web app for booking doctor appointments and hospital facility tests such as lab tests and X-rays. Built as a final-year project (CS-619), then refactored into a layered app with a full test suite and security hardening.

## Features

- Browse hospitals, doctors and facilities with search, filters and pagination
- Book a doctor in a free time slot (working days, live availability) or book a facility test
- Patients can view, reschedule and cancel their own bookings
- Admin dashboard to manage hospitals, doctors, facilities, users and all bookings
- Security: hashed passwords, CSRF protection, role checks, safe image uploads and security headers
- Responsive Bootstrap 5 UI with dark mode
- 332 automated tests with 100% code coverage

## How it works

```mermaid
flowchart TD
    A([Patient signs in]) --> B[Search hospitals, doctors or facilities]
    B --> C[Pick a date and a free slot]
    C --> D{Slot still free?}
    D -- no --> C
    D -- yes --> E[Booking saved]
    E --> F([View, reschedule or cancel in My Bookings])
```

## Tech stack

Python · Flask · SQLAlchemy · Flask-WTF · Bootstrap 5 · SQLite or MySQL · pytest

## Quick start (Windows)

```bat
git clone https://github.com/Faizan-Ali-code/Medical-Appointment-and-Facilities.git
cd Medical-Appointment-and-Facilities\Solution
setup.bat
run.bat
```

Open http://127.0.0.1:5000. `setup.bat` creates a virtual environment, a local SQLite database and demo data (20 hospitals, 40 doctors, 24 facilities). Run the tests with `test.bat`.

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@yahoo.com | admin |
| Patient | user@yahoo.com | user |

To use MySQL instead of SQLite, import `Solution/medicalappointmentsfinal.sql` and set `DATABASE_URL` in `.env` (see `.env.example`).

## Project structure

```
Solution/
  app/      Flask app: blueprints, services, models, templates, static files
  tests/    pytest suite
  docs/     architecture and change notes
  run.py    starts the server
```

More detail: [Solution/README.md](Solution/README.md) and [Solution/docs/ARCHITECTURE.md](Solution/docs/ARCHITECTURE.md).
