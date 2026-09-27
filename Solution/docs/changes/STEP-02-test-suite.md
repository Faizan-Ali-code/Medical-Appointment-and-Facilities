# Step 2 — Full test suite (pytest + coverage)

**Date:** 2026-09-27
**Status:** Done. 133 passed, 10 xfailed (known flaws). Coverage of `index.py`: **97%**

## Why
Before changing the architecture we need a safety net. If a refactor breaks any page or feature, a test must fail.

## Design of the test suite
- **Black-box tests:** tests use only HTTP (Flask test client) and plain SQL (`rows` fixture). They don't import app internals, so the same tests will keep working after the refactor in Step 3.
- **Fresh database per test:** the `fresh_db` fixture recreates a temporary SQLite database with the sample data before every test. Your real `medical.db` is never touched.
- **Known flaws as `xfail(strict=True)`:** flaws that exist today are written as tests of the *correct* behavior and marked `xfail`. When a flaw is fixed, the test starts passing, and pytest reports `XPASS(strict)` as a failure, which reminds us to remove the marker. The list of known flaws therefore lives in the tests themselves.

## Files

| File | What it tests | Tests |
|---|---|---|
| `tests/conftest.py` | Fixtures: `client`, `user_client`, `admin_client`, `rows`, `upload_dir`, `fresh_db` | – |
| `tests/test_public.py` | Home/search, doctors, facilities, hospital detail, guest booking pages, nav, 404, static files | 33 |
| `tests/test_auth.py` | Login OK/fail, register, duplicate email, logout | 11 |
| `tests/test_account.py` | Login-required pages, account, settings, own doctor and test bookings, booking rules | 20 |
| `tests/test_admin.py` | Access control; hospitals, doctors, facilities, users CRUD; bookings and results | 79 |
| `pyproject.toml` | pytest and coverage configuration (`xfail_strict`, branch coverage) | – |
| `requirements-dev.txt` | pytest, pytest-cov, coverage (installed in `venv`) | – |
| `.vscode/settings.json` | VS Code uses the project's `venv` interpreter, and the Testing tab runs pytest | – |

Removed: `tests/test_smoke.py` (Step 1). All its cases are now covered by the new files.

## Known flaws found (tracked as xfail)

| # | Type | Flaw | Test |
|---|---|---|---|
| 1 | Security | Passwords stored as plain text | `test_password_is_not_stored_in_plain_text` |
| 2 | Security | Anyone can register as **admin** | `test_register_cannot_choose_admin_role` |
| 3 | Security | Normal user can delete any user (`/user_delete`) | `test_user_cannot_delete_users` |
| 4 | Security | Normal user can list all users/doctors (admin pages) | `test_user_cannot_list_all_users` |
| 5 | Security | Normal user can set test results | `test_user_cannot_set_test_result` |
| 6 | Security | Booking trusts `user_id` from a hidden form field | `test_book_doctor_ignores_forged_user_id` |
| 7 | Security | User can cancel other users' bookings | `test_cannot_cancel_other_users_booking` |
| 8 | Bug | `/book_doctor/<unknown id>` crashes (500) | `test_book_doctor_unknown_id` |
| 9 | Bug | `/book_facilities/<unknown id>` crashes (500) | `test_book_facility_unknown_id` |
| 10 | Bug | 404 page is returned with HTTP status 200 | `test_unknown_url_returns_404_status` |

Other flaws noticed while reading the templates (to be fixed in Steps 3–4):
- Edit forms (hospital/doctor) have no `enctype="multipart/form-data"`, so a new image can never be uploaded from the UI.
- The "Choose" option in the edit forms keeps the old hospital, but the list doesn't show which hospital is selected.
- Every page repeats the same header, and the nav is included separately on each page.
- Templates read data by position (`row[3]`), which breaks easily if a column changes.

## How to run
```bat
test.bat                    :: all tests + coverage (terminal + htmlcov\index.html)
test.bat -k admin           :: only tests whose name contains "admin"
test.bat tests\test_auth.py :: one file
```
VS Code: open the **Testing** tab (flask icon). Tests are discovered automatically from the `venv` interpreter.

## Coverage
```
index.py     97%
init_db.py   77%   (only the CLI print branches are missed)
TOTAL        96%
```
