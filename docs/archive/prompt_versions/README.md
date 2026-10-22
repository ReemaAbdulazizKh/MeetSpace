# Milestone 2 prompt iterations

The editable current prompt is `backend/prompts/booking_agent.md`. Historical text
is preserved here; no prompt performance or productivity rates are assumed.

| Version | Actual observation | Precise change / observed outcome |
|---|---|---|
| v1 | Read-only English request “I need a training room on 2026-11-17 from 10:00 to 12:00 for 15 people.” yielded `end_time=null`. | No offer/write was allowed. Added explicit instruction to extract both range endpoints and made all extraction schema keys required. |
| v2 | One English probe extracted `12:00`; a subsequent probe still omitted it. | Separated extraction and response prompt sections at runtime, retained failures rather than treating one success as proof. |
| v3 | First live Typical attempt still asked for end time; no booking created. See `docs/m2_live_attempt_01.json`. | Distinguished absent fields (null) from explicit ambiguities (`unclear`), then replaced prose examples with full JSON examples and passed latest user text as the actual user message. |
| v4 | The live Typical request extracted both endpoints; Arabic Messy retained date/type/start and collected only attendance/end time. | Current compact prompt with full bilingual examples. Complete run outcomes and exact inputs are in `docs/m2_live_results.json`; browser outcomes are recorded separately. |

The server remains responsible for validation and consent, regardless of prompt
quality. Invalid JSON or missing/ambiguous data fail closed. Natural wording that
fails output checks is replaced by grounded server feedback. Prompt iteration here
is required M2 development, not a claim that the later M4 evaluation is complete.
