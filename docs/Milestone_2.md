# Milestone 2 — Core AI booking, owner review

22 October 2026, Asia/Riyadh. Authorization: owner's attached Prompt 07 states
Milestone 1 completed/reviewed and requests Milestone 2. Only M2 was implemented.
Approved BRD, SPEC, AGENTS and design HTML were not changed.

## Delivered behavior and files

- `backend/prompts/booking_agent.md`: editable prompt v4. Previous versions and
  precise observed changes are in `docs/archive/prompt_versions/`.
- `backend/agent.py`, `schemas.py`: local Ollama Chat API with JSON-schema output,
  strict Pydantic validation, bilingual extraction, and grounded natural wording
  with server fallback. No model database access or model-executed tools.
- `backend/sessions.py`, `chat_service.py`: employee-bound random sessions, bounded
  recent context, retained draft fields, missing/ambiguous-field questions, room
  selection and one pending offer. Material edits and employee switches invalidate
  old offers. Unequivocal natural consent and the confirmation button use the same
  server booking service. Ambiguous, conditional, quoted or negative consent does
  not write. An uncertain commit keeps the same key and blocks material edits.
- `backend/booking_service.py`, updated `firestore_store.py`: actual room search,
  capacity/type/maintenance checks, overlap checks, labelled type alternatives,
  future-time and single-Riyadh-day validation. UTC Firestore timestamps. Stable
  offer ID is also booking ID. A transaction reads employee, room, booking,
  `room_days/{room_id}_{YYYYMMDD}` and existing same-room bookings before writing
  booking + interval atomically. The extra same-room booking read also protects
  against preexisting bookings lacking coordination records. Every successful
  commit is followed by persisted verification; uncertain outcomes are reconciled
  using the same booking ID.
- Updated `backend/routes.py`, `main.py`: typed `POST /api/chat` and
  `POST /api/bookings/confirm`, local POST CORS. `discard_offer` on the chat route
  clears the old employee's offer on switching, without invoking the model or
  introducing another endpoint.
- Updated `frontend/src/{App,components/ChatPanel}.jsx`, `api.js`: real messages,
  loading/error states, actual cards and offer review, typed/button confirmation,
  verified receipt. Employee chat state is separate; theme/language/navigation
  preserve content. Example chips fill text only. Existing Concept A CSS/layout
  remains in use; no redesign or new pages.
- Updated `backend/requirements.txt`: small `tzdata` dependency (installed 2026.5),
  needed because Windows Python had no `Asia/Riyadh` zoneinfo data. Existing stack
  and model are unchanged. README now explains M2 operation and safe retries.
- Checks: updated `backend/tests/test_foundation.py`, `frontend/checks/check-foundation.mjs`;
  added `backend/{test_booking,test_model_contract,verify_live_m2,
  verify_concurrency_m2,audit_m2}.py`, `frontend/checks/check-chat.mjs` and the evidence
  JSON files below. Live verification scripts intentionally leave fictional test
  bookings in place; they never delete/reset/cancel data.

## Actual results

| Check | Observed result |
|---|---|
| Backend isolated tests | 21 tests passed: timing/UTC/boundaries, invalid dates and attendee types/counts, capacity/maintenance, alternatives, current-room transaction rechecks before writes, sessions, corrections, consent, outages/invalid JSON, uncertain-commit reconciliation, absence of M3 endpoints. Test doubles are explicitly isolated checks, not Firestore persistence evidence. |
| Frontend build | `npm.cmd run build` passed. |
| Typical, real Qwen + Firestore | English training request with 15 attendees, explicit date and 10:00–12:00 → suitable options → select T02 → “Yes, book it” → exactly one verified booking and interval. No writes at search/selection. |
| Messy, real Qwen + Firestore | Arabic request supplied training/date/10am only. Asked only attendance/end time. Follow-up supplied 15/noon and retained earlier fields. Room selection then «أؤكد الحجز» persisted a second verified booking. |
| Edge, real Qwen + Firestore | Requested the Typical room/slot after its commit. T02 excluded; T03/T04/T05 offered. No pending offer or new write for the conflicting request. Separately, an offer prepared before the Typical commit was rejected with `conflict` at transaction time. |
| Duplicate confirmation | Same offer returned the same persisted booking; collection count did not increase. |
| No pending offer | Actual natural-language confirmation returned `no_offer`, no booking. |
| Invalid timing | Actual past request, reverse-end request and explicit next-day overnight request were rejected without an offer/write. Overnight extraction omitted separate end_date, but 23:00→01:00 was deterministically rejected rather than assumed next day. Impossible date and equal endpoints were also covered by isolated validation tests. |
| Concurrent real transactions | Initially one winner and one `unknown`, with one slot write. After read-phase abort retry correction, a separate real simultaneous run returned one `confirmed`, one `conflict`, with exactly one persisted booking/interval for that slot. |
| Real browser round trip | Chrome → React → FastAPI → Qwen → real cards → pending offer → button confirmation → verified receipt. Checked loading/double-submit prevention, theme/language preservation during processing, employee isolation and 390/768/1440 px layouts; no page JS errors. Screenshots inspected in ignored `frontend/test-results/`. |
| Foundation browser regression | Separate role navigation, visual calendars, light/dark, RTL/LTR, employee drafts, responsive widths and disabled manager maintenance passed. |
| Independent persistence audit | Fresh Python process read all 5 identified bookings and exact matching daily intervals. No confirmed same-room overlaps. Inventory still 10 rooms/3 employees; 5 bookings/5 room_days. |
| Fresh backend process | Persisted browser booking still present; old in-memory session correctly returned HTTP 409. |
| Final connectivity/security checks | Backend/Ollama/Firestore `ok`. Actual `.env` and credential JSON ignored and untracked. No private-key/Firebase-key patterns found in application source or frontend bundle (bounded scan, not a security audit). No credential contents printed or uploaded. |

Evidence: `evidence/m2/m2_live_results.json` records exact user inputs, replies, draft state,
options and turn durations. `evidence/m2/m2_browser_results.json`, `evidence/m2/m2_concurrency_results.json`,
`evidence/m2/m2_persistence_audit.json` and `evidence/m2/m2_final_checks.json` contain supporting results.

The full live script stopped at the initial concurrency classification assertion,
after Typical/Messy/Edge and invalid-input checks succeeded. That failed run is
preserved as `evidence/m2/m2_live_attempt_02.json`; it is not relabelled a full-script pass.
Only the affected concurrency check was rerun after its fix, then independently
audited. An unrelated browser booking committed during that rerun, so its first
global-collection count assertion was overly broad (2 new records on different
dates). `evidence/m2/m2_concurrency_attempt_01.json` preserves that assertion failure; the
corrected slot-specific audit confirms 1 winner at the tested slot. The repeatable
concurrency script now counts only its own slot. No test failure was hidden by
deleting records.

## Identified live test bookings — left in Firestore

All names/identities are fictional. Times below are Asia/Riyadh; stored values are
UTC. These are test artifacts, not employee production bookings.

| Booking ID | Scenario | Employee / room | Local date and time |
|---|---|---|---|
| `2f9692be654b4aaa872eef497c8e72b3` | Typical | sara / T02 | 26 Nov 2026, 10:00–12:00 |
| `1467f3ff5e8d4b41aab4c78a17897693` | Messy | noura / T02 | 27 Nov 2026, 10:00–12:00 |
| `56de9cd9153a425394266f602776c468` | Initial concurrency winner | sara / T02 | 29 Nov 2026, 10:00–11:00 |
| `0c0aa05c2f2948de99f2746afeb3f611` | Corrected concurrency check winner | sara / T02 | 3 Dec 2026, 10:00–11:00 |
| `c6102c9f97be47378e7adb3e58df31c0` | Actual browser flow | sara / T04 | 24 Dec 2026, 14:00–15:00 |

## Observed problems, corrections and limits

1. Explicit end time omitted by early Qwen prompts → strict required schema keys,
   clearer missing-vs-ambiguous rules, full bilingual JSON examples and direct user
   message → v4 extracted the executed Typical range and completed Arabic Messy.
   Earlier failed attempt created no booking and remains in the evidence. This is
   not a claim of universal extraction accuracy; missing/invalid output fails closed.
2. SDK retries commit aborts but can propagate read-phase contention → bounded fresh
   transaction retry for `Aborted` → actual subsequent same-slot concurrency returned
   a definite conflict for the loser, without a double booking.
3. Qwen is 100% CPU here. Observed API turns in the recorded live run took about
   9–65 seconds; UI loading is essential. No model download or provider switch.
4. Some generated wording echoed details or failed output checks. Grounded server
   feedback was used in those turns; at least the recorded Typical options intro
   came from Qwen. Success receipts are always server-owned after persistence.
5. Less familiar consent phrasing may require rephrasing or using the review button.
   No general “yes” triggers a booking. Context is transient, with one FastAPI process.
6. Python 3.10 Google support warning and upstream TestClient deprecation warning
   remain; tests pass. Python 3.11+ is recommended. Physical service shutdown tests
   were not performed; failure handling was tested through injected exceptions.
7. Booking-calendar data, cancellation and admin maintenance remain disabled.
   Cross-type alternatives and maintenance changes at confirmation are covered by
   isolated rule/transaction checks; existing live room states were not modified to
   manufacture those conditions. No productivity comparisons/measurements or M4
   acceptance work are claimed.

Technical implementation checked against primary documentation:
[Ollama Chat API](https://docs.ollama.com/api/chat) for structured JSON format, and
[Firestore transactions](https://docs.cloud.google.com/firestore/native/docs/manage-data/transactions)
for atomic read-before-write operations and contention retries. The installed SDK's
transaction source was also inspected for the observed read-abort behavior.

No scope/technology/design decision needs additional approval. Stop for the owner's
M2 review. Proposed M3 only after explicit authorization: real employee/manager
calendar data, ownership-checked cancellation and manager maintenance operations.
