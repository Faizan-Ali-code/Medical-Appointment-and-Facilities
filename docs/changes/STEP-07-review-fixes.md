# Step 7: Fixes from an external code review

**Status:** Done. 381 tests pass, line and branch coverage **100%**.

An independent review of the project found the problems below. Each one is fixed and has a test
(most of them in `tests/test_hardening.py`).

| # | Problem found | Fix | Tests |
|---|---|---|---|
| 1 | **Double booking under concurrency.** "Is the slot free?" was checked in Python, then the booking was inserted. Two requests at the same moment could both pass | Unique constraints in the database (`doctor_id, date, slot, holds_slot`; `user_id, facility_id, service, open_request`; `users.email`). A violation at commit becomes the normal "already booked" message | `test_lost_race_for_a_slot_is_rejected_by_the_database`, `test_lost_race_for_a_facility_test_is_rejected`, `test_duplicate_email_race_is_caught` |
| 2 | **Patients' files were public.** Prescriptions uploaded with a facility booking were saved in `static/images` and could be opened by anyone with the URL | Saved in `instance/uploads` and served only by `/bookings/files/<id>` to the patient or an admin (`no-store`, sandboxing CSP, PDFs as downloads). `flask secure-uploads` moves files saved by older versions | `test_patient_file_*`, `test_legacy_public_files_are_served_and_can_be_moved` |
| 3 | **Logout did not revoke the session.** Flask keeps the session in a signed cookie; a copied cookie stayed valid for 31 days | `session_version` per user, checked on every request and incremented on logout and password change. 30-minute idle timeout, 12-hour absolute limit | `test_copied_session_cookie_stops_working_after_logout`, `test_new_password_ends_other_sessions_but_not_this_one`, `test_session_expires_after_absolute_lifetime` |
| 4 | **No protection against password guessing**, minimum password length 6, and the seeded admin password `admin` published in the README | Account lockout (5 failures → 15 minutes, atomic counter); Flask-Limiter per client IP; minimum 8 characters, common passwords and the user's own name/email refused; random seed passwords printed by `init-db` | `test_account_locks_after_repeated_failures`, `test_rate_limit_per_client_ip`, `test_weak_passwords_are_rejected`, `test_seeded_accounts_have_no_fixed_passwords` |
| 5 | **Time slots sorted as text** (`10:00 AM` before `9:00 AM`) and slots earlier today could still be booked | Bookings store the parsed start time (`starts_at`) and sort by it; slots that already passed today are refused (and shown as "passed" in the form); admin form validates and normalises slots | `test_bookings_sort_by_time_of_day_not_text`, `test_slot_that_already_passed_today_cannot_be_booked`, `test_doctor_slots_are_normalised` |
| 6 | **Fees and services as free text** with no check that every service has a numeric fee | Admin forms require one numeric fee per service (and a numeric doctor fee). The comma-separated columns are kept for compatibility with the original dump; see ARCHITECTURE.md | `test_facility_form_needs_one_numeric_fee_per_service`, `test_doctor_form_rejects_bad_slots_and_fees` |
| 7 | **Deleting a hospital or user deleted patients' booking history** (cascade) | Hospitals, doctors, facilities and users are archived: hidden everywhere, bookings kept. A closed account cannot log in | `test_delete_hospital_archives_it_and_keeps_bookings`, `test_closed_account_keeps_bookings_and_cannot_login` |
| 8 | **"Security headers" covered only three headers**; CDN files without integrity check | Content-Security-Policy with a per-request nonce (no `unsafe-inline`), HSTS over HTTPS, Permissions-Policy; Subresource Integrity on the three CDN files | `test_content_security_policy_with_nonce`, `test_cdn_assets_have_subresource_integrity`, `test_hsts_only_over_https` |
| 9 | **Debugger on by default**, development server only, weak `SECRET_KEY` accepted in production | Debugger opt-in (`FLASK_DEBUG=1`), refused on non-local addresses; `wsgi.py` + waitress for deployment; production rejects placeholder/short keys and `setup.bat` writes a random one | `test_debugger_is_opt_in`, `test_production_refuses_weak_secret_keys` |
| 10 | **Test results were only Positive/Negative** and the status then read "Approved"; route `/res_negitive` | One route `POST /facbookings/<id>/result` with a free-text result (max 50 characters); status "Result ready" | `test_set_test_result*`, `test_result_visible_to_user` |
| 11 | **Sample data used a real hospital's photo, address and a Wikipedia text**, and a downloaded wallpaper | Replaced with fictional text and two hand-made SVG images | `test_home_lists_hospitals` |
| 12 | Search treated `%` and `_` typed by the user as SQL wildcards | Escaped in `catalog._contains` | `test_search_treats_wildcards_literally` |

## Schema changes

New columns and unique indexes are added to existing databases by `flask --app run upgrade-db` (also run by
`run.py`). If old data breaks a new unique index (for example two accounts with the same email), the index is
skipped with a warning naming it; fix the rows and run `upgrade-db` again.

## New dependencies

`Flask-Limiter` (rate limiting) and `waitress` (production WSGI server).
