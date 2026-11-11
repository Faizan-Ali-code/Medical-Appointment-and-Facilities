# Enhancement Changelog

Online Medical Appointments & Services (CS-619). Each step has its own detailed file in `docs/changes/`.
The overall design is described in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

| Step | Title | Tests | Coverage | Details |
|---|---|---|---|---|
| 1 | Virtual environment, configurable DB, smoke tests, 2 bug fixes | 8 | – | [STEP-01](docs/changes/STEP-01-environment-setup.md) |
| 2 | Full pytest test suite, 10 known flaws tracked as xfail | 133 + 10 xfail | 97% | [STEP-02](docs/changes/STEP-02-test-suite.md) |
| 3 | Architecture: app package, factory, blueprints, services, ORM, template structure, Bootstrap 5 | 204 + 2 xfail | 100% | [STEP-03](docs/changes/STEP-03-architecture.md) |
| 4 | UI polish: home hero, admin dashboard, user overview, dark mode, confirm modal, form validation | 225 + 2 xfail | 100% | [STEP-04](docs/changes/STEP-04-ui-polish.md) |
| 5 | Security: password hashing, no admin self-registration, CSRF, POST-only actions, safe uploads, headers | **284, 0 xfail** | 100% | [STEP-05](docs/changes/STEP-05-security.md) |

| 6 | Demo data (20 hospitals, 40 doctors, 24 facilities) + pagination, filters, working days, live slot availability, appointment status, reschedule, schema upgrade | **332** | 100% | [STEP-06](docs/changes/STEP-06-features-and-demo-data.md) |

All 10 flaws found in Step 2 are fixed.

## Possible next steps
7. **Notifications:** email/SMS confirmation and reminder before an appointment
8. **Reports:** admin charts (bookings per day, busiest doctors), CSV export
9. **Hardening:** login rate limiting, Content-Security-Policy, password reset by email
10. **Deployment:** production server (waitress/gunicorn), HTTPS, MySQL backup script
