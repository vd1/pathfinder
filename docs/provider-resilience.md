# Provider capacity resilience

This release improves failure evidence, bounded retry timing and coordinated admission. It does not
prevent provider overload, change scientific gates, change models or approve unknown-usage estimates.
Existing frozen deployments remain unchanged until an operator upgrades them while idle.

## Evidence and classification

Native CLI calls write append-only, fsynced stdout events and stderr under
`transport-evidence/<call-id>.events.jsonl` and `<call-id>.stderr.log`, with private file permissions.
The active-call record points to both files. Finished receipts bind their paths, sizes and SHA-256
hashes. Concurrent stderr draining prevents a full stderr pipe from blocking the CLI. Reader or
journal failures retain unresolved active-call evidence rather than claiming a complete result.
Lifecycle inventory treats these files as retained evidence. Storage grows with actual output;
this release does not silently truncate or delete the journals. They can contain research and tool
output and should receive the same access controls as campaign evidence.

Receipts preserve structured provider codes, status, request IDs and retry hints when the CLI emits
them. Only provider error events supply these fields; model messages and tool output do not.
Known structured billing/quota codes take precedence over generic capacity or HTTP-rate wording.
Model overload and rate limiting retain the existing retryable `rate` class for compatibility,
with their original structured details alongside it. Missing provider fields remain unknown.

Usage samples retain their origin and semantics. Cumulative snapshots are not summed, and resets
or repeated samples are preserved. A completed terminal usage report can populate the normal
accounting counters. On failure, raw reported usage and samples are retained as partial evidence,
but incomplete accounting counters remain null. No inference of zero usage is made. Older receipts
are not rewritten. Unknown usage continues to block strict shared-budget admission unless the
existing exact reservation mechanism has a separately approved record.

## Retry policy

Default transient delay ceilings are 60 and 120 seconds, with equal jitter: the sampled delay is
between half the ceiling and the ceiling. Explicit `transient_backoff_seconds` lists remain
supported, including the older 60/300 schedule. `retry_jitter_fraction` defaults to 0.5 and can range
from 0 to 1. A value of zero gives the configured deterministic delay, useful for controlled tests.

A valid provider Retry-After value, in seconds or HTTP-date form, is a minimum delay. The longest
exposed hint is retained. Invalid hints are not invented. Retry events record the chosen delay and
attempt index. Known quota/authentication failures are not retried as overload; model routing does
not change. Existing restrictions on timeout retries and residual peer allowances remain in place.

`retry_episode_seconds` optionally bounds the entire retry episode, including shared cooldown
waiting. Its default covers the configured maximum attempt count at the request timeout plus the
configured delay ceilings. A delay beyond the remaining episode causes a recorded deferral without
an early retry. Each new attempt is capped to the remaining episode, rounded up to whole seconds;
process teardown and ordinary scheduler overhead can extend elapsed time beyond that granularity.
Operator stops remain polled during waits. No unlimited retry mode is introduced.

## Shared cooldown and recovery probes

Campaigns naming the same account share cooldown state keyed by backend, account and actual routed
model. State lives under the configured Pathfinder accounts directory, in `provider-cooldowns`.
Different accounts and models do not inherit each other's model-scoped cooldown. Deployments without
an explicit account retain the existing campaign/parent cooldown behavior.

Expiry updates use a cross-process lock and retain the later expiry. Once cooldown expires, a single
recovery probe holds a separate OS lock through admission and the call. Other callers wait without
holding seats or the group budget lock. Admission rechecks cooldown state after acquiring resources;
if another in-flight call has renewed it, those resources are released before waiting again.
Already running calls are not interrupted.

Only a successful probe clears the generation it tested. An older success cannot erase a newer
failure. A failed or killed probe releases its lock, allowing a later bounded probe; failures renew
cooldown through normal receipt handling. Health snapshots show shared model scopes, remaining
waits and pending recovery probes. This is not a FIFO scheduler or an account-wide quota override.

Mixed engine versions do not all honour the new shared state. Upgrade participating controllers only
at idle boundaries; do not replace running engines or reinterpret prior receipts.

## Scope and validation

The exact single-receipt unknown-usage reservation remains separate. No future automatic reservation
policy is enabled. Provider availability and unreported usage cannot be guaranteed by this release.

Tests cover structured-code precedence, message isolation, Retry-After dates and seconds, jitter and
episode limits, partial/reset counters, durable journals, large stderr output, independent-process
expiry updates, exclusive probes, stale successes, operator stops and accounting compatibility.

See [official OpenAI guidance](https://developers.openai.com/api/docs/guides/deployment-checklist).
API error codes are used only when actually exposed; this does not retrospectively diagnose Atlas's
plain-text capacity failure as a particular HTTP response.
