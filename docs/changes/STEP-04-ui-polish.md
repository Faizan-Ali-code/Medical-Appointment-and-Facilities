# Step 4 — UI/Design polish

**Date:** 2026-09-27
**Status:** Done. 225 passed, 2 xfailed. Coverage of `app/`: **100%**

## Why
Step 3 gave every page the same structure. This step improves how the app looks and feels: a proper landing page, an admin overview, a useful user home, dark mode, and friendlier interactions.

## What changed

### New pages / sections
| Where | What |
|---|---|
| Home `/` | **Hero section**: headline, large search box, "Find a doctor" / "Book a test" buttons, and live counts of hospitals, doctors and facilities. When searching, it shows "N results for …" with a Clear link |
| **Admin dashboard** `/dashboard` (new) | Six stat tiles (hospitals, doctors, facilities, registered users, upcoming appointments, tests awaiting result), an upcoming-appointments table, and a pending-tests table with one-click Positive/Negative. Linked from the Manage menu and the admin account page |
| User account `/account` | New cards: **Upcoming appointments** (today and later) and **Latest test bookings**, with result and status |

### Look and feel
| Feature | Details |
|---|---|
| **Dark mode** | Moon/sun button in the navbar. It follows the OS setting by default, and the user's choice is saved in the browser (`localStorage`). The theme is set before the page paints, so there is no white flash |
| Theme-aware colours | Removed `table-light` / `text-bg-light`, which stayed white in dark mode. Table headers and badges now use Bootstrap CSS variables (`--bs-tertiary-bg`, …) |
| **Confirm dialog** | Delete/cancel buttons open a Bootstrap modal instead of the browser's `confirm()`. Any link with `data-confirm="…"` uses it. There is no inline JavaScript any more (`onclick=` removed) |
| **Form validation** | All POST forms use Bootstrap client-side validation (`needs-validation`), which shows red/green hints before submitting. Server-side checks still apply |
| Empty states | Icon + message, with a context-specific text such as "No upcoming appointments" or "All test results are up to date" |
| Status badges | Pending/Approved now show an icon next to the colour (hourglass / check), so status is not shown by colour alone |
| Pluralization | "1 doctor", "0 doctors", "1 facility" instead of "doctor(s)" |
| Favicon | `static/img/favicon.svg` (heart-pulse logo) |
| Accessibility | "Skip to content" link, `aria-label` on icon-only buttons, and hover animations are turned off when the OS asks for reduced motion |
| Responsive | Dashboard tables stack below 1400px, so no columns are cut. Checked the home page at phone width (500px) |

### Files
| File | Change |
|---|---|
| `app/services/stats.py` | **New.** `public_counts()`, `admin_overview()`, `user_overview(user)` |
| `app/blueprints/admin.py` | New `dashboard` route |
| `app/blueprints/public.py`, `account.py` | Pass counts / overview to templates |
| `app/templates/admin/dashboard.html` | **New** |
| `app/templates/partials/confirm_modal.html` | **New** |
| `app/templates/layouts/base.html` | Theme script, favicon, `hero` block, skip link, modal, `app.js` |
| `app/templates/partials/macros.html` | New `stat_tile`, `plural`. `empty` has an icon, `action_btn` uses `data-confirm`, `status_badge` has an icon |
| `app/templates/partials/navbar.html` | Dashboard link, theme toggle |
| `app/templates/public/hospitals.html`, `account/account.html` | Hero section, user overview |
| `app/static/js/app.js` | **New.** Theme toggle, confirm dialog, form validation |
| `app/static/css/main.css` | Hero, stat tiles, theme-aware table headers, empty states, reduced motion |
| `app/static/img/favicon.svg` | **New** |
| `tests/test_ui.py` | **New.** 21 tests |

## Tests
New `tests/test_ui.py` (21 tests) covers:
- hero counts, and that they follow the data
- search result count
- dashboard access control, tile values, lists and empty states
- user overview (upcoming only, results shown)
- layout assets (theme toggle, confirm modal, favicon, JS)
- delete buttons use `data-confirm` and have no `onclick`
- pluralization and status badge icon
- **template lint checks**: no light-only classes; every POST form has `needs-validation`

The coverage threshold (`fail_under = 100`) did its job during this step. The first run after adding the dashboard failed at 99.6% until the new code had tests.

| File | Tests |
|---|---|
| test_public.py | 33 |
| test_auth.py | 12 |
| test_account.py | 32 |
| test_admin.py | 112 |
| test_unit.py | 17 |
| test_ui.py | 21 |
| **Total** | **227** (225 pass + 2 xfail) |

## Virtual environment
No new Python packages. The new front-end assets are Bootstrap 5.3 and Bootstrap Icons (CDN, same as Step 3) plus a small local `app.js`.

## Verification
- `test.bat` → `225 passed, 2 xfailed`, coverage 100%
- Headless Edge screenshots checked: home (light and dark), dashboard (light and dark), user account, and home at phone width. The first dashboard screenshot showed a table column cut off at 1300px; the grid breakpoints were fixed and the page re-checked.
