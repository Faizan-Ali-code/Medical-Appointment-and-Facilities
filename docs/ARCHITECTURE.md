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
│   catalog.py   listing + search queries                      │
│   bookings.py  booking rules (slot free? date valid? ...)    │
├──────────────────────────────────────────────────────────────┤
│ Models (app/models.py)                data + relationships   │
│   User · Hospital · Doctor · Facility                        │
│   DoctorBooking · FacilityBooking                            │
├──────────────────────────────────────────────────────────────┤
│ Flask-SQLAlchemy (app/extensions.py) → SQLite or MySQL       │
└──────────────────────────────────────────────────────────────┘
 Cross-cutting: app/utils/ (auth decorators, uploads, form helpers)
                app/config.py (settings), app/seed.py (init-db CLI)
```

## Folder structure

```
Solution/
├── app/                        the application package
│   ├── __init__.py             create_app() — application factory
│   ├── config.py               Development / Testing / Production config
│   ├── extensions.py           db = SQLAlchemy()
│   ├── models.py               ORM models (same tables as the .sql dump)
│   ├── seed.py                 sample data + CLI commands (init-db, seed-demo, upgrade-db, create-admin, …)
│   ├── demo.py                 demo data (20 hospitals, 40 doctors, 24 facilities) + SVG image generator
│   ├── migrations.py           upgrade_schema(): adds new columns to existing databases
│   ├── blueprints/
│   │   ├── public.py           /  /fdoctors  /ffacilities  /detail/<id>  /api/doctors/<id>/availability
│   │   ├── auth.py             /login  /register  /logout
│   │   ├── account.py          /account  /setting
│   │   ├── bookings.py         /book_doctor/<id>  /book_facilities/<id>  my bookings
│   │   └── admin.py            /dashboard, hospitals, doctors, facilities, users, bookings (admin only)
│   ├── services/
│   │   ├── catalog.py          queries used by public + admin pages
│   │   ├── bookings.py         BookingError + booking rules
│   │   └── stats.py            counts/overviews for home, dashboard, account
│   ├── utils/
│   │   ├── __init__.py         search_term(), form_values()
│   │   ├── auth.py             login_user, logout_user, login_required, admin_required
│   │   └── uploads.py          save_upload()
│   ├── templates/
│   │   ├── layouts/base.html   the only full HTML page; everything extends it
│   │   ├── partials/           navbar, flash messages, footer, macros (form fields, tables…)
│   │   ├── public/ auth/ account/ bookings/
│   │   ├── admin/<entity>/     list.html + form.html (form is shared by Add and Edit)
│   │   └── errors/             404 and generic error page
│   └── static/                 css/main.css, js/app.js, img/favicon.svg, images/ (also the upload folder)
├── instance/medical.db         default SQLite database (created by init_db.py)
├── tests/                      pytest suite (see STEP-02 / STEP-03)
├── docs/                       ARCHITECTURE.md + one file per enhancement step
├── run.py                      start the dev server
├── index.py                    old entry point, still works (imports run.app)
├── init_db.py                  create tables + sample data
├── requirements.txt            runtime packages      (installed in venv/)
├── requirements-dev.txt        + pytest, coverage     (installed in venv/)
├── pyproject.toml              pytest + coverage settings
└── setup.bat / run.bat / test.bat
```

## Key design decisions

| Decision | Why |
|---|---|
| **Application factory** (`create_app`) | Tests create an app with their own database, and config can be switched with `APP_ENV` |
| **Blueprints per area** | Each file is small and has one responsibility. The admin guard is written once for the whole blueprint (`@bp.before_request`) |
| **Service layer** | Booking rules can be unit-tested without HTTP, and the same query is reused by public and admin pages |
| **ORM models with relationships** | No more N+1 loops or positional `row[3]` access. Templates use `doctor.hospital_name`, `facility.service_fees` |
| **Cascade deletes** | Deleting a hospital removes its doctors, facilities and their bookings. Deleting a user removes their bookings. No orphan rows |
| **Same table names as the SQL dump** | An existing MySQL database imported from `medicalappointmentsfinal.sql` works without migration |
| **Same URLs as before** | Links and bookmarks keep working, and the Step 2 test suite could be reused as a safety net |
| **Post/Redirect/Get + flash** | Refreshing the page doesn't resubmit a form, and messages are shown in one place (`partials/flash.html`) |
| **`g.user` + `current_user` in templates** | The logged-in user is loaded once per request. Views no longer pass `user_id` / `role` to every template |
| **One layout, one navbar** | The navbar changes by role (guest / user / admin) instead of three copied nav files |
| **Progressive enhancement JS** (`static/js/app.js`) | Dark mode, confirm dialog and form validation are added on top of plain HTML links and forms. The app still works if JavaScript fails to load |
| **Theme via Bootstrap CSS variables** | One stylesheet works in both light and dark mode, with no separate dark CSS |
| **Shared Add/Edit form** | One template and one view per entity. The edit form now supports image upload and pre-selects the hospital |

## Security model

| Concern | Where it is handled |
|---|---|
| Who is logged in | `utils/auth.py`: `load_current_user` puts the user on `g.user` for each request |
| Who may do what | `@login_required`, `@admin_required`, and the admin blueprint's `before_request` guard. Ownership checks are in the queries (`filter_by(user_id=g.user.id)`) |
| Passwords | `User.set_password` / `check_password` (scrypt). Old plain-text rows are upgraded on login |
| Forged requests (CSRF) | `extensions.csrf` (Flask-WTF). Every POST form includes `ui.csrf_field()`. Data-changing routes are POST-only |
| Uploads | `utils/uploads.save_upload`: type allow-list, magic-byte check, random name, 5 MB limit |
| Headers and cookies | `app/__init__.py` (`security_headers`) and `config.py` (cookie flags, production `SECRET_KEY` check) |

## Request flow example: booking a doctor

1. `POST /book_doctor/3` → `bookings.book_doctor` view
2. `load_current_user` (before_request) has already set `g.user`
3. The view checks that the user may book (`_can_book`), then parses the date
4. It calls `services.bookings.book_doctor(user, doctor, date, slot)`:
   - date must be today or later
   - slot must be one of the doctor's slots
   - slot must not already be booked
5. On success it flashes "Booking Successful". On a `BookingError` it flashes the error
6. It redirects to `GET /book_doctor/3` (PRG), and the page shows the flash message

## Data model

```
User 1───* DoctorBooking *───1 Doctor *───1 Hospital
  │                                          │
  └──1───* FacilityBooking *───1 Facility *──┘
```
`doctors.days` (working days) and `doctor_bookings.status` (booked / completed / cancelled) were added in Step 6. `app/migrations.py` adds them to older databases.

`slots`, `services` and `fee` are stored as comma-separated text, as in the original database. The models expose them as lists (`slot_list`, `service_list`, `service_fees`).
