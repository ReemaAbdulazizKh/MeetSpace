# Milestone 3 — Calendar & Admin Integration

22 October 2026, Asia/Riyadh. Implemented under the owner's attached Prompt 08.
M3 only; stop for owner review. Approved BRD, SPEC, AGENTS and Concept A HTML were
not modified. Qwen2 7B, the editable v4 prompt, Firestore and the existing design
remain unchanged. No new dependencies, public hosting or authentication system.

## Implemented behavior

Employee calendar reads only the selected employee's actual bookings through
FastAPI. Month navigation and selectable-day details show room name, local
date/time and confirmed/canceled status. A cancellation dialog requests explicit
consent. The server checks ownership, reads booking and Riyadh room-day before
writes, then atomically marks the booking `canceled`, sets `canceled_at` and removes
only that booking's interval. Repeats preserve the original canceled state and do
not remove neighbors. Persisted booking/interval reads verify cancellation, even
when a network response may have hidden a committed transaction. The UI updates
from the verified response; failures prompt a refresh, without optimistic success.

The separate manager calendar displays all employee bookings, names and statuses.
The actual ten rooms have Available/Maintenance controls. A transaction updates
only the room's status; existing bookings are never canceled by maintenance.
Confirmation reads that same room document, so concurrent maintenance/confirmation
is serialized by Firestore. Restoring availability still respects capacity and
occupied periods. No calendar cell creates bookings; New booking navigates to chat.

Calendars group timestamps and display times in Asia/Riyadh regardless of the
browser timezone. Light/Dark, Arabic RTL/English LTR, responsive layout and separate
employee/admin navigation are preserved. Loading, genuine empty days, errors,
verified success and cancellation are distinct. All displayed inventory/bookings
come from Firestore; obsolete design-fixture fallbacks were removed. Refresh
actions reload other-tab changes; no realtime subscriptions were added.

## Files created or modified

| Files | Change |
|---|---|
| `backend/schemas.py`, `routes.py`, `main.py` | Typed booking views, explicit cancellation body, validated room status, four approved M3 endpoints and local PATCH CORS. Responses omit internal session/offer fields. Backend version 0.3.0. |
| `backend/firestore_store.py` | Employee-filtered query, cancellation/status transactions, persisted verification and reused bounded read-abort retry. No deletes/resets or startup writes. |
| `backend/booking_service.py` | Joined booking view data and protection against returning a canceled booking as a confirmed receipt. |
| `backend/chat_service.py` | Existing unsupported-action feedback now directs cancellation requests to My calendar; no chat cancellation action was added. |
| `frontend/src/components/Calendar.jsx`, `MyBookings.jsx`, `AdminPanel.jsx` | Connected existing calendar/detail/status layouts, owned cancellation with confirmation, manager inventory and maintenance controls, truthful feedback. |
| `frontend/src/App.jsx`, `api.js` | Selected employee passed to calendar, actual data only, PATCH client and M3 labels. Chat workflow retained. |
| `frontend/src/designData.js` | Removed obsolete preview fixtures. |
| `backend/tests/test_calendar_admin.py`, `test_booking.py` | New isolated M3 checks and updated milestone-specific assertions. |
| `backend/checks/verify_live_m2.py` | Optional report path so M3 regression preserves historical M2 evidence. |
| `backend/checks/verify_live_m3.py`, `audit_m3.py` | Actual Qwen regression + live M3 operations, then independent persisted-state audit. |
| `frontend/checks/check-calendar.mjs`, `check-calendar-states.mjs`, `check-foundation.mjs` | Actual browser calendar/admin/cancellation checks, explicit failure-feedback checks and updated maintenance-enabled expectation. |
| `README.md`, `docs/m3_*.json`, this file | Local instructions, exact observed evidence and review gate. |

Endpoints: `GET /api/bookings?employee_id=…`,
`POST /api/bookings/{id}/cancel` with `{employee_id, confirmed:true}`,
`GET /api/admin/bookings`,
`PATCH /api/admin/rooms/{id}/status` with `available` or `maintenance`.
Employee/role selection is still a demonstration mechanism, not secure login.

## Actual checks and outcomes

| Check | Observed outcome |
|---|---|
| Frontend production build | PASS: `npm.cmd run build` from `frontend/`. No deployment. |
| Backend isolated checks | PASS: 30 tests, including ownership/no-write failures, explicit consent, read-before-write cancellation, neighbor preservation, idempotency, uncertain acknowledgment reconciliation, status-only maintenance update, canceled-offer reconfirmation, view scope and error sanitization, plus existing M2 rules. Test doubles are isolated tests, not persistence evidence. |
| Actual Typical/Messy/Edge regression | PASS: full real Qwen/FastAPI/Firestore run. English complete request persisted after explicit confirmation; Arabic missing-data follow-up retained known fields and persisted after consent; conflict excluded the occupied room and returned alternatives. Duplicate/no-offer/invalid-time checks and simultaneous same-slot confirmation also passed. `evidence/m3/m3_booking_regression.json`. |
| Original five bookings in calendars | PASS: actual stored M2 IDs appeared in the correct employee calendar and in manager view. Other employees' bookings were absent from the selected employee view. |
| Foreign cancellation / missing consent | Actual HTTP 403 / 400; fixture unchanged. |
| Real cancellation | New fixture marked canceled with a real timestamp; matching interval removed, adjacent booking/interval preserved. Repeating cancellation left the record unchanged. Same room became searchable for the freed period while remaining blocked for the neighbor's period. |
| Maintenance | Actual enable/restore persisted. Search excluded the room while in maintenance. An already-reviewed pending offer was rejected at confirmation. Full booking snapshots were unchanged by maintenance. Restoring availability restored eligibility. |
| Concurrent maintenance and confirmation | PASS: real race returned `maintenance` for confirmation, no booking created for the rejected offer, room status verified. Original status restored afterward. |
| Actual browser actions | PASS: maintenance enabled/restored; dismissing cancellation dialog sent no write; accepting it updated the real fixture and calendar status. No cancel button remained for the canceled item. |
| Riyadh vs browser timezone | PASS in a Los Angeles browser: existing UTC 07:00 booking displayed 10:00 Riyadh on its correct day. New UTC 21:30 previous-day fixture appeared at 00:30 on the next Riyadh day, not the browser/UTC day. |
| Themes, languages, responsiveness | PASS: selected details survived Light/Dark and Arabic/English changes. Employee and manager layouts checked at 390/768/1440 px without horizontal overflow. No page JavaScript errors. Screenshots inspected in ignored `frontend/test-results/`. |
| Loading/empty/error/recovery | PASS: delayed real GET showed loading without false empty state; actual current-day empty state displayed afterward. Explicitly injected employee/admin HTTP 503 responses showed errors and no fake inventory/success; reload recovered actual API data. These injections were UI tests, not a physical Firestore outage. |
| Fresh-process persistence audit | PASS: all preexisting document hashes unchanged, including all five M2 bookings and their room-days. All confirmed bookings have exactly one matching interval; canceled bookings have none; no confirmed same-room overlaps. M01 restored to its original available status. |

Evidence: `evidence/m3/m3_live_results.json`, `evidence/m3/m3_booking_regression.json`,
`evidence/m3/m3_browser_readonly.json`, `evidence/m3/m3_browser_results.json`, `evidence/m3/m3_ui_state_checks.json`,
`evidence/m3/m3_persistence_audit.json`, `evidence/m3/m3_final_checks.json`.

Final Firestore inventory: **10 rooms, 3 employees, 11 bookings (9 confirmed,
2 canceled), 10 room_days**. No document was deleted. The original five M2 bookings
remain unchanged. Six additional fictional test bookings were disclosed and left
in place; only the two NEW cancellation fixtures were canceled:

| New booking ID | Purpose / owner / room | Riyadh slot | Final status |
|---|---|---|---|
| `4ac97cc38f4c4a31b0d1123a9dfaa634` | Typical regression / sara / T02 | 4 Dec 2026, 10:00–12:00 | confirmed |
| `9ccf6392a64e44f69224302a33ad852e` | Messy regression / noura / T02 | 5 Dec 2026, 10:00–12:00 | confirmed |
| `5856bd9fdccf4179b705d308fcce5ee4` | Concurrent confirmation winner / fahad / T02 | 7 Dec 2026, 10:00–11:00 | confirmed |
| `174a45989e2445b89826112b4696a2e3` | API cancellation fixture / fahad / M01 | 10 Jan 2027, 00:30–01:30 | canceled |
| `9493a19443ed413d990d5375c1302234` | Adjacent interval fixture / noura / M01 | 10 Jan 2027, 01:30–02:30 | confirmed |
| `f0220a64b01c4237b3b24ea59d60a4d2` | Browser cancellation fixture / sara / M02 | 10 Jan 2027, 14:00–15:00 | canceled |

The first three were created through the real model workflow. The last three are
explicit test setup through the existing validated server booking service, not a
new manual creation API or user-facing booking form. No seed initialization ran.

## Notes, remaining issues and next gate

Observed integration issue → correction → outcome: the M2 unsupported-action text
said cancellation was unavailable → now directs users to My calendar → chat still
does not cancel records; calendar cancellation is verified. Canceled receipts are
also explicitly rejected on reconfirmation, covered by the new test.

Routine check setup errors: an initial build command ran at the repository root
and failed because package.json is in frontend; rerunning there passed. A first
browser script used a relative API URL without a context base URL; setting the
local base URL fixed the check, and both read-only/full browser runs passed. No
application data was changed by those failed setup checks.

Open for M4: Qwen CPU latency (previously about 9–65 seconds; current regression
turn durations are recorded), extraction/response fallback limitations documented
in M2, final broad refinement/acceptance and actual measured productivity
comparisons. No model, prompt or performance tuning was undertaken in M3.
Python 3.10 Google-support and upstream TestClient deprecation warnings remain;
Python 3.11+ is recommended. No realtime synchronization or secure authentication
is claimed. No productivity results or pass rates were invented.

Repeatable commands are in README. M3 implementation is ready for owner review;
the MVP is not declared finally accepted. **Stop here; do not begin M4 without
explicit owner authorization.**
