# MeetSpace — AI-Powered Room Booking Assistant

## 🌐 جرّبي التطبيق — Live Demo

### [افتحي MeetSpace](https://meetspace-fucc.onrender.com/)

**رابط التطبيق:** https://meetspace-fucc.onrender.com/

React/Vite + FastAPI room-booking assistant using Qwen3.8 27B through Groq in the hosted configuration, with server-side validation and Firebase Firestore persistence. Local Ollama remains an optional provider. This is an educational demo with fictional data; role switching is not individual authentication.

## وثائق المشروع — Project Documents

- [BRD — متطلبات الأعمال](docs/MeetSpace_BRD.md)
- [SPEC — المواصفات التقنية](docs/MeetSpace_SPEC.md)
- [AGENTS.md — تعليمات وكيل التطوير](AGENTS.md)
- [تعليمات وكيل الحجز — Booking Agent Prompt](backend/prompts/booking_agent.md)

## Project folders

- backend/: runtime API, agent, booking rules and Firestore access.
- backend/tests/: isolated automated tests.
- frontend/src/: React application; frontend/checks/: browser QA.
- docs/: [document index](docs/README.md), approved references and reports.
- docs/evidence/: original technical results, grouped by milestone.
- docs/archive/: previous prompts and source snapshots.
- docs/m4/productivity_results.csv: human observations, unchanged path; [results](docs/Productivity_Results.md).
- design/: approved visual reference.

## Run locally (PowerShell)

From the project root, with Python 3.11+ recommended and Node 20.19+ or 22.12+:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` locally. It is ignored; never paste secrets into chat or put credentials under `frontend/`.

- `FIREBASE_PROJECT_ID`: `smart-room-booking-agent`.
- `GOOGLE_APPLICATION_CREDENTIALS`: absolute path to your server service-account JSON, kept outside this repository. Obtain it locally through Firebase project settings → Service accounts, or use an existing authorized Application Default Credentials setup. Do not upload or commit the JSON. Ensure the Firestore database exists and the account has access.
- `OLLAMA_BASE_URL`: `http://127.0.0.1:11434` (default).
- `OLLAMA_MODEL`: `qwen2:7b` (installed model verified with `ollama list`; no download performed).
- `FRONTEND_ORIGIN`: `http://127.0.0.1:5173` (default).

Start Ollama if it is not running. Check `ollama list`. Then:

```powershell
.\.venv\Scripts\python.exe -m backend.firestore_store
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The initialization command creates only missing records: ten fictional rooms and three employees matching the approved design. It uses a read-before-write transaction, preserves existing room/employee fields and maintenance, and never creates or changes bookings or room-days. It does not run automatically at startup. Re-running is safe.

In a second terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to the local backend. Keep both services bound to loopback.

## Checks

```powershell
cd frontend
npm.cmd run build
```

Backend API: `http://127.0.0.1:8000/docs`; `GET /api/health` checks Ollama's installed-model list and performs a real Firestore server read. HTTP 200 may report `degraded`; inspect each dependency's status. `GET /api/employees` and `/api/rooms` read Firestore and return 503 on failure, with no mock fallback.

The UI offers Arabic/English, RTL/LTR, light/dark, separate role navigation, employee selection and independent conversations/drafts. Chat sends real requests through `POST /api/chat`, displays actual room cards and a single pending offer, and accepts typed explicit confirmation or the offer's button (`POST /api/bookings/confirm`). A verified persisted booking ID appears in chat. Enter requests directly in the chat input.

Employee calendars now read only the selected demo employee's actual bookings. Select a day for room/date/time/status details. Cancellation requires confirming the dialog; the backend checks ownership and atomically marks the booking canceled and removes only its occupied interval. Repeated cancellation is harmless. The calendar updates after verified persistence. New booking navigates to chat only; date cells never create bookings.

The separate manager calendar displays all employees' bookings and names. The ten real rooms have Available/Maintenance controls. Maintenance persists on the room document, blocks new search/confirmation, and preserves every existing booking. Restore makes a room eligible again subject to capacity and schedule. Use the page's refresh action to reload changes made in another tab; there is no realtime subscription. All calendar grouping and booking time display use Asia/Riyadh, regardless of the browser timezone. No design fixtures or database fallbacks are used.

New API contracts: `GET /api/bookings?employee_id=...`, `POST /api/bookings/{id}/cancel` with `{employee_id, confirmed:true}`, `GET /api/admin/bookings`, and `PATCH /api/admin/rooms/{id}/status` with `{status:"available"|"maintenance"}`. Demo role/employee selection is still not secure authentication. All Firestore operations remain server-side; API errors never show raw exception details.

Edit agent behavior in `backend/prompts/booking_agent.md`. Earlier prompt versions and actual iteration outcomes are kept under `docs/`. JSON extracted by Qwen is validated; server rules reject invalid/ambiguous requests, insufficient capacity, maintenance, conflicts and cross-midnight bookings. All times use Asia/Riyadh and persist in UTC. `tzdata` supplies timezone data on Windows.

Run one FastAPI process only. Sessions and limited chat context are in memory, lost on backend restart; confirmed bookings persist. An expired session returns 409 and the UI asks for a new request. Switching employees clears the previous pending offer server-side. Material edits require a fresh offer. Repeated confirmation uses the same server-owned offer/booking ID. Each transaction reads employee, room, daily coordination and existing room bookings before atomically writing booking + `room_days` interval; success is shown only after a persisted read. Unknown network outcomes retain the same offer key for safe confirmation retry. Do not start a duplicate new request after an uncertain confirmation.

Qwen runs on CPU in this setup and may take tens of seconds per turn; the UI displays processing and disables repeat submission. Model outages/invalid JSON fail closed. Natural introductory wording comes from Qwen when it passes output checks; exact booking data and verified success/error messages remain server-owned.

Owner-authorized speed follow-up: ordinary messages now use one Qwen extraction call, with optional brief wording in that same result; there is no separate RESPOND call. Grounded bilingual questions/options/receipts come from actual server results. Qwen stays resident using `keep_alive=-1` while Ollama runs. Fresh before/after measurements and rejected experiments are in the follow-up section of `docs/Prompt_Engineering_Log.md`. These are separate from human productivity timings. Read-only real-model regression: `python -m backend.checks.verify_speed_readonly` (forbids booking commits).

Room-card selection uses `POST /api/chat` with `action:"select_room"`, `room_id`, existing `session_id`, employee and language (and the normal display message). It bypasses Qwen, accepts only a room previously displayed to that employee/session, rechecks current eligibility and builds a pending review offer. It does not write a booking. Typed room choices still use Qwen; explicit confirmation and transaction safeguards remain unchanged. Read-only live check: `python -m backend.checks.verify_selection_readonly`.

```powershell
.\.venv\Scripts\python.exe -m unittest backend.tests.test_foundation backend.tests.test_booking backend.tests.test_model_contract backend.tests.test_calendar_admin -v
```

See [backend checks](backend/checks/README.md) and [browser checks](frontend/checks/README.md) for optional verification. Some tools create/cancel fictional bookings or temporarily change maintenance; they are not startup commands. Historical checkpoint checks have fixed assumptions and are not general health checks.

Human results are recorded in [Productivity_Results.md](docs/Productivity_Results.md); unmeasured active time, error counts and second repetitions remain blank in the existing CSV. Technical model benchmarks remain separate. Existing reports and raw observations were retained during folder organization.
