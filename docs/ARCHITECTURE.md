# Architecture

MediBook is a server-rendered Flask application organised in layers. Each layer only calls the layer below it.

```
 Browser
   │  HTTP (HTML forms, GET/POST)
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Blueprints (app/blueprints/)          HTTP layer             │
│   public · auth · account · bookings · admin                 │
│   read the request, call a service, flash a message,         │
│   redirect or render a template                              │
├──────────────────────────────────────────────────────────────┤
│ Services (app/services/)              business rules         │
│   catalog.py   listing + search queries (archived rows hidden)│
│   bookings.py  booking rules (slot free? date valid? ...)    │
├──────────────────────────────────────────────────────────────┤
│ Models (app/models.py)                data + relationships   │
│   User · Hospital · Doctor · Facility                        │
│   DoctorBooking · FacilityBooking  (+ unique constraints)    │
├──────────────────────────────────────────────────────────────┤
│ Flask-SQLAlchemy (app/extensions.py) → SQLite or MySQL       │
└──────────────────────────────────────────────────────────────┘
 Cross-cutting: app/utils/ (auth/sessions, passwords, uploads, time slots, form helpers)
                app/config.py (settings), app/seed.py (CLI commands), Flask-Limiter (rate limits)
```

## Folder structure

```
Medical-Appointment-and-Facilities/
├── app/                        the application package
│   ├── __init__.py             create_app() — application factory, security headers (CSP with nonce, HSTS)
│   ├── config.py               Development / Testing / Production config
│   ├── extensions.py           db, csrf, limiter
│   ├── models.py               ORM models (same tables as the original .sql dump, plus new columns)
│   ├── seed.py                 sample data + CLI commands (init-db, seed-demo, upgrade-db, create-admin,
│   │                           hash-passwords, secure-uploads)
│   ├── demo.py                 demo data (20 hospitals, 40 doctors, 24 facilities) + SVG image generator
│   ├── migrations.py           upgrade_schema(): adds new columns and unique indexes to existing databases
│   ├── blueprints/
│   │   ├── public.py           /  /fdoctors  /ffacilities  /detail/<id>  /api/doctors/<id>/availability
│   │   ├── auth.py             /login  /register  /logout  (lockout + rate limit)
│   │   ├── account.py          /account  /setting
│   │   ├── bookings.py         /book_doctor/<id>  /book_facilities/<id>  my bookings  /bookings/files/<id>
│   │   └── admin.py            /dashboard, hospitals, doctors, facilities, users, bookings (admin only)
│   ├── services/
│   │   ├── catalog.py          queries used by public + admin pages
│   │   ├── bookings.py         BookingError + booking rules
│   │   └── stats.py            counts/overviews for home, dashboard, account
│   ├── utils/
│   │   ├── __init__.py         search_term(), form_values(), safe_next()
│   │   ├── auth.py             login_user, logout_user, session validation, login_required, admin_required
│   │   ├── passwords.py        password policy
│   │   ├── timeslots.py        parse/format/sort time slots, "already passed today"
│   │   └── uploads.py          save_upload() (public or private folder), private_file_folder()
│   ├── templates/              layouts/base.html, partials/, public/ auth/ account/ bookings/ admin/ errors/
│   └── static/                 css/main.css, js/app.js, img/favicon.svg, images/ (public pictures only)
├── instance/                   medical.db (default SQLite database) and uploads/ (patient files, private)
├── tests/                      pytest suite, 100% line and branch coverage enforced (pyproject.toml)
├── docs/                       ARCHITECTURE.md + one file per enhancement step
├── run.py                      local development server
├── wsgi.py                     entry point for a production server (waitress), behind HTTPS
├── requirements.txt            runtime packages      (installed in venv/)
├── requirements-dev.txt        + pytest, coverage     (installed in venv/)
├── pyproject.toml              pytest + coverage settings
└── setup.bat / run.bat / test.bat
```

The original single-file final-year project (`index.py`, 1,318 lines, and its templates) is kept in the git
history: tag `v1-original-fyp`, folder `Solution/_original_backup/`.

## Key design decisions

| Decision | Why |
|---|---|
| **Application factory** (`create_app`) | Tests create an app with their own database, and config can be switched with `APP_ENV` |
| **Blueprints per area** | Each file is small and has one responsibility. The admin guard is written once for the whole blueprint (`@bp.before_request`) |
| **Service layer** | Booking rules can be unit-tested without HTTP, and the same query is reused by public and admin pages |
| **ORM models with relationships** | No N+1 loops or positional `row[3]` access. Templates use `doctor.hospital_name`, `facility.service_fees` |
| **Consistency in the database, messages in Python** | The services check a booking first, so the user gets a clear message. Two requests can pass that check at the same moment, so unique constraints decide (`uq_doctor_bookings_active_slot`, `uq_facility_bookings_open`, unique `users.email`) and a violation at commit becomes the same message. See "Concurrency" below |
| **Archive instead of delete** | Hospitals, doctors, facilities and users get `archived = 1`: they disappear from every list and page, but bookings that refer to them stay, so patient history is never lost. An admin can still remove a single booking entered by mistake |
| **Same table names as the SQL dump** | An existing MySQL database imported from the original dump keeps working; `migrations.py` adds what is new |
| **Hand-written schema upgrader, not Alembic** | A short, append-only list of additive changes (columns, unique indexes) that also has to work on a database imported from the original dump. With destructive or branching schema changes, Flask-Migrate/Alembic would be the right tool |
| **Comma-separated slots, services and fees** (kept from the original schema) | Normalising them into separate tables would break databases imported from the original dump and every admin form for little gain at this scale. Instead the admin forms validate and normalise them (times in one format, one numeric fee per service), and each booking stores the parsed start time (`starts_at`) so bookings sort by time, not by text. The trade-off: the database cannot enforce "one fee per service"; the form does |
| **Same URLs as before** | Links and bookmarks keep working, and the Step 2 test suite could be reused as a safety net |
| **Post/Redirect/Get + flash** | Refreshing the page doesn't resubmit a form, and messages are shown in one place (`partials/flash.html`) |
| **`g.user` + `current_user` in templates** | The logged-in user is loaded once per request |
| **Progressive enhancement JS** (`static/js/app.js`) | Dark mode, confirm dialog, live slot availability and form validation are added on top of plain HTML forms. The server re-checks everything |

## Security model

| Concern | Where it is handled |
|---|---|
| Who is logged in | `utils/auth.py`: `load_current_user` puts the user on `g.user`. A session is accepted only if its `session_version` matches the user's (logout and password changes increment it, so copied cookies stop working), the account is not archived, it was active within the last 30 minutes, and it is less than 12 hours old |
| Who may do what | `@login_required`, `@admin_required`, and the admin blueprint's `before_request` guard. Ownership checks are in the queries (`filter_by(user_id=g.user.id)`) |
| Passwords | scrypt hashes (`User.set_password`). Policy in `utils/passwords.py`: at least 8 characters, not a common password, not the user's name or email. Old plain-text rows are upgraded on login |
| Guessing passwords | Per account: 5 failures in a row lock it for 15 minutes (atomic SQL counter). Per client IP: Flask-Limiter, 10 POSTs/minute and 50/hour on `/login` and `/register`. Unknown emails take as long as known ones |
| Seeded accounts | No fixed passwords: `flask init-db` and `seed-demo` generate random ones and print them once |
| Forged requests (CSRF) | `extensions.csrf` (Flask-WTF). Every POST form includes `ui.csrf_field()`. Data-changing routes are POST-only |
| Uploads | `utils/uploads.save_upload`: type allow-list, magic-byte check, random name, 5 MB limit. Hospital and doctor pictures go to `static/images`; patients' files go to `instance/uploads` and are served only by `/bookings/files/<id>` to their owner or an admin, with `Cache-Control: no-store` and a sandboxing CSP. `flask secure-uploads` moves files that older versions stored publicly |
| Browser defences | `app/__init__.py`: Content-Security-Policy with a per-request nonce for the one inline script (no `unsafe-inline`), `frame-ancestors 'none'`, HSTS over HTTPS, `nosniff`, Referrer-Policy, Permissions-Policy. CDN files are pinned with Subresource Integrity hashes |
| Configuration | `config.py`: production refuses a placeholder or short `SECRET_KEY`; `setup.bat` writes a random one. The Werkzeug debugger is opt-in (`FLASK_DEBUG=1`) and `run.py` refuses to expose it beyond localhost |

## Concurrency

Booking a slot is check-then-insert. Two patients who click "Book" at the same moment can both pass the check,
so the check alone cannot prevent a double booking. The database does:

* `doctor_bookings` has a unique constraint on `(doctor_id, date, slot, holds_slot)`. `holds_slot` is `1` while a
  booking occupies its slot and `NULL` once it is cancelled. Unique indexes treat NULLs as distinct (SQLite,
  MySQL, PostgreSQL), so any number of cancelled bookings can share a slot, but only one active booking can.
* `facility_bookings` does the same with `open_request` for "one pending test per user, facility and service".
* An event listener in `models.py` keeps `holds_slot`, `open_request` and `starts_at` in step with `status` and
  `slot` on every insert and update, whichever code path writes the row.
* `services/bookings._commit` turns the `IntegrityError` of the losing request into the normal "already booked"
  message. The failed-login counter is incremented with one `UPDATE ... SET failed_logins = failed_logins + 1`.

Tests in `tests/test_hardening.py` simulate the lost race by disabling the Python check.

## Request flow example: booking a doctor

1. `POST /book_doctor/3` → `bookings.book_doctor` view (404 if the doctor is archived)
2. `load_current_user` (before_request) has already set `g.user`
3. The view checks that the user may book (`_can_book`), then parses the date
4. It calls `services.bookings.book_doctor(user, doctor, date, slot)`:
   - date must be today or later, and a working day of the doctor
   - slot must be one of the doctor's slots and, for today, not already passed
   - slot must not already be booked (checked here, guaranteed by the unique constraint at commit)
5. On success it flashes "Booking Successful". On a `BookingError` it flashes the error
6. It redirects to `GET /book_doctor/3` (PRG), and the page shows the flash message

## Data model

```
User 1───* DoctorBooking *───1 Doctor *───1 Hospital
  │                                          │
  └──1───* FacilityBooking *───1 Facility *──┘
```

Columns added after the original dump (all added to older databases by `app/migrations.py`):

| Table | Columns |
|---|---|
| `doctors` | `days` (working days), `archived` |
| `doctor_bookings` | `status` (booked / completed / cancelled), `starts_at`, `holds_slot` |
| `facility_bookings` | `open_request` |
| `users` | `archived`, `session_version`, `failed_logins`, `locked_until` |
| `hospitals`, `facilities` | `archived` |
