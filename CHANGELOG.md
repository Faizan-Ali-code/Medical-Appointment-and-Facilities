# Enhancement Changelog

Online Medical Appointments & Services (CS-619 final-year project, then refactored step by step).
Each step has its own detailed file in `docs/changes/`. The overall design is described in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The original code before Step 1 is kept at git tag `v1-original-fyp`.

| Step | Title | Tests | Coverage | Details |
|---|---|---|---|---|
| 1 | Virtual environment, configurable DB, smoke tests, 2 bug fixes | 8 | – | [STEP-01](docs/changes/STEP-01-environment-setup.md) |
| 2 | Full pytest test suite, 10 known flaws tracked as xfail | 133 + 10 xfail | 97% | [STEP-02](docs/changes/STEP-02-test-suite.md) |
| 3 | Architecture: app package, factory, blueprints, services, ORM, template structure, Bootstrap 5 | 204 + 2 xfail | 100% | [STEP-03](docs/changes/STEP-03-architecture.md) |
| 4 | UI polish: home hero, admin dashboard, user overview, dark mode, confirm modal, form validation | 225 + 2 xfail | 100% | [STEP-04](docs/changes/STEP-04-ui-polish.md) |
| 5 | Security: password hashing, no admin self-registration, CSRF, POST-only actions, safe uploads, headers | 284, 0 xfail | 100% | [STEP-05](docs/changes/STEP-05-security.md) |
| 6 | Demo data (20 hospitals, 40 doctors, 24 facilities) + pagination, filters, working days, live slot availability, appointment status, reschedule, schema upgrade | 332 | 100% | [STEP-06](docs/changes/STEP-06-features-and-demo-data.md) |
| 7 | Review fixes: double bookings blocked by the database, private patient files, session revocation, login lockout and rate limiting, CSP and SRI, archive instead of delete, time-slot and fee validation | **381** | 100% | [STEP-07](docs/changes/STEP-07-review-fixes.md) |

All 10 flaws found in Step 2 and all 12 problems from the Step 7 review are fixed.

## Possible next steps
8. **Notifications:** email/SMS confirmation and reminder before an appointment
9. **Reports:** admin charts (bookings per day, busiest doctors), CSV export
10. **Accounts:** password reset by email, breached-password check (Have I Been Pwned range API)
11. **Operations:** MySQL backup script, shared rate-limit storage (Redis) when running several processes
