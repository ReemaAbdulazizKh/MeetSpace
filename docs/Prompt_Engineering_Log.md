# Milestone 4 — Prompt Engineering log

## Controlled sequence

1. Preserve the original v4 prompt byte-for-byte as `archive/prompt_versions/m4_A_baseline.md`; measure before editing production prompt/code.
2. Candidate B: explicit RICE structure, shorter instructions and a partial follow-up example instead of five complete JSON examples. Keep production extraction schema, context, generation parameters and two-call orchestration unchanged.
3. Observed B regression: complete Typical/Edge requests sometimes lost `end_time`; the model asked for a supplied value. One English request was extracted with Arabic language. B is rejected, not deployed. Raw unsuccessful outputs remain in `evidence/m4/optimized_B.json`.
4. Candidate B2: retain RICE and restore three full bilingual JSON examples (complete request, incomplete request, follow-up). Explicitly tie language to user text. This responds to observed extraction errors rather than assuming shorter is better. Keep code unchanged for the comparison.
5. B2 passed all six scenario trials (eight HTTP turns); A/B/B2 production code hashes and fixtures match. B2 is 3,039 characters versus A's 3,848. Post-run language audit found four language errors in B, none in A or B2. The comparison report includes this additional audit without rewriting raw observations.
6. Technical C uses the exact B2 prompt and changes only `agent.natural_reply`: status `missing` returns the existing bilingual, field-specific server question without a redundant RESPOND generation. The extraction call is unchanged, as are all validation and write paths. A dedicated test asserts the question is preserved and no wording call occurs. This is a code effect, distinct from prompt changes.
7. C passed all six trials/eight turns without database changes. Messy calls fell from four to three per two-turn trial; mean time fell from B2 33.48s to C 26.88s. C Edge slightly regressed (20.50s vs 20.45s). Typical still makes two calls; its different timing is not credited to this branch change. See the milestone report for all individual timings and cache limitations.

## Hypotheses and attribution

The baseline prompt contains repeated full JSON keys and five examples. Reducing it may reduce prompt evaluation work, but examples may be essential for this local model; B demonstrates that risk. Draft retention and selection/confirmation remain server responsibilities. The prompt must output only newly stated changes and distinguish missing from ambiguous values.

Two model calls per ordinary turn are a code decision, not a prompt defect. RESPOND generates an optional introductory sentence; authoritative server facts are appended regardless. Baseline actual results discarded six of eight generated introductions under the safety guard. A prompt cannot remove that second HTTP call. Any technical change must therefore be measured as a separate phase after the prompt-only comparison.

Ollama reported `qwen2:7b`, 4096 context, 100% CPU on Intel Core Ultra 7 155H (16 cores, 22 logical processors). Load, prompt evaluation and decoding durations are recorded separately in nanoseconds in raw JSON. CPU inference and cache/loading behavior are plausible contributors to latency; this is an inference, not a controlled hardware comparison. No model replacement, parameter tuning or hardware speedup is claimed.

## Reproduction and limits

Use `python -m backend.checks.benchmark_m4 --label A --prompt docs/archive/prompt_versions/m4_A_baseline.md --trials 2 --output docs/evidence/m4/baseline_A.json` and corresponding B/B2 paths. Historical evidence files must be copied to a new output path when rerunning. Run phases serially with no other model workload. `python -m backend.checks.report_m4` derives `evidence/m4/comparison.json` from completed observed reports.

Exact inputs, fixed Riyadh context, real conflict fixture and all outputs are in each raw report and `evidence/m4/benchmark_fixtures.json`. Typical and Edge are one-turn provisional searches; Messy is two turns. These latency comparisons do not include human selection, confirmation or calendar inspection. Full booking behavior is checked separately by live regression.

Each phase performs an excluded minimal model warm-up; it does not guarantee identical prefix caches. Phase order is A → B → B2, not randomized. Two repetitions per scenario are descriptive evidence, not statistical proof. The first A Typical turn is substantially slower than its second despite warm-up; show individual results and do not present the mean difference as a guaranteed speedup.

`model_calls[].started_riyadh` in A/B/B2/C records is the fixed extraction context time because the harness freezes the booking clock. It is not a per-call wall-clock start. Actual phase start/finish, `perf_counter` elapsed times and Ollama durations are independently recorded. No times have been estimated or backfilled.

Final results and the selected prompt are recorded in `Milestone_4.md`; the raw files retain rejected candidates and any regressions. Human email/Excel results remain empty in the separate measurement template.

## Owner-authorized speed follow-up — 22 October 2026

Observed problem: keeping Qwen resident removed reload delay, but ordinary room search still made two sequential model calls. Owner explicitly requested further optimization after observing slow replies. A fresh keep-alive baseline was measured before changing orchestration. All measurements below are automated server latency, separate from human productivity observations.

Precise change: retain the real Qwen extraction and all deterministic validation, but remove the separate RESPOND generation. Extraction may include a short optional acknowledgment in the same JSON; it is never used as a source of availability, success or database facts. The bilingual response is composed from the actual backend result; optional wording is safety-filtered and used only for options/offers. Missing questions, errors and verified receipts remain server-owned. Reset acknowledgment at the beginning of every turn to prevent stale wording. No natural-language confirmation shortcut, model replacement, booking rule, Firestore write path, context truncation or UI change was introduced. `keep_alive=-1` remains enabled.

The optional-acknowledgment candidate passed six trials/eight turns. In these trials Qwen omitted the optional acknowledgment, so the displayed replies were entirely server-grounded; no improvement in generated phrasing is claimed. Genuine semantic extraction still used Qwen on every measured turn. Current production module/prompt hashes exactly match this measured candidate.

Rejected follow-up: making acknowledgment required and explicitly requesting compact JSON did not help. Typical/Messy means regressed to 26.02s/32.02s; an English request generated an Arabic acknowledgment containing a date and a success-like phrase, which was discarded. This version was not deployed. Raw measurements and its prompt remain preserved; the selected version restored the original B2 prompt byte-for-byte.

| Scenario | Fresh keep-alive baseline mean seconds | Selected one-call mean seconds | Required acknowledgment, rejected | Calls baseline → selected |
|---|---:|---:|---:|---|
| Typical | 18.75 | 10.08 | 26.02 | 2 → 1 |
| Messy, two turns | 28.38 | 20.44 | 32.02 | 3 → 2 |
| Edge | 21.44 | 10.94 | 18.09 | 2 → 1 |

Two repeats each, identical inputs/fixtures. Fields, recommendations and extracted language passed both repetitions in all phases. All three phases left their complete Firestore snapshot unchanged. Raw individual times, call outputs, token counts and load/prompt/decode metrics: `evidence/m4/pre_speed_keepalive.json`, `evidence/m4/post_speed_single_call.json`, `evidence/m4/post_speed_ack.json`; derived results: `evidence/m4/speed_comparison.json`. Warm-up is excluded; these sequential small-sample measurements do not establish a guaranteed speedup. Required-ack first Typical includes a large new-prefix evaluation cost; that is not concealed. Selected search response is still about ten seconds on this CPU, not instantaneous.

Before-source copies are in `m4/speed_before/`. Booking/Firestore services were not edited. Isolated regression: 32 tests passed, including no second wording generation, rejection of unverified success/availability claims, material corrections, explicit assent and transaction safety. Additional real-model selection/consent/correction checks are recorded separately in `evidence/m4/speed_readonly_regression.json`; their guard forbids any booking commit. Positive consent is extracted only, never submitted as an actual booking in this read-only follow-up.

Reproduce analysis with `backend.checks.report_m4.main(['pre_speed_keepalive','post_speed_single_call','post_speed_ack'],'docs/evidence/m4/speed_comparison.json')`. Use new output paths when repeating measurements. Historical M4 performance evidence and human CSV observations were not overwritten.

Deployment validation: all ten real-model follow-up checks passed (English and
Arabic selection, positive consent extraction, negative consent extraction,
material correction invalidating the old offer, and confirmation with no remaining
offer). Each used exactly one model call; the complete Firestore snapshot remained
unchanged. Positive confirmation was never committed by these checks. Final 32
isolated tests passed. Restarted the local backend with the selected source;
actual `/api/health` reported backend/Ollama/Firestore OK, `ollama ps` showed
Forever, and the real Chrome foundation/navigation/theme/responsive check passed.
The local application was left running for the owner. Backend restart clears
temporary conversations only; refresh the page and start a fresh conversation.

### Terminal and duplicate-call diagnosis requested by owner

Inspected production call sites and active listeners: one local listener each on
8000 (FastAPI), 5173 (Vite) and 11434 (Ollama). Production extraction calls
`structured` once; `natural_reply` makes no HTTP request. Health uses `/api/tags`,
not generation. Standalone benchmark/verification entry points are not invoked
by normal application startup. The browser HTTP client contains no automatic
retry, and its send handler uses an immediate ref guard against double submit.

Actual direct terminal extraction, without FastAPI/browser/Firestore: **13.92s,
one model call**. Ollama reported loading 0.03s, prompt evaluation 5.55s and
decoding 8.19s. Evidence: `evidence/m4/terminal_call_probe.json`.
Actual headless Chrome provisional-search submission: **12.56s, exactly one POST
to `/api/chat`**, status options, no selection/confirmation/booking write.
Evidence: `evidence/m4/browser_call_probe.json`. These sequential probes have different
cache/scheduling conditions; their durations must not be subtracted to estimate
database time. No duplicate generation was found in the tested path; no claim
is made about all possible external Ollama clients. No production code changed
for this diagnosis and human measurement cells were not populated.

### Owner-approved direct room-card selection

Observed issue: clicking a known room card generated a text message and invoked
Qwen unnecessarily. Added `action:select_room` and `room_id` to the existing chat
contract, requiring an existing employee-bound session. The card passes its ID
directly; typed text still uses Qwen. The service accepts only displayed rooms,
invalidates superseded offers, preserves uncertain-commit recovery, re-reads
eligibility and creates an in-memory pending offer. It never commits a booking;
the existing explicit confirmation and atomic transaction path is unchanged.
Shared offer formatting keeps typed and card selection consistent. Loading text
now describes processing without falsely implying every action calls Qwen.

Real Firestore/API checks: Arabic M03 selection 1.54s, English 2.05s, zero model
calls each, complete database snapshot unchanged. Evidence:
`evidence/m4/structured_selection_checks.json`. Actual Chrome card click: M03 offer visible
in 1.73s, structured selection payload, no confirmation request or booking created.
Evidence: `evidence/m4/structured_selection_browser.json`. These are individual observed
times, not a promised response time or human productivity measurements. Guard
tests cover unlisted/stale rooms, employee/session separation, malformed action
contracts, uncertain commits, failed reads and no model/write at selection.
Human CSV results remain untouched. Backend was restarted to apply the change;
temporary conversations require a fresh page/session, persisted bookings remain.
