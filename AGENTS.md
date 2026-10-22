# MeetSpace — Coding Agent Operating Instructions

**Status:** v1.0 — draft for the project owner's approval; **do not start implementation on the basis of this file alone**.  
**Project:** MeetSpace | SDAIA Academy AI Productivity Bootcamp | Local MVP  
**Purpose:** Give Claude Code, Codex, or another coding agent a bounded implementation contract. The owner makes all scope and product decisions.

## 1. Project Overview

Build a small **AI-powered room-booking web application**, not an enterprise platform. A demo employee selects a fictitious identity, requests a single room booking in Arabic or English through an AI conversation, reviews eligible rooms or alternatives, explicitly confirms an offer, and can view/cancel their bookings. A separate demo manager experience displays all bookings and changes room status between available and maintenance. Use **10 fictitious training/meeting rooms** and persist real bookings and maintenance states in Firestore.

**RICE operating brief:**
- **R — Role:** Act as a careful senior full-stack implementer, not an autonomous product manager.
- **I — Instructions:** Implement only approved requirements, validate actual behavior, and work milestone by milestone.
- **C — Context:** This is a time-limited educational MVP used to demonstrate prompt engineering, responsible delegation, verification, and measured productivity.
- **E — Expected Result:** A working, locally run app faithful to the approved documents and design, with reproducible checks, an accurate change log, and no unapproved additions.

## 2. Authoritative Project References

**Read the complete files before planning or editing code:**
1. `MeetSpace_BRD.md` — **approved simplified v1.0, 22 Oct 2026**: functional requirements, business rules, exclusions, acceptance. Do **not** use the older, larger BRD.
2. `MeetSpace_SPEC.md` — **approved v1.0**: implementation decisions, data contracts, workflow, APIs and validation. Includes **SPEC-01: single-local-day bookings only**. Its earlier internal “pending approval” header is superseded by the owner's explicit subsequent approval.
3. `MeetSpace_A_Redesign.html` — approved **Concept A / Modern Minimal (redesigned)** interaction and visual reference, contained in `MeetSpace_A_Redesign_Preview.zip` if not extracted.
4. Approved UI screenshots, when present, for Chat Light, Calendar Light/Dark, Admin Dark, and Mobile.

The files may be in the repository root or organized under `docs/` and `design/`. Locate and verify the **actual approved versions**; do not guess missing contents. **Conflict precedence:** BRD for behavior/scope → SPEC for technical decisions → approved redesigned UI for presentation and navigation → this AGENTS.md for workflow. Report any genuine conflict and stop for owner approval rather than silently choosing.

**Documented design refinements, not new business functionality:**
- “My Bookings” is displayed as a **calendar with selectable day details** instead of a plain list. Selecting a day and cancelling one's own booking are still the BRD's existing view/cancel operations; **no booking by clicking a calendar cell**.
- The manager has **visually and navigationally separate screens**; switching demo roles does not provide authentication. Employees must never see manager navigation within their employee menu.
- Manager bookings use a calendar rather than a list. This is a display choice only: no external calendar integration, scheduling system, or additional booking rules.

## 3. Approved Tech Stack

| Layer | Required choice | Boundary |
|---|---|---|
| Frontend | React + Vite | Local browser UI; communicate with FastAPI |
| Backend | Python + FastAPI | All validation, Firestore access, business actions |
| Model | Qwen2 7B on local Ollama | Intent extraction and conversational responses |
| AI integration | Ollama Chat API + structured JSON extraction | Validate parsed output on server; never execute arbitrary LLM instructions |
| Persistent data | Firebase Firestore (server-side Admin SDK) | Real bookings, room maintenance and mock seed data |
| Runtime | Local web application | Firestore requires internet; no public hosting |

Keep dependencies minimal. **Do not add** LangGraph, smolagents, Docker, external-model APIs, a second database, enterprise authentication, or public deployment without a demonstrated need and owner approval. Prefer a simple React component tree and a single local FastAPI process.

## 4. Project Structure

Use the SPEC's proposed responsibilities as the base; small organizational differences require only a brief explanation, not a new architecture:

- `frontend/src/App.jsx` — employee selection, demo role separation, navigation and top-level UI state.
- `frontend/src/api.js` — central application HTTP client with clear response/error handling; no direct Firestore calls.
- `frontend/src/components/ChatPanel.jsx` — bilingual conversation, room offers and explicit confirmation.
- `frontend/src/components/MyBookings.jsx` — employee calendar, selected-day details and cancellation.
- `frontend/src/components/AdminPanel.jsx` — separate manager calendar, booking details and maintenance controls.
- Small shared components/styles as needed for calendar, room cards, layout, language, theme and responsiveness. Avoid a large component library solely for the MVP.
- `backend/main.py`, `routes.py` — FastAPI bootstrap and HTTP contracts.
- `backend/agent.py` — Ollama requests, validated structured extraction, grounded natural-language output.
- `backend/sessions.py` — temporary session and one active pending offer.
- `backend/booking_service.py` — deterministic booking rules, atomic confirmation/cancellation, conflict and maintenance checks.
- `backend/firestore_store.py` — Firestore queries/transactions and safe one-time seed initialization.
- `backend/prompts/booking_agent.md` — **editable agent prompt, separate from Python code**; a key deliverable for later RICE prompt improvement.
- `docs/` — approved BRD/SPEC and minimal change/test records; `.env.example` — configuration **names only**, no credentials.

## 5. Coding Standards

- Keep the solution readable, modular and small. Write brief comments for non-obvious booking/concurrency decisions, not exhaustive boilerplate.
- Keep AI orchestration, HTTP handlers, validation, Firestore operations and UI state separate. Use explicit request/response schemas and server-side validation for LLM JSON and API inputs.
- Never trust model output as database truth. Do not silently coerce ambiguous dates, times, capacities, room choices or confirmations.
- Use clear bilingual labels and messages; handle RTL Arabic and LTR English (including mixed text, numbers and dates) correctly.
- Implement loading, empty, success and error feedback without falsely reporting success. Preserve conversation content when changing light/dark theme or language.
- Avoid unnecessary new endpoints, abstractions, services, dependencies and generated scaffolding. Do not copy the prototype's business logic into production.

## 6. AI Agent Instructions

- Store the behavioral prompt in `backend/prompts/booking_agent.md`; version prompt edits so the owner can compare before/after performance.
- From natural Arabic/English messages, extract intent and structured fields: room type, local date, start/end times, attendee count, selected room, and confirmation/cancellation intent when relevant.
- Validate all extracted JSON in Python. If missing, inconsistent or ambiguous, ask only for needed information, retaining previously confirmed fields from the current session.
- Use a `session_id` bound to the selected fictitious `employee_id`. Keep transient draft fields, limited message context, displayed offers and **one identifiable `pending_offer`** in Backend memory. Switching employees must separate drafts; changing material details invalidates the old offer. Persistent chat history is **not** required.
- Use server-owned functions (not model-executed database tools) to find rooms, suggest valid alternatives, confirm bookings, list/cancel own bookings, and fetch manager data/maintenance.
- Replies should be natural, contextual and in the user's language, grounded in actual backend results. No fabricated availability, booking ID, room, or confirmation.
- Natural explicit confirmation, e.g. **«أؤكد الحجز»**, **«نعم، احجز»** or “I confirm the booking,” works only when a **single valid pending offer** belongs to that employee and session. A button, if shown, must follow exactly the same backend safeguards. No valid offer or no unequivocal assent → **no booking**.

## 7. Booking Business Rules

All enforcement occurs in FastAPI and is rechecked at transaction time:

1. **Single booking**, not recurring, batched or partial; room type, date, start/end time, and positive attendee count are required.
2. Use **Asia/Riyadh** as the local booking calendar; store timestamps in UTC. `start_at` must be **strictly later than current time** when committed.
3. `end_at > start_at`, and local start/end dates must be **the same calendar day**. Reject overnight or multi-day offers; ask for corrected times, never assume next-day end.
4. Room must exist, be appropriate for the request, fit **attendees ≤ capacity**, and be **available**, not in maintenance. If suggesting a different room type, state the difference; never describe an undersized room as suitable.
5. Confirmed bookings conflict when **new.start < existing.end AND new.end > existing.start**; touching boundaries do not conflict. Cancelled bookings do not block time.
6. Initial search is provisional. **Only after explicit confirmation**, re-read the room/maintenance status and daily occupancy in a Firestore transaction; atomically persist the booking and its active interval. Use the SPEC's `room_days/{room_id}_{YYYYMMDD}` coordination document and read-before-write transaction sequence to prevent concurrent double booking.
7. Handle duplicate confirmations/retries idempotently using a server-controlled stable confirmation/offer key so the **same approved offer cannot create two bookings**.
8. Cancel only a booking owned by the selected demo employee; atomically mark it `canceled` and remove its occupied interval. Repeated cancellation must be harmless.
9. Switching a room to `maintenance` blocks **new** bookings but **never automatically cancels prior bookings**. Re-enabling it restores eligibility subject to conflicts.
10. Announce success **only after verified Firestore commit**. On uncertain network outcome, check persisted state before suggesting a retry; never claim a failed/unknown write succeeded.

## 8. UI/UX Design Rules

- Treat `MeetSpace_A_Redesign.html` and its screenshots as a **visual/interaction reference**, not production code or source of business truth.
- Follow Concept A Redesigned: generous whitespace, clean typography, soft rounded cards, plum/mint accents, RTL/LTR-aware layout, desktop-first and usable mobile widths.
- **Light:** background `#F7F7F5`, deep plum `#5B2453`, mint `#67C9C5`. **Dark:** navy `#101827`, indigo `#24263E`, turquoise `#5D9EAA`, mauve `#8B5D78`. Maintain visual hierarchy and contrast in both themes with a working toggle.
- **Employee navigation only:** AI Booking Chat and My Bookings Calendar. Choose employee from the approved demo list; show room cards and confirmation within chat. Selecting a date in My Bookings shows that employee's booking details and permitted cancellation. “New booking” may **navigate to chat only**, never open a separate booking form.
- **Manager navigation:** a distinct experience with calendar of **all** employees' bookings, selected-day details, room inventory and available/maintenance switch; no manager link among employee menu items. Demo role switching is clearly not secure login.
- The HTML preview uses **hardcoded scenario flows and browser `localStorage` for fake bookings**. **Replace these completely** with Ollama/Backend/Firestore behavior. Existing example chips, if retained for demonstration, may only fill/send example text through the same real chat workflow; never bypass validation.
- A few read-only overview counts visible in the manager mockup are presentation-only; **do not build reports or analytics features**. No external calendars, notification actions, settings system or unrelated navigation.

## 9. Database & Security Rules

- Seed **exactly ten fictional rooms** and a small set of fictional employees; use `employees`, `rooms`, `bookings`, and the internal daily `room_days` coordination records from SPEC.
- Initialize demo data idempotently. **Never wipe bookings, reset maintenance, or overwrite real demo state on startup.**
- All Firestore reads/writes go through the Python backend, using server-side credentials. **Never commit service-account JSON, tokens, secrets or actual `.env` files**; never expose them in React, screenshots or logs.
- Demo employee/manager switching is **not authentication**; do not claim access controls are secure. Keep the API bound to local development and do not publish it on the public internet.
- Check ownership on employee cancellation even in the demo. Handle Firestore or Ollama unavailability gracefully, with no simulated database success or secret-leaking stack traces.

## 10. Development Milestones

**Do not begin any milestone until the owner explicitly authorizes building. Work on one milestone at a time; after each, report changed files, working behavior, test evidence, known issues and the next proposed step, then pause for approval.**

1. **Foundation:** local React/Vite and FastAPI shells; minimal dependencies/config; connectivity checks to Ollama and Firestore; safe seed data; approved theme/role/navigation skeleton. **Stop for review.**
2. **Core Booking:** editable agent prompt, parsed/validated extraction, temporary conversation state, room search/alternatives, pending-offer confirmation, atomic persistence. **Stop for review.**
3. **Employee & Manager:** actual employee calendar/cancellation, manager calendar and maintenance switching; fully connect UI to backend. **Stop for review.**
4. **Verification & Refinement:** repeatable checks, real bilingual chat validation, fixes for observed issues, light/dark and responsive refinement; log before/after changes. **Stop for final acceptance.**

Do not scaffold all milestones in one pass or claim future tasks were completed.

## 11. Testing & Verification

**Three primary evaluation scenarios, with real state assertions:**
- **Typical:** complete booking request → available appropriate room → explicit confirmation → one persisted booking shown on employee calendar.
- **Messy:** missing attendance and/or end time → ask only for missing data, retain known values → no write until valid offer and confirmation.
- **Edge:** preexisting same-room time conflict → no conflicting write → clear valid alternatives, or explain no availability.

**Supporting readiness checks (not additional measured evaluation scenarios):** past times; end ≤ start; crossing midnight; capacity shortfall; maintenance before/after confirmation; concurrent same-slot confirmations; duplicate submit/retry; cancellation frees interval; ownership separation; persistence across app restart; Firestore/Ollama outage; Arabic/English and RTL/LTR; responsive UI and theme toggle; role navigation separation. Inspect actual Firestore records for booking assertions, not chat text alone.

For the course, perform **at least two actual measured comparisons** of traditional email + Excel versus MeetSpace, recording active time, elapsed time when relevant, correctness, and errors/corrections. **Never invent measurements or pass rates.** Keep prompt versions, test inputs and changes so improvements are reproducible.

## 12. Change Control & Approval Gates

**Stop and ask the owner before** adding functionality, changing any BRD rule, altering an approved technology, adding a significant dependency, materially redesigning the UI, exposing/hosting the app publicly, or resolving a real inconsistency among the approved sources.

Small code corrections that preserve approved behavior may be made within an authorized milestone, with a concise change note and corresponding verification. For defects or prompt changes, record **observed behavior → precise change/prompt → observed outcome**; do not infer success without testing.

If prerequisite files, API credentials, Ollama model, or Firestore access are missing, report the blocker and the minimal setup needed. Do **not** invent a substitute production data source or silently build fake successful booking behavior.

## 13. Definition of Done

The MVP is done **only when the owner approves the result** and there is evidence that:

- The local React/FastAPI app runs with Qwen2 7B/Ollama and Firestore, using fictitious data and no exposed secrets.
- Chat genuinely interprets Arabic/English, retains needed details, presents suitable real-time options/alternatives and honors a uniquely pending explicit confirmation.
- Booking writes and cancellation are persisted and reflected in availability; conflicts, invalid timing, insufficient capacity and maintenance are rejected on the backend, including at confirmation.
- Employee and manager experiences match the approved redesigned Concept A, with distinct navigation, functioning calendars, Light/Dark and responsive RTL/LTR.
- Typical/Messy/Edge and supporting readiness checks are executed with documented actual results; no fabricated metrics.
- Changed files, prompt iterations and approvals are recorded. The owner has explicitly accepted the completed milestone(s) and MVP.

**Final guardrail:** AGENTS.md is an instruction contract only. **Creating or approving this file does not authorize writing application code, designing additional pages, or beginning development.**
