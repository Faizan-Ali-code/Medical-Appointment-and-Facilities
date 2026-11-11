# Step 1 — Virtual environment, configurable database, smoke tests

**Date:** 2026-09-26
**Status:** Done, all 8 smoke tests pass, and the app runs on http://127.0.0.1:5000

## Why
- Flask and the other packages were not installed on this machine, and no `requirements.txt` existed.
- The database URL was hardcoded to MySQL (`root:@localhost`). The app crashed on startup if XAMPP/MySQL was not running.
- There was no way to check that a change didn't break anything.

## What changed

| File | Change |
|---|---|
| `venv/` | New virtual environment. Packages are installed here, not globally |
| `requirements.txt` | New file. Pinned package versions |
| `.env.example` | New file. Settings template (`DATABASE_URL`, `SECRET_KEY`, `FLASK_DEBUG`) |
| `.gitignore` | New file. Ignores `venv/`, `.env`, `*.db`, `__pycache__/` |
| `init_db.py` | New file. Creates all tables and loads the same sample data as `medicalappointmentsfinal.sql`. Works on SQLite and MySQL |
| `tests/test_smoke.py` | New file. 8 tests covering every page (guest/user/admin), login, search, register, doctor booking, facility booking and add hospital |
| `setup.bat`, `run.bat`, `test.bat` | New files. One-click setup, run and test |
| `_original_backup/` | Copy of the original `index.py` and `templates/` |
| `index.py` | Config changes and bug fixes (see below) |

### `index.py` changes
1. **Config from `.env`**: `DATABASE_URL`, `SECRET_KEY`, `FLASK_DEBUG`. If `DATABASE_URL` is not set, the app uses a local SQLite file, `medical.db`.
2. `UPLOAD_FOLDER` is now an absolute path, so it works from any working directory.
3. **Bug fix:** booking `date` was sent to the DB as a string. It is now converted to a Python `date` object (`book_doctor`, `book_facilities`).
4. **Bug fix:** a normal user opening `/hospitals` or `/facilities` crashed with `TemplateNotFound` (`user_hospitals.html` / `user_facilities.html` don't exist). The user is now redirected to the public Hospitals / Facilities page.

## How to run
```bat
setup.bat     :: first time only
run.bat       :: start the app
test.bat      :: run smoke tests
```
To use MySQL (XAMPP): import `medicalappointmentsfinal.sql` in phpMyAdmin, then put this in `.env`:
```
DATABASE_URL=mysql+mysqlconnector://root:@localhost/medicalappointmentsfinal
```

## Verification
- `test.bat` → `Ran 8 tests ... OK`
- Ran the server and requested `/`, `/fdoctors`, `/ffacilities`, `/detail/3`, `/login` and a static image. All returned 200.

## Login credentials (sample data)
- Admin: `admin@yahoo.com` / `admin`
- User: `user@yahoo.com` / `user`
