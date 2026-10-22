# Milestone 1 — Foundation review

## Firebase setup follow-up — 22 October 2026

The previous Firebase blocker below is resolved. At the owner's explicit request, the existing service-account JSON under `backend/` was validated privately against `smart-room-booking-agent`. The root `.env`, which `backend/config.py` loads, now points to its absolute local path and sets the approved project and local service settings. No credential contents were printed. Both files were verified with `git check-ignore` and `git ls-files`: ignored, not tracked, and still present locally. An exact JSON-file rule was added to `.gitignore`; no GitHub upload, staging or commit occurred.

Actual authenticated Firestore checks succeeded. First seed created 13 documents: exactly 10 rooms and 3 fictional employees. All expected IDs were read back from Firestore. Second seed created 0 documents; full in-memory before/after comparisons confirmed no changes on repeat and preservation of any preexisting records. `bookings` and `room_days` both contain 0 records and were unchanged. No data was deleted or replaced.

FastAPI TestClient exercised actual dependency calls: `/api/health` returned HTTP 200 with overall/backend/Ollama/Firestore `ok`; `/api/rooms` returned HTTP 200 with 10 records; `/api/employees` returned HTTP 200 with 3 records. Non-secret persistence results are recorded in `docs/evidence/m1/firebase_m1_verification.json`. Existing Python-version and TestClient deprecation warnings remain. No UI, booking workflow or Milestone 2 implementation was changed.

The remaining sections record the original foundation review and its then-observed blocker for historical accuracy.

Date: 22 October 2026 (Asia/Riyadh). Authorization: owner's attached Prompt 06, “Begin Milestone 1 now.” No later milestone started. Original approved BRD, SPEC, AGENTS and HTML remain unchanged. The SPEC header's old pending status is superseded by the owner's instruction, as documented in AGENTS.

## Delivered files and behavior

- `frontend/package.json`, `package-lock.json`, `index.html`, `vite.config.js`: minimal React/Vite application and loopback development proxy.
- `frontend/src/App.jsx`, `api.js`, `main.jsx`: separate employee/manager navigation, demo employee choice, unsent drafts isolated by employee, language/theme and dependency status. Drafts survive language, theme and navigation changes in memory.
- `frontend/src/components/{ChatPanel,Calendar,MyBookings,AdminPanel,Icon}.jsx`: approved Concept A layout, calendar month/day controls, visual room card/confirmation shell, manager inventory and disabled future actions.
- `frontend/src/styles.css`: approved prototype CSS reused for visual fidelity, with small status/accessibility/layout additions. Only CSS, SVG icon definitions and fictional reference inventory were transferred; simulated booking logic was not copied.
- `frontend/src/designData.js`: explicitly labelled preview fixtures from the approved design. Firestore API failures return 503; the UI labels reference fixtures as unconnected previews. No fake booking records or database-success fallback.
- `backend/{main,routes,config,connectivity,firestore_store,seed_data}.py`, `__init__.py`, `requirements.txt`: FastAPI, loopback CORS, typed response contracts, Ollama installed-model check, real Firestore read check, inventory reads, explicit manual additive seed transaction.
- `.gitignore`, `.env.example`, `README.md`: local configuration names, secret exclusions and execution instructions. No actual `.env` or credentials created.
- `backend/tests/test_foundation.py`, `frontend/checks/check-foundation.mjs`: repeatable bounded checks. Browser tool is optional, installed without saving it as an application dependency.

No booking/search/chat orchestration, cancellation or maintenance writes are implemented. No prompt/session/booking-service placeholders were created for future milestones. The small additional `config`, `connectivity`, `seed_data` and shared calendar files separate foundation responsibilities without adding a service or architecture.

## Actual verification

| Check | Observed result |
|---|---|
| `npm.cmd run build` | PASS: Vite 7.3.7, 31 modules; production bundle generated locally, not deployed. Initial sandbox path-read failure resolved by approved execution. |
| FastAPI startup via uvicorn | PASS: application startup complete, bound to `127.0.0.1:8000`. |
| Live `GET /api/health` | Backend `ok`; overall `degraded`. |
| `ollama list` and live health model check | PASS: local `qwen2:7b` installed and API reachable. No generation test or download performed. |
| Firestore real server read | BLOCKED: unavailable. No `.env` or credential environment variable; ADC check raised `DefaultCredentialsError`. |
| Manual seed command | Failed gracefully due to unavailable credentials; no successful seed or database persistence is claimed. |
| `python -m unittest backend.tests.test_foundation -v` | PASS: 2 isolated tests. Outage returns 503 without private exception text; booking confirmation route absent. Seed test preserves existing maintenance/bookings, creates only missing records, reads before writes, and creates zero records on repeat. Uses test doubles, not live Firestore evidence. |
| Python compileall | PASS for initial foundation source; final updated modules subsequently imported/executed successfully by unittest and health check. |
| `node checks/check-foundation.mjs` using installed Chrome, real local UI/API | PASS: employee/admin navigation separation, employee draft isolation, disabled send and maintenance, calendar next/today/day selection, New booking returns to chat, light/dark switching, Arabic RTL and English LTR. No page JavaScript errors. |
| Responsive browser checks | PASS: no horizontal document overflow at 390, 768 and 1440 px for employee chat and manager screens. |
| Screenshot inspection | Reviewed dark English chat and light Arabic mobile manager screenshots. Generated images in ignored `frontend/test-results/`. Pixel-perfect equivalence is not claimed. |
| Credential pattern scan | Zero private-key / Firebase API-key patterns in application source and built frontend. No service-account file or actual `.env` created. This is a bounded scan, not a security audit. |
| Dependency install audit | npm reported zero vulnerabilities at installation. |

Observed issue → change → outcome: missing database configuration → explicit degraded health, 503 inventory and labelled preview notices → browser displayed unavailable Firestore without fake success. Potential repeated Firebase initialization failure/concurrent inventory calls → serialized named-app reuse → final backend tests and live health executed successfully; live authenticated retry remains untested.

Known environment notes: Python 3.10.9 works for the checks but Google libraries warn it is unsupported for future updates; use Python 3.11+ for ongoing work. TestClient also emits an upstream httpx deprecation warning; tests pass. No extra runtime framework was added to suppress warnings. Git status was unavailable because inherited Git configuration pointed at an inaccessible parent path; no Git commit or staging was attempted.

## Remaining setup and review gate

Configure credentials locally as described in README, restart FastAPI, run the seed command twice and inspect the ten rooms/three employees in the actual Firestore project. Verify the second seed creates zero records and existing maintenance/bookings stay unchanged. Authenticated connectivity and live seed idempotency remain unverified until then.

Re-run isolated backend checks with `.\.venv\Scripts\python.exe -m unittest backend.tests.test_foundation -v`. For browser checks, start backend/frontend, run `npm.cmd install --no-save --package-lock=false playwright` inside `frontend`, then `node checks/check-foundation.mjs` (requires existing Chrome; no browser download).

Milestone 1 implementation is ready for owner review, with Firebase readiness blocked. It is not marked fully accepted. Stop here. Proposed Milestone 2, only after explicit approval: editable prompt, validated extraction, temporary sessions, real room search/alternatives and atomic pending-offer confirmation. No booking evaluation or productivity measurements have been invented or performed in this foundation milestone.
