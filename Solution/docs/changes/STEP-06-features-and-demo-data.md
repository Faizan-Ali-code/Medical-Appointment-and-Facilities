# Step 6 — Demo data and new features

**Date:** 2026-09-27
**Status:** Done. **332 passed.** Coverage of `app/`: **100%**

## Part A — Demo data

`flask --app run seed-demo` adds realistic sample data so the app looks alive:

| What | Count | Details |
|---|---|---|
| Hospitals | **20** | In 10 cities (Lahore, Karachi, Islamabad, Rawalpindi, Multan, Faisalabad, Peshawar, Quetta, Hyderabad, Sialkot), each with an address, phone and description |
| Doctors | **40** | 2 per hospital, across 15 specializations (Cardiologist, Pediatrician, Dentist, ENT, …), with fees, time slots and **working days** |
| Facilities | **24** | Labs, radiology, cardiac diagnostics, physiotherapy, eye testing and pathology, each with services and matching fees |
| Patients | 6 | `patient1@demo.com` … `patient6@demo.com`, password **`patient123`** |
| Bookings | ~35 doctor + 18 test bookings | Past (completed/cancelled) and upcoming (booked/cancelled), plus pending and finished test results, so the dashboard and "My bookings" have content |

- **All names, addresses and phone numbers are fictional.** Each description says "(Demo record: fictional hospital.)". No real hospital is named, and no real hospital's photo is used.
- **Images are generated SVGs** (`app/static/images/demo/`): a coloured cover with a hospital illustration for each hospital, and an initials avatar for each doctor. They are small, sharp at any size, and work in dark mode.
- The data is generated with a fixed random seed, so it is the same every time.
- Running `seed-demo` twice is safe: the second run prints "Demo data is already loaded." `seed-demo --reset` recreates the database with the original sample data plus the demo data.
- `setup.bat` now loads the demo data automatically.

## Part B — New features

### 1. Pagination
- Public hospital and doctor cards show 9 per page (3×3). Tables show 10 per page: facilities, all admin lists, doctor/facility bookings, and the user's own bookings.
- "Showing 1–9 of 21 hospitals" plus page links with « ».
- Page links **keep the search and filters** (`?search_query=…&specialization=…&page=2`).
- Row numbers continue across pages (page 2 starts at 11).
- A page number past the end shows the last page, and a negative number shows page 1.

### 2. Filters
| Page | Filters |
|---|---|
| Home (hospitals) | City dropdown (built from the data) |
| Doctors | Search + **Specialization** + **Hospital** |
| Facilities | Search + **Hospital** |

The dropdowns submit on change (small JS), and there is a "Clear filters" link.

### 3. Doctor working days
- New column `doctors.days` (for example `Mon,Wed,Fri`; empty means every day).
- The admin doctor form has day toggle buttons (Mon … Sun).
- Doctor cards and the booking page show "Mon, Wed, Fri" or "Every day".
- Booking on a day the doctor does not work is rejected with a clear message ("… is not available on Tuesdays. Working days: Mon").

### 4. Live slot availability
- New JSON endpoint `GET /api/doctors/<id>/availability?date=YYYY-MM-DD` returns the working day flag, the past-date flag and each slot's free/booked status.
- On the booking and reschedule pages, choosing a date **disables booked slots** ("10:10 AM (booked)") and shows "3 slots available", "doctor does not work on this day" or "All slots are booked".
- The server still validates everything. The JS only helps the user.
- `&exclude=<booking id>` lets a user rescheduling their own booking see their current slot as free. It works only for the booking's owner; anyone else gets 404.

### 5. Appointment status
- New column `doctor_bookings.status`: **booked**, **completed** or **cancelled**.
- **Cancel no longer deletes the row.** It sets `cancelled`, so the history stays visible, and the slot becomes free for others.
- Only upcoming *booked* appointments can be cancelled or rescheduled.
- Admin doctor-bookings page: **Completed** and **Cancel** buttons (POST + CSRF), plus the existing permanent Remove.
- Status badges with icon + label: Booked (calendar), Completed (check), Cancelled (x).
- The dashboard counts and lists only *booked* upcoming appointments.

### 6. Reschedule
- "Reschedule" button on the user's upcoming bookings opens `/user_docbookings/<id>/reschedule`.
- Pick a new date and slot, using the same live slot picker as booking. All booking rules apply: future date, working day, free slot.
- Keeping the same slot is allowed.
- Only the owner can reschedule; anyone else gets 404.

### 7. Schema upgrade for existing databases
New columns must not break an existing database (SQLite or the XAMPP/MySQL one). A small upgrader, `app/migrations.py`, adds missing columns with `ALTER TABLE … ADD COLUMN` and never deletes data. It runs:
- automatically when the server starts (`run.py`)
- in `flask init-db` and `flask seed-demo`
- on demand: `venv\Scripts\flask --app run upgrade-db`

`medicalappointmentsfinal.sql` also has the two new columns.

## Security note
The admin "set status" action accepts a `next` URL for redirecting back. It goes through a new `safe_next()` helper that only allows paths on this site (not `https://evil…`, `//evil…` or `/\evil…`). This prevents an **open redirect**. It is tested.

## Files
| File | Change |
|---|---|
| `app/demo.py` | **New.** Demo data + SVG generator |
| `app/migrations.py` | **New.** `upgrade_schema()` |
| `app/models.py` | `Doctor.days`, `day_list`, `works_on()`. `DoctorBooking.status`, `status_label`, `is_active`. `WEEKDAYS` |
| `app/services/bookings.py` | Working-day check, cancelled slots free, `availability()`, `reschedule()`, `cancel()`, `set_doctor_booking_status()` |
| `app/services/catalog.py` | `*_query()` builders with filters, `paginate()`, `cities()`, `specializations()` |
| `app/services/stats.py` | Upcoming = booked and today or later |
| `app/blueprints/public.py` | Filters + pagination, availability API |
| `app/blueprints/bookings.py` | Cancel = status, reschedule route, paginated lists |
| `app/blueprints/admin.py` | Paginated lists, working days, booking status route |
| `app/seed.py` | `upgrade-db`, `seed-demo` commands |
| `app/utils/__init__.py` | `safe_next()` |
| `app/__init__.py` | `page_url()` template helper |
| `run.py` | Auto schema upgrade on start |
| Templates | `ui.pagination`, `ui.rownum`, `ui.booking_status_badge`, `ui.working_days`. New `bookings/_slot_picker.html` and `bookings/reschedule.html`. Filter bars. Day toggles |
| `app/static/js/app.js` | Live slot availability, auto-submit filters |
| `medicalappointmentsfinal.sql` | `doctors.days`, `doctor_bookings.status` |
| `setup.bat` | Loads the demo data |

## Tests
New file **`tests/test_features.py`** (47 tests):
- demo counts, idempotency and XML escaping; demo login; CLI with and without `--reset`
- pagination: pages, out-of-range, filters kept in links, admin lists, row numbers
- filters: city, specialization, hospital (doctors and facilities)
- working days: model, rejected booking, display, admin form save/show (including "all days" and "none")
- availability API: free/booked slots, past date, non-working day, bad date (400), unknown doctor (404), `exclude` only for the owner
- status: cancelled slot re-bookable, cancelled not "upcoming", admin completed/cancel, unknown status, **safe redirect** (4 cases), user can't change status, badges
- reschedule: full flow, same slot, taken slot, bad date, inactive booking, other user (404)
- schema upgrade on a database with the *original* tables, and the `upgrade-db` CLI

Updated: `test_account.py` (cancel keeps history; past booking can't be cancelled) and `test_ui.py` (result count text).

| File | Tests |
|---|---|
| test_public.py | 33 |
| test_auth.py | 18 |
| test_account.py | 39 |
| test_admin.py | 127 |
| test_unit.py | 32 |
| test_ui.py | 23 |
| test_security.py | 13 |
| test_features.py | 47 |
| **Total** | **332 passed** |

## Verification
- `test.bat` → 332 passed, coverage 100%
- `flask seed-demo` on the real `instance/medical.db` → 20 hospitals, 40 doctors, 24 facilities, 6 patients. Running it again → "already loaded"
- Headless Edge screenshots with demo data, all checked:
  - home (21 hospitals, city filter, pagination)
  - doctors filtered by Cardiologist
  - booking page (working days)
  - patient's bookings (Reschedule/Cancel)
  - admin dashboard (16 upcoming, 7 pending)
  - admin doctor form (day toggles)
- Reschedule page in a real browser: the other patient's slot showed as `05:00 PM (booked)` (disabled), the user's own `07:00 PM` stayed selected, and the page said "4 slots available."
