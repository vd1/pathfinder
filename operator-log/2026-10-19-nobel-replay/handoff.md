# Classic verifier replay and presentation sentence relocation

Runtime: `ea46411cb4fe262c50f7933daf69f7344a78dd6c`.
Frozen runtime: `/private/tmp/pathfinder-verifier-archive`.
Archive: `/private/tmp/pathfinder-verifier-ea46411.tar.gz`.
The archive checksum is recorded in `archive.sha256` beside this handoff.
All earlier paper-pool, ITERATE, release and tail fixes are ancestors.

## Verifier-only replay

The old `reopen` command does not support classic campaigns with no research scheme,
and its existing grants are not verifier-only. Do not change the scheme or hand-edit
research status. The new `verify-replay` command validates an exact independent copy
of a terminal classic thread against its original before preparing anything.

The deployment operator owns creating a new campaign root for each follow-up. Copy
the original campaign configuration, required corpus/configuration/prompt/style and
extension resources, and the complete target thread with ordinary independent copies,
not hardlinks or symlinks. Keep the shared absolute source-pool path. Copy the existing
receipt/run history for charge and provenance continuity. Do not copy active-call files,
runner locks or live process metadata; preserve these in the untouched original.
Retain any stop marker and resolve it through the ordinary authorised stop workflow.
Keep the shortlist limited to the intended copied pair before later research dispatch.
The campaign JSON must remain exactly equal to the original at replay preparation.

Pilot 7 uses its final round-2 snapshot of Q242-P465. Pilot 8 uses its round-1 PAUSE
snapshot of that pair. Both actual snapshots were tested. The operator supplies the
intended verifier prompt in the follow-up's prompt overlay before preparation. Prompt
hashes are frozen at preparation. No exploratory criterion has been invented here.

From the separate frozen runtime, with the existing Python environment:

```text
python -m pathfinder.cli --root FOLLOWUP verify-replay PAIR --origin ORIGINAL --reason "Approved bounded verifier reassessment"
python -m pathfinder.cli --root FOLLOWUP --accept-change "Classic verifier-only follow-up on new runtime" verify-replay PAIR --apply
```

Preparation makes no model calls. It archives the previous status, note, ledger,
verdicts and pending response, and moves old editorial/presentation/rating products
into `threads/PAIR/reassessment/prior/` in the follow-up only. The original is read-only.
The current note and ledger remain the snapshot being judged. Original verdict history
is retained and the new verdict is appended with a reassessment marker.

Apply runs only the verifier under normal routing, admission, budget, provider and
stop guards, restricted to OpenAI. Raw output, prompt, dispatch, verdict, transactional
installation record and result are saved. Malformed output or uncertain dispatch stops
for inspection without another automatic response. Saved responses and installation
resume without another call. This path does not guarantee DRAFT or paper acceptance.

DRAFT or PAUSE becomes the terminal follow-up outcome. An ITERATE or REVISE within
the original allowance prepares the ordinary next peer or consolidation stage but
stops before running it. Exhausted original limits remain PAUSE-ON-ITERATE or
PAUSE-ON-REVISE. Inspect the new verdict, then authorise ordinary `research --pairs PAIR`
or `paper PAIR` as appropriate. The engine does not grant extra research allowance.

The runtime change is separate from the exploratory-prompt treatment. Record both
in the experiment provenance; do not describe this comparison as prompt-only across
runtime versions. Originals and their frozen engines remain intact.

## Presentation relocation

The reported sentence occurs verbatim before and after the correction, with changed
position and wrapping. The guard now pairs identical moved sentences across changed
blocks by occurrence count. Genuine deletion, wording changes and introduced content
still face the existing checks; the subsequent fresh checker remains required.
The exact retained refused correction now produces zero guard findings.

For the paused accepted paper, the existing canonical recovery is
`present Q462-P471 --restart` on the follow-up runtime, after campaign ownership is idle.
The supported restart archives the previous presentation attempt. Do not edit the
refused stage, bypass the checker or replace engine files while any call is active.
Record this tail-only runtime correction separately from the research treatment.

## Validation

- 32 frozen verifier, movement and presentation tests passed on c06900a.
- The final archive addition passed 12 focused tests on frozen ea46411.
- Both actual Nobel snapshots passed one-verifier stub tests on independent copies:
  44 prior Pilot 7 thread files and 30 prior Pilot 8 thread files remained unchanged.
- The actual relocation candidate passed the corrected guard without source editing.
- Interrupted verdict installation resumes without a second call; changed copies,
  changed prompts and using the original as destination are refused.
- No live model calls, original-campaign writes or active-engine replacement by maintainer.
