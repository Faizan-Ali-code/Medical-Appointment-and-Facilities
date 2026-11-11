# Step 5 — Security hardening

**Date:** 2026-09-27
**Status:** Done. **284 passed, 0 xfailed.** All 10 flaws found in Step 2 are now fixed. Coverage of `app/`: **100%**

## Summary of fixes

| # | Risk | Before | After |
|---|---|---|---|
| 1 | Password theft | Passwords stored as **plain text** | Hashed with **scrypt** (werkzeug). Old plain-text rows are upgraded automatically on the next successful login, or all at once with `flask hash-passwords` |
| 2 | Privilege escalation | Register form had a **Role: Admin** option | Registration always creates a normal `user`. Admins are created with `flask create-admin` |
| 3 | CSRF (Cross-Site Request Forgery) | Any website could make a logged-in admin's browser delete data | **Flask-WTF CSRFProtect**: every POST form carries a secret token. Requests without it get a 400 page |
| 4 | Destructive GET links | Delete / cancel / set-result / logout were plain links | **POST only**. Buttons are small forms with a CSRF token, and a GET request returns a friendly **405** page |
| 5 | Malicious uploads | Any file type, and the original filename was reused (overwrites, path tricks) | Allow-list of types, **content check by magic bytes** (a `.png` must really be a PNG), and a **random UUID filename**. Hospital/doctor images accept PNG/JPG/GIF/WebP. Facility bookings also accept PDF |
| 6 | Orphan upload files | A file was saved even when the booking was rejected | Booking rules are checked **before** the file is saved |
| 7 | Weak passwords | No rule | Minimum length 6 (`MIN_PASSWORD_LENGTH`) at register and password change |
| 8 | Password shown in HTML | Settings form was pre-filled with the password | Password field is empty ("leave empty to keep"). The hash is never rendered (tested) |
| 9 | Session fixation | – | Login clears the old session first (tested) |
| 10 | Cookie theft / clickjacking | Default cookies, no headers | `HttpOnly`, `SameSite=Lax`, and `Secure` in production. Headers `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` |
| 11 | Weak secret key | Hardcoded `'FinalProject'` | Read from `SECRET_KEY`. **Production refuses to start** with the default key |
| 12 | Duplicate accounts by case | `Ali@x.com` and `ali@x.com` were different users | Emails are stored lowercase and compared case-insensitively |
| 13 | Admin locks themself out | Admin could delete their own account | Blocked with a message |

## Files changed
| File | Change |
|---|---|
| `app/extensions.py` | `csrf = CSRFProtect()` |
| `app/config.py` | Cookie flags, `MIN_PASSWORD_LENGTH`, `PASSWORD_HASH_METHOD` (scrypt, or fast pbkdf2 in tests), `SECRET_KEY` from env, production check |
| `app/__init__.py` | CSRF init, security headers (`after_request`), 400 (CSRF) and 405 error pages, `is pdf` template test |
| `app/models.py` | `User.set_password`, `check_password` (with plain-text upgrade), `has_hashed_password` |
| `app/seed.py` | Sample users are hashed. New CLI commands `create-admin` and `hash-passwords` |
| `app/utils/uploads.py` | Rewritten: `UploadError`, allow-lists `IMAGES` / `IMAGES_AND_PDF`, magic-byte check, UUID names |
| `app/blueprints/auth.py` | Hash check, lowercase email, no role on register, password length, POST-only logout |
| `app/blueprints/account.py` | Optional password change with length check |
| `app/blueprints/admin.py` | POST-only delete/result routes, upload errors shown, can't delete self |
| `app/blueprints/bookings.py` | POST-only cancel, PDF/image upload, check before saving the file |
| `app/services/bookings.py` | New `check_facility_booking()` |
| Templates | `ui.csrf_field()` in every POST form, `ui.post_btn` for data-changing buttons, logout as a form, `ui.upload_link` (PDF icon or thumbnail), no role on register, password hint |
| `app/static/js/app.js` | Confirm dialog now works with forms (submits after "Yes") |
| `medicalappointmentsfinal.sql` | `users.password` widened to `varchar(255)` so hashes fit |
| `requirements.txt` | + `Flask-WTF 1.3.0`, `WTForms 3.2.2` (installed in `venv/`) |

## If you use MySQL (XAMPP) with an existing database
The hash is about 100–160 characters long. The old column was `varchar(50)`. Run this once in phpMyAdmin:
```sql
ALTER TABLE users MODIFY password varchar(255);
```
Then either just log in (each user's password is upgraded on login) or hash everything at once:
```bat
venv\Scripts\flask --app run hash-passwords
```

## New commands
```bat
venv\Scripts\flask --app run create-admin      :: asks for email, name, password
venv\Scripts\flask --app run hash-passwords    :: hash old plain-text passwords
```

## Tests
- New file **`tests/test_security.py`** (13 tests). It runs with the real CSRF check switched on: no token → 400, forged token → 400, token from the page → works; forged cross-site delete is blocked; logout needs a token; security headers; cookie flags; the hash is never rendered.
- `test_auth.py`: the two remaining xfails are now normal tests. Added: hashed seed, short password, case-insensitive email, **plain-text upgrade on login**, empty password can't log in, session fixation.
- `test_account.py`: password kept when the field is empty, password change, short password, password never shown, PDF upload, fake PDF rejected, **no file saved for a rejected booking**.
- `test_admin.py`: all state-changing URLs reject GET (405); guests and users can't POST them; unknown IDs return 404 on POST; bad uploads rejected (wrong content, `.html`, PDF for hospital image, no extension); random stored filename; admin can't delete self.
- `test_ui.py`: lint that **every POST form has a CSRF token**; delete buttons are POST forms; logout is a POST form.
- `test_unit.py`: upload accept/reject matrix, hashing round-trip, production uses scrypt, production refuses the default secret, cookie flags, `create-admin` and `hash-passwords` CLI.
- The test config uses fast `pbkdf2:sha256:1000` hashing. With scrypt the suite took more than 5 minutes; with pbkdf2 it takes about 40 seconds. Production still uses scrypt.

| File | Tests |
|---|---|
| test_public.py | 33 |
| test_auth.py | 18 |
| test_account.py | 38 |
| test_admin.py | 127 |
| test_unit.py | 32 |
| test_ui.py | 23 |
| test_security.py | 13 |
| **Total** | **284 passed, 0 xfail** |

## Verification
- `test.bat` → `284 passed`, coverage 100%
- Real server (dev config, CSRF on):
  - `flask hash-passwords` hashed the 3 existing passwords in `instance/medical.db`
  - login without a token → 400; login with the page's token → 200, and the dashboard opens
  - `GET /hospitals/delete/3` → 405
  - responses carry `X-Frame-Options: DENY` and `X-Content-Type-Options: nosniff`

## Not done yet (possible future work)
- **Login rate limiting** (e.g. Flask-Limiter) against password guessing
- **Content-Security-Policy** header (needs a nonce for the small inline theme script)
- Email verification and password reset by email
- HTTPS is required in production for `Secure` cookies. This depends on the hosting setup.
