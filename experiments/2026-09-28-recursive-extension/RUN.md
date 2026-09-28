# Recursive extension run record

Protocol: `plans/2026-09-28-1322-recursive-extension.md`.
The setup is frozen in `manifest.json`; runtime outcomes are separate.
The engine is the verified copy of commit `01b0f87`, not a modified copy
of the September 25 experiment. Scientific inputs and historical outputs
are not rewritten on resume.

## Commands

From the Pathfinder checkout:

```sh
uv --cache-dir /private/tmp/pathfinder-plan-uv-cache run --no-sync python experiments/2026-09-28-recursive-extension/launch.py preflight
uv --cache-dir /private/tmp/pathfinder-plan-uv-cache run --no-sync python experiments/2026-09-28-recursive-extension/launch.py launch
uv --cache-dir /private/tmp/pathfinder-plan-uv-cache run --no-sync python experiments/2026-09-28-recursive-extension/launch.py status
```

`launch` is one-shot and refuses a second launch record. The authorized
supervisor resume command is the same script's `run` action, never `prepare`
or another fresh scientific replicate. Resume requires process inspection
and an unexpired admission window; no stop marker is cleared automatically.

## Readiness evidence

- Both versioned seed PDFs built successfully; tau/shared-draw assumptions,
  common-reward wording and local-reference locators were checked.
- Selected public sources and attribution boundaries were verified in the
  separate September 28 source audit.
- The selected mathematical witness script passes.
- Source/PDF style gates have no errors. R2 retains 22 long-source-line
  warnings inherited from its parent; they do not affect the PDF. No
  overfull boxes or unresolved-reference warnings were found in the builds.
- The corrigendum, seed pages and updated science note were visually inspected.
- Preflight validates all four identities, immutable files, source ingestion,
  matching questions/prompts, protected parents and the engine freeze.
- Model-free coordinator, admission, provenance and supervision checks:
  63 passed. Experiment-specific admission-window checks: 3 passed.

Unchanged original full-text source copies remain under the repository's
existing `sources/` ignore rule, with their content hashes in the manifest.
They are not new authored artifacts: the broad staged style check initially
flagged their inherited whitespace and formatting. They were removed from
staging, not altered or deleted. Versioned generated seeds and their immediate
local-source packages are tracked. Reconstructing elsewhere also requires
the original September 23 source corpus.

The final staged gate checked 20 artifact files with zero errors and 115
warnings across copied engine prompts, source packages and seed text. These
are source-layout warnings (long lines and prompt heading structure), retained
to preserve the frozen engine and inherited manuscript text. Newly written
protocol and audit notes pass without warnings.

## Launch

Started 28 September at 13:31:57 Europe/Paris. The initial supervisor PID is
49472 and coordinator PID is 49475; these are historical launch identities,
not permanent liveness assertions. The recorded admission deadline is 16:01:57
Europe/Paris. The watch ceiling is approximately 16:31:57 Europe/Paris.
Both first control peers started, and their active-call records were visible
under the aggregate snapshot. Later health must be read from runtime records.

The first five-minute Astra audit returned `continue`: it checked both arms,
found the control peer calls within their deadlines and recent ledger activity,
and reported no failures, stops or need for intervention. The recursive arm
was queued. This verifies the watch is operating, not scientific completion.

Fixes were pushed as `e3d52bb`; the frozen setup was pushed as `eb6b8ca`.
The last ACCEPT review for each selected parent was also checked to bind
to the exact SHA-256 of its archived TeX, not merely to a matching title.

## Scientific assessment

Evaluate claims and ancestry, not acceptance-rate superiority. The comparison
is question-conditioned and unblinded: both arms receive the same starting
question within each block. Costs and terminal verdicts remain descriptive.
New ideas must be separated from the generated seeds' existing claims and
the earlier historical/control record.

## Limits and health

The per-arm API-equivalent admission cap is 50. Aggregate usage is not an
invoice and does not reproduce subscription-credit accounting. Astra audit
usage is recorded separately in supervision logs. New calls stop after
2.5 hours, and the watch lasts three hours. The grace period is not a hard
termination deadline for already-running calls.

`status` reports both child campaigns under `extensions.arms`; the empty
root shortlist is not evidence of completion. Runtime files `launch.json`,
`progress.json`, `outcomes.json`, arm receipts and `supervision/latest-session.json`
are authoritative for what actually ran. The historical pilot is unchanged.
