# Follow-up: capacity resilience

Atlas reports successful recovery and research continuing in round 2. No live patch is requested.
The existing approval covers only receipt 398ff543ec6e4b6bab6ae24d278f4d54.

## Diagnosis boundary

The capacity message is consistent with transient model congestion. It does not establish an exact
service cause or scope. The receipt contains no structured HTTP status or provider error code, and
provides no evidence of quota exhaustion. The call was partially served before the failure.

[Official OpenAI guidance](https://developers.openai.com/api/docs/guides/deployment-checklist)
distinguishes model overload, rapid request growth and quota or billing failures. These API codes
must not be retrospectively assigned to a Codex receipt that did not expose them.

## Engine backlog, in priority order

1. Preserve structured failure metadata and usage completeness. Retain error code/type, status,
   request ID and retry hints when exposed, with their origin. Prefer structured quota/spend codes
   over generic rate classification. Missing fields remain unknown. Journal incremental events and
   counters durably; distinguish cumulative snapshots from deltas and partial usage from a complete
   total. Drain stderr concurrently. Session persistence can help only when counters are emitted.
2. Add bounded exponential retry delays with jitter and honour Retry-After as a minimum. Parse
   seconds and HTTP dates; defer or stop when a required wait exceeds the remaining allowance.
   Record delay selection and attempt number. Preserve stop responsiveness and model choice.
   Quota and authentication failures must not enter the overload retry loop.
3. Coordinate cooldowns across explicitly shared backend/account/model scopes. Use locked maximum
   expiry updates and a single probe after repeated failures. Broaden scope only on supporting
   evidence. Do not cancel active calls. Avoid holding seats or the group budget lock through long
   cooldown waits; recheck admission atomically before dispatch. Shared-seat FIFO fairness remains
   a separate issue.
4. Consider a separately authorised future missing-usage policy. Bind models, stages, failure
   evidence, reservation amounts and rationale, maximum exception count, cumulative reserve ceiling
   and expiry before launch. Each use must retain immutable receipt bindings and separate measured
   and reserved totals within unchanged aggregate caps. Unknown usage outside that policy stops.
   The current single-receipt approval is not authority for this future policy.

## Required validation before deployment

Use recorded-event tests for overload versus quota precedence, missing final events, failures after
partial work, cumulative/reset usage counters and process termination. Test concurrent controllers,
Retry-After parsing, jitter, deadlines, stop responsiveness, cooldown scope and probe ownership.
Verify that recovery preserves completed research and historical receipts. Do not claim a partial
counter is total usage or that an estimated reservation certifies actual aggregate compliance.

These changes can reduce synchronized retries and recovery disruption. They cannot guarantee
provider availability. No implementation or live deployment change accompanies this backlog entry.
