# PCE continuation and dated release handoff

Runtime commit: `9a2df43011e7ed8cc45b1313e07ffe76d7ba66cd`.
Frozen runtime: `/private/tmp/pathfinder-pce-9a2df43`.
Archive: `/private/tmp/pathfinder-pce-9a2df43.tar.gz`.
Archive SHA-256:
`273b7c3aeaf5c2dff310d9b92b17a72980743007eed67e72544ac3b4ee2574ca`.
Scope: targeted PCE, presentation and release patch validation. The full
cross-deployment release gate has not been run; no new engine tag is claimed.
This commit includes the paper-pool fix `4c764f9` and the ITERATE readiness
fix `56518ebf252b48d68b184228ce76f14d78a78f21`.

## Julien-2 recovery

The ten batch-2 records were copied to a temporary campaign and exercised
with stubbed role replies. All ten completed the simulated PCE path. Their
312 historical PCE files and scientific status bytes remained unchanged.
The two owner-accepted notes remained the selected baselines; other retained
rounds continued from their last draft. The single-editor note entered PCE
through the same explicit grant. These results validate recovery mechanics,
not the scientific or editorial quality of a live model's future replies.
No live deployment files, pauses, charges or calls were changed.

Before dispatch, the deployment operator should:

1. Pin and verify the frozen engine, retaining the v1.6.0 engine and old
   records. Use the deployment's supported upgrade mechanism.
2. Set the five `edit/pce-*` routes to the existing OpenAI subscription model,
   currently `gpt-6.1-sol`, on `codex`. Check actor-specific overrides.
   For the account tail, also set `present/editor`, `present/corrector`,
   `present_lookup/lookup`, `present_check/checker`,
   `present_check/checker-1`, `present_check/checker-2` and `review/claims`.
   Remove `refusal_fallback`; this path stops on safety refusal.
3. Set `edit_scheme` to `pce` for future ordinary edits. Explicit recovery
   grants also work for existing records whose setting was `single`.
4. Keep provider pauses and stop markers intact. A pause or budget refusal
   remains a blocker; do not bypass it.
5. Grant three new passes and three new fact checks per batch-2 account,
   recording the owner's request as the reason. This bounds the work to at
   most fifteen PCE role calls per account. Existing charges and allowances
   remain historical; global budget guards still apply.

For each explicit pair, using the pinned engine entry point:

```sh
pathfinder --root CAMPAIGN reconcile PAIR \
  --pce-grant completion-20261019 \
  --passes 3 --fact-checks 3 \
  --reason 'Owner requested completion of independent PCE gates' \
  --repair-only
pathfinder --root CAMPAIGN \
  --accept-change 'Pin PCE recovery engine and OpenAI editorial routes' \
  reconcile PAIR --apply
pathfinder --root CAMPAIGN present PAIR --edited
pathfinder --root CAMPAIGN release PAIR --edited
```

The first command records a grant without calls. Repeating its ID and
parameters does not allocate a second round. Reconciliation resumes the
active grant; an exhausted round requires a new explicit grant. Do not
remove or reset `result.json` or move historical rounds aside.

The grant retains the previous edit record, result, baseline, routes and
historical hashes in `edited/pce-rounds/<grant>/grant.json`. Its immutable
inputs are separately hashed. Scientific ledger entries are projected into
the reviewers' supplement without previous review decisions; full research
and review records remain available internally and historically.

Only an installed note with completed PCE gates can enter `present --edited`.
Presentation and export records live under
`edited/publication/<content-hash>`. They do not create a scientific
paper-stage acceptance or change a PAUSE verdict into DRAFT. Presentation
prompts preserve that distinction. Confirmed scientific problems return to
the operator without commissioning research or automatically amending a
paper. An explicit presentation restart archives the prior attempt.

Astra should report progress incrementally: grant prepared, PCE result,
presentation clearance or blocker, and validated dated release. Preserve
the ten batch-1 model-editor acceptances. Their already accepted accounts
can use the account tail after its preflight succeeds.

## Nobel and release dating

Nobel can integrate this same frozen runtime into its fresh Pilot 7 arms.
Keep Pilot 6 comparison settings, the paper-pool configuration and the
ITERATE fix. This handoff does not authorise a launch or model call.
The existing paper path continues to use `present PAIR` and `release PAIR`.

The operator can specify `release PAIR --timestamp 20261019T142530Z`.
Without that option, the engine captures UTC once when creating the attempt.
The authoritative source and PDF are:

- `release/20261019T142530Z/paper-20261019T142530Z.tex`
- `release/20261019T142530Z/paper-20261019T142530Z.pdf`

The visible date is fixed as `Released 2026-10-19 14:25:30 UTC`.
The adjacent manifest records artifact hashes, input hash, clearance,
timestamp and engine provenance. `references.bib` is in the same directory.
Internal provenance is retained under `release-records`; it is not part of
the exported artifact set. Canonical `release/paper.tex`, `paper.pdf` and
`references.bib` are compatibility copies, updated after validation.

Failed attempts keep their timestamp for retry. Successful retries verify
hashes and reuse the validated files without recompilation. An explicit new
timestamp creates another dated release. Collisions or changed authoritative
files are refused. Recompilation preserves the source's printed date but
does not inherit the recorded PDF hash; publish a new timestamp for a newly
built PDF. Old dated directories are retained.

Nobel's configured acknowledgement is compatible with this path:

> The outputs were generated by Pathfinder (https://github.com/vd1/pathfinder)
> with no human input after the choice of sources.

## Validation evidence

The copied-record check is in
`/private/tmp/pathfinder-pce-9a2df43-julien-copy.log` and
`/private/tmp/julien-recovery-validation.json`.
Frozen regression results are recorded in
`/private/tmp/pathfinder-pce-9a2df43-tests.log` and the matching JUnit XML.
The final frozen artifact passed all 27 recovery and release tests in
70.63 seconds. The broader run on parent commit `5b6f59a` passed 182 tests
and found one error-message compatibility failure. The final commit changes
only that refusal message; the failing case and all release tests passed
on the final frozen artifact. Broader evidence remains in
`/private/tmp/pathfinder-pce-5b6f59a-tests.log` and its JUnit XML.
The ten-record simulation was repeated successfully on the final artifact.
Frozen verification matched the commit with no added, missing or changed
runtime files. No live model calls or campaign mutations were made.
