# Milestone 4 — Verification & Prompt Optimization

Date: 22 October 2026. Scope: approved M4 only; no UI redesign, new product features, model replacement, hosting, presentation creation or database deletion.

## Changes and controlled comparison

Preserved the original v4 prompt unchanged in `archive/prompt_versions/m4_A_baseline.md`. Added RICE candidates B and B2; B was rejected after observed regressions. Production `backend/prompts/booking_agent.md` now uses B2: concise instructions with three complete bilingual JSON examples. All server validation, explicit consent, employee binding, pending-offer identity and transaction safeguards remain intact.

After completing prompt-only A/B/B2 measurements, changed `backend/agent.py` to omit the second wording generation only for `missing` responses. The existing bilingual server question already contains exactly the missing fields. Qwen still interprets every ordinary incoming message; room search and persistence remain server-owned. This separate technical phase is C, using the identical B2 prompt. Added a regression test for preserving that question without a redundant call.

Added read-only benchmark/report scripts, preserved raw evidence, and parameterized existing live/browser/audit scripts to write M4 evidence without overwriting M1–M3 reports. No frontend product source or styles changed. See `Prompt_Engineering_Log.md` for observed problem → prompt/code change → outcome.

## Actual response-time results

Real local `qwen2:7b`, temperature 0, num_predict 600, context 4096, FastAPI TestClient `/api/chat`, real Firestore. Two repeats per scenario per phase. Each Typical/Edge trial is one provisional-search turn; Messy includes initial request and follow-up. These are server HTTP times, **not full human booking-cycle times**. Confirmation and persistence are tested separately.

Mean seconds, with both individual trials in parentheses:

| Scenario | A original | B rejected | B2 prompt only | C B2 + technical change |
|---|---|---|---|---|
| Typical | 31.24 (45.52, 16.97) | 28.40 (35.61, 21.19) | 28.78 (39.64, 17.92) | 18.27 (18.09, 18.44) |
| Messy, two turns | 41.61 (42.30, 40.92) | 40.12 (39.79, 40.45) | 33.48 (33.59, 33.36) | 26.88 (26.32, 27.44) |
| Edge | 21.85 (21.68, 22.02) | 21.59 (22.01, 21.16) | 20.45 (20.56, 20.33) | 20.50 (20.10, 20.90) |

| Scenario | Correct trials A / B / B2 / C, including language | Calls per trial A / B / B2 / C | User turns per trial |
|---|---|---|---|
| Typical | 2/2 · 0/2 · 2/2 · 2/2 | 2 / 2 / 2 / 2 | 1 |
| Messy | 2/2 · 2/2 · 2/2 · 2/2 | 4 / 4 / 4 / 3 | 2 |
| Edge | 2/2 · 0/2 · 2/2 · 2/2 | 2 / 2 / 2 / 2 | 1 |

B lost supplied end times in three turns and extracted the wrong language in four English turns. It caused three unnecessary clarification turns. A/B2/C had no unnecessary clarification turns in these fixtures. B2 restored correct field extraction, retention and actual eligible options. Correctness counts are descriptive of these exact trials, not a general model pass rate. Raw harness assertions cover fields/options; `comparison.json` adds a language audit without changing raw reports.

B2 improved all three scenario means against A in this run, but its second Typical trial was slower (17.92 vs 16.97). C Edge was slightly slower than B2 (20.50 vs 20.45). C Typical retains exactly the same two-call path as B2: its lower time cannot be attributed to the missing-question code change. Different prompt-evaluation/cache costs explain much of that observed difference; no guaranteed Typical speedup is claimed. The defensible technical effect is one fewer model call for the missing-details turn, with a lower measured Messy mean here.

Mean Ollama total seconds per trial (excludes server/Firestore overhead):

| Scenario | A | B | B2 | C |
|---|---|---|---|---|
| Typical | 28.62 | 27.41 | 27.27 | 16.79 |
| Messy | 38.20 | 37.89 | 31.69 | 25.06 |
| Edge | 19.74 | 20.79 | 18.87 | 19.04 |

Excluded warm-ups: A 13.76s, B 1.11s, B2 1.04s, C 1.07s. A warm-up included about 11.67s model loading. Subsequent warm-ups were already loaded. They do not equalize all prefix caches. No concurrent model workload was started during comparisons. Hardware inspection reported 100% CPU on Intel Core Ultra 7 155H; decoding and prompt evaluation remain material costs. Raw per-call nanosecond load/prompt/decode metrics and output token counts are retained. No hardware upgrade was tested.

Limits: sequential phase order, small sample, cache effects and variable Firestore/network overhead. Exact inputs use Typical 2027-01-30, Messy 2027-01-31 and the real T02 conflict on 2026-11-26. Each report includes complete inputs, outputs, prompt/code hashes, fixed clock and state hashes. A/B/B2 code hashes match; C changes only the relevant agent code among the monitored production modules. All four benchmark phases left the entire Firestore snapshot unchanged.

Evidence: `evidence/m4/baseline_A.json`, `evidence/m4/optimized_B.json`, `evidence/m4/optimized_B2.json`, `evidence/m4/technical_C.json`, `evidence/m4/comparison.json`, `evidence/m4/benchmark_fixtures.json`. Instrumentation timestamp caveat and rerun commands are in the prompt log and README.

## Interaction quality and remaining limits

The RICE prompt is shorter (3,039 vs 3,848 characters), while retaining examples needed by this model. Shortening alone was insufficient, as rejected B demonstrates. B2 still sometimes repeats the authoritative options sentence in its optional Arabic introduction, with imperfect grammar. Baseline discarded six of eight optional introductions; B2 discarded six of eight as well. This wording problem is not claimed solved. Missing-details C uses one concise authoritative question; natural extraction and other optional contextual wording still use Qwen.

Observed semantic limitation in live regression: for “23:00 until 01:00 the next day”, Qwen omitted the explicit separate end date. The backend still rejected the reversed times and wrote no booking, but returned the end-time correction rather than the more specific cross-day explanation. The unit-tested same-local-day rule remains enforced; complete extraction of every overnight phrase is not claimed.

CPU latency remains noticeable. Python 3.10 Google SDK support warnings and the upstream TestClient/httpx deprecation warning remain; tests passed with the installed dependencies. A Python 3.11+ environment upgrade is recommended separately. Demo role switching is not authentication; sessions remain temporary and local. No productivity gains are inferred from model latency alone.

## Human productivity measurement

Prepared `Productivity_Measurement_Protocol.md` and `m4/productivity_results.csv`: Typical/Messy/Edge, both email+Excel and MeetSpace, two repeats each. Defines matched state, exact input sequence, active time per participant, elapsed/waiting time, correctness, actual errors/corrections, counterbalanced order and evidence. All 12 rows have **empty result fields**, including human TO-BE times, because no paired human trials have occurred. No estimates, invented zeroes or productivity percentages were entered. The owner will run and record these experiments; this does not block the authorized Agent verification work.

## Verification evidence

- `python -m unittest backend.tests.test_foundation backend.tests.test_booking backend.tests.test_model_contract backend.tests.test_calendar_admin -q`: **31 tests passed**. Includes field validation, single local day, future start, capacity/type/maintenance, touching boundaries, guarded explicit assent, invalid model JSON/outage, idempotency, unknown-write reconciliation, ownership and cancellation transactions. These are isolated checks, not claims of a real service outage.
- `npm run build` in frontend: passed with 30 modules transformed.
- `MEETSPACE_TEST_MILESTONE=m4 node checks/check-calendar.mjs --read-only`: passed against actual API data; employee isolation, manager records, Riyadh grouping in a Los Angeles browser, themes, language, responsive 390/768/1440 widths, and no booking from calendar cells. Evidence: `evidence/m4/m4_browser_readonly.json`.
- `MEETSPACE_TEST_MILESTONE=m4 node checks/check-calendar-states.mjs`: passed; delayed real reads, no premature empty state, actual empty day, injected employee/admin HTTP 503 feedback, recovery, and zero writes. Evidence: `evidence/m4/m4_ui_state_checks.json`.
- `node checks/check-foundation.mjs`: initially failed because its old immediate room-count assertion ran before asynchronous inventory loading. Moved its existing readiness wait before counting; rerun passed navigation separation, draft retention across theme/language, employee draft separation, responsive layouts and zero page errors. This is a QA synchronization correction, not a product behavior change.
- Live `verify_live_m3.main('docs/evidence/m4/m4_live_results.json','docs/evidence/m4/m4_booking_regression.json')`: passed real English/Arabic booking, missing fields/retention, selection, natural explicit consent, Firestore read-back, duplicate confirmation, stale-offer conflict, valid alternatives, no-offer confirmation rejection, past/reversed/overnight rejection, concurrent same-slot transactions, calendar ownership, cancellation/consent/idempotency, released occupancy with adjacent interval preservation, maintenance before commit, maintenance/confirmation race, and manager inventory. The race returned `maintenance`, creating no race booking. Evidence: `evidence/m4/m4_live_results.json`, `evidence/m4/m4_booking_regression.json`.
- Full `MEETSPACE_TEST_MILESTONE=m4 node checks/check-calendar.mjs`: passed actual browser maintenance enable/restore, dismissing cancellation without a write, confirming cancellation with persisted status and calendar update, employee/manager calendars, Riyadh display across UTC midnight, themes/languages and responsive widths. Only the newly identified M4 browser fixture was canceled. Evidence: `evidence/m4/m4_browser_results.json`.
- Fresh-process `audit_m3.main('m4')`: passed. All **11 preexisting bookings and all preexisting documents** retain their recorded hashes. All active intervals match confirmed bookings, canceled bookings have no occupied interval, and no confirmed same-room overlaps exist. M01's original available state was restored. Evidence: `evidence/m4/m4_persistence_audit.json`.
- Restarted the local backend, then `python -m backend.checks.check_m4_final` passed actual HTTP health/rooms/employees/admin-bookings reads: Ollama and Firestore healthy, all 17 persisted IDs/statuses matched the audit. Also checked preserved prompt hashes, ignored/untracked credential files and all empty human-measurement result cells. Evidence: `evidence/m4/m4_final_checks.json`. Owned local QA servers were stopped after checks.

## Firestore outcome and disclosed new fixtures

Final inventory: **10 rooms, 3 employees, 17 bookings (13 confirmed, 4 canceled), 15 room_days**. No record was deleted, no existing booking canceled, no maintenance reset on startup and no seed initialization run. Six new fictional test bookings were left in place; two of those new records were canceled by the authorized cancellation tests.

| New booking ID | Purpose / owner / room | Riyadh slot | Final status |
|---|---|---|---|
| `5f53b72435f24ec289a7a1a021b07c32` | Typical / sara / T02 | 8 Dec 2026, 10:00–12:00 | confirmed |
| `4bf774563b814f099e24ba21536e3d1f` | Messy / noura / T02 | 9 Dec 2026, 10:00–12:00 | confirmed |
| `ced618dea87442bab525dc0c897c8041` | Concurrent winner / sara / T02 | 11 Dec 2026, 10:00–11:00 | confirmed |
| `3b49223395184ddeb58f8254bdd0c9fa` | API cancellation / fahad / M01 | 11 Jan 2027, 00:30–01:30 | canceled |
| `a8bad8fd84544449960f2414a18a7145` | Adjacent interval / noura / M01 | 11 Jan 2027, 01:30–02:30 | confirmed |
| `707cdeed308145e8bf0b87d153c4f68a` | Browser cancellation / sara / M02 | 11 Jan 2027, 14:00–15:00 | canceled |

The reused verification runner retains historical “M3” wording in some fixture labels/console output; these IDs were newly created during this M4 run and are disclosed in the M4 evidence files. The first two bookings use actual natural confirmation; concurrency and cancellation setup use the approved server service. No user-facing manual booking form or extra API was added.

## Security and review gate

Verified root `.env` and the backend service-account JSON are ignored and untracked by Git. Credential contents were not displayed, added to frontend or uploaded. Firestore project remains `smart-room-booking-agent`. No commit, push, public deployment or external messages were sent.

M4 verification/refinement is ready for owner review. Human productivity observations remain pending owner execution, as explicitly requested; they do not block this technical milestone. **Stop at M4 for approval; no final acceptance, presentation or next milestone is inferred.**

## Subsequent explicitly authorized speed follow-up

After the owner tried the application and requested further speed improvements,
the current implementation changed to one real Qwen extraction call per ordinary
message, with optional acknowledgment in the same result and server-grounded
response details. The earlier tables above remain historical M4 evidence.
Fresh measured means: Typical 18.75 → 10.08s, two-turn Messy 28.38 → 20.44s,
Edge 21.44 → 10.94s (two trials each). No human productivity result is inferred.
All benchmark database snapshots were unchanged. The full change rationale,
rejected required-wording experiment, limitations and evidence paths are in the
owner-authorized follow-up section of `Prompt_Engineering_Log.md`.
