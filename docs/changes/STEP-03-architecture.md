# Step 3 — Architecture and design restructure

**Date:** 2026-09-27
**Status:** Done. 204 passed, 2 xfailed. Coverage of `app/`: **100%** (the run now fails if it drops below 100%)

See [../ARCHITECTURE.md](../ARCHITECTURE.md) for the full picture: layers, folder structure and design decisions.

## Why
The whole app was one 1,300-line `index.py`:
- every route re-reflected tables (`autoload=True`) on every request
- hospital/doctor names were fetched in loops (N+1 queries)
- templates read data by position (`row[3]`)
- login/role checks were copy-pasted into every route, and some were missing
- 3 separate navbars and a copied page header on every template
- the add and edit forms were duplicated, and the edit forms couldn't upload images

## What changed

### Backend
| Before | After |
|---|---|
| `index.py` (all code) | `app/` package: factory, config, models, blueprints, services, utils |
| Table reflection per request | ORM models in `app/models.py` with relationships |
| Hardcoded config | `app/config.py`: Development/Testing/Production, chosen with `APP_ENV` |
| `if 'id' in session and ...` in each route | `@login_required`, `@admin_required`, one `before_request` guard for the admin blueprint |
| Business rules inside routes | `app/services/bookings.py`, `app/services/catalog.py` |
| Separate add + edit functions | One view per entity handles both (`hospital_form`, `doctor_form`, `facility_form`) |
| `init_db.py` with its own table definitions | `app/seed.py` + `flask --app run init-db` (`init_db.py` still works) |
| SQLAlchemy 1.4 (legacy API) | SQLAlchemy 2.0 + Flask-SQLAlchemy 3.1 |
| Default DB `Solution/medical.db` | `Solution/instance/medical.db` (Flask convention) |

`index.py` is still there as a 3-line entry point, so `python index.py` keeps working.

### Frontend (templates)
| Before | After |
|---|---|
| 30 flat templates, Bootstrap 4 | Folders by area: `layouts/ partials/ public/ auth/ account/ bookings/ admin/<entity>/ errors/`, Bootstrap 5.3 + Bootstrap Icons |
| 3 nav files (front/admin/user) | One `partials/navbar.html` that changes by role, with an active-page highlight |
| Messages rendered per page | One `partials/flash.html` (Bootstrap alerts with category colours) |
| Copy-pasted form markup | `partials/macros.html`: `field`, `textarea`, `hospital_select`, `file_input`, `search_form`, `page_header`, `empty`, `badges`, `status_badge`, `action_btn` |
| Positional `row[3]` | Named attributes: `doctor.hospital_name`, `facility.service_fees`, `booking.status_label` |
| Separate add/edit templates | One `form.html` per entity (edit form now has `multipart/form-data` and pre-selects the hospital) |
| Delete links with no warning | Delete buttons ask for confirmation |
| `static/` next to `index.py` | `app/static/` (images are also the upload folder) |

## Behavior changes (intentional)

| # | Change | Test that covers it |
|---|---|---|
| 1 | Unknown IDs return **404** instead of an empty page or a crash | `test_unknown_ids_return_404`, `test_booking_page_unknown_id_is_404`, `test_hospital_detail_unknown_id` |
| 2 | 404 page returns HTTP status **404** (was 200) | `test_unknown_url_returns_404_status` |
| 3 | Deleting a hospital also deletes its doctors, facilities and their bookings. Deleting a doctor, facility or user deletes their bookings | `test_delete_hospital_also_deletes_...`, `test_delete_user_also_deletes_their_bookings` |
| 4 | Test result spelling fixed: **Negative** (URL `/res_negitive/<id>` kept) | `test_set_test_result` |
| 5 | Search uses `GET ?search_query=`, so results can be bookmarked. POST still works, and admin hospital search uses the same field name | `test_search_works_with_get_query_string` |
| 6 | After a successful add/edit/register/booking the app **redirects** (Post/Redirect/Get) and shows a flash message | all form tests (the test client follows redirects) |
| 7 | Doctor booking rejects past dates, invalid dates and unknown slots on the server | `test_book_doctor_invalid_input` |
| 8 | "You already booked" (same user) and "Someone already booked" (another user) are now separate messages | `test_book_doctor_same_slot_twice`, `test_book_doctor_slot_taken_by_someone_else` |
| 9 | Facility booking image is optional, and the date is always today (set on the server) | `test_book_facility_without_image` |
| 10 | Email can't be changed from the profile/user edit form (the field is read-only) | `test_user_edit_cannot_change_email` |
| 11 | Normal users who open an admin URL are sent to their account with "Admin access required" (before, they were logged out) | `test_user_cannot_open_admin_listings` |
| 12 | Upload limit of 5 MB, with a friendly 413 page. There is also a friendly 500 page | `test_upload_too_large_returns_413`, `test_server_error_page` |

## Flaws fixed by the new architecture (xfail → pass)
From the Step 2 list, these are now fixed and their `xfail` markers were removed:

- #3 user could delete users. Fixed by the admin blueprint guard.
- #4 user could list users/doctors. Fixed by the admin blueprint guard.
- #5 user could set test results. Fixed by the admin blueprint guard.
- #6 booking trusted a hidden `user_id`. The booking now uses `g.user`.
- #7 user could cancel others' bookings. The query now filters by `user_id=g.user.id`.
- #8 and #9 `book_*` pages crashed on unknown ID. They now return 404.
- #10 404 status.

**Still open (xfail), planned for the Security step:** #1 plain-text passwords, #2 anyone can register as admin.

## Test suite changes
- `conftest.py` now builds the app with `create_app('testing', ...)`. The test client follows redirects on POST.
- New fixture `other_user_client` (a second normal user).
- New file `tests/test_unit.py`: models, services, uploads, config, error pages, CLI.
- The tests listed in "Behavior changes" were updated or added. Every other Step 2 test ran **unchanged** against the new code.
- `pyproject.toml`: coverage source is now `app`, with `fail_under = 100`.

| File | Tests |
|---|---|
| test_public.py | 33 |
| test_auth.py | 12 |
| test_account.py | 32 |
| test_admin.py | 112 |
| test_unit.py | 17 |
| **Total** | **206** (204 pass + 2 xfail) |

## Virtual environment
New or updated packages, installed in `venv/` only: `Flask-SQLAlchemy 3.1.1`, `SQLAlchemy 2.0.54` (was 1.4.54). See `requirements.txt`.
To update an existing checkout:
```bat
venv\Scripts\python -m pip install -r requirements-dev.txt
venv\Scripts\python init_db.py
```

## Verification
- `test.bat` → `204 passed, 2 xfailed`, coverage 100%
- Ran the server and requested every public and admin page as guest and as admin. All returned 200, and an unknown URL returned 404.
- Headless-browser screenshots of home, hospital detail and doctor booking pages look correct.

## Notes
- The old `Solution/medical.db` (from Step 1) is no longer used and can be deleted once the old server is stopped.
- The original code is still in `_original_backup/` for reference. It needs SQLAlchemy 1.4 to run.
