# Released-account significance ratings and bounded continuations

Runtime: `566ba59aba14875b74d38ae59c87fb50ecf8b8b7`.
Frozen runtime: `/private/tmp/pathfinder-ratings-566ba59`.
Archive: `/private/tmp/pathfinder-ratings-566ba59.tar.gz`.
Archive SHA256: `38575e2f2f2c151e6db058908ca6bec12215d7777dae8fd952779dc0387952e9`.

Use this separate immutable runtime only when the target campaign ownership is idle.
Do not replace any engine files under active calls. A released, idle batch1 account
has its own campaign root; it can be rated while other batch1 roots continue.
Batch2 shares a campaign root: wait for its controller to finish before rating there.
Record the reviewed engine change with the global `--accept-change` option when applying.
All ancestor paper-pool, ITERATE and tail fixes remain included.

## Canonical rating path

From the frozen runtime, use the existing Python environment:

```text
python -m pathfinder.cli --root CAMPAIGN rate-release PAIR --edited
python -m pathfinder.cli --root CAMPAIGN --accept-change "Add authorised release significance ratings" rate-release PAIR --edited --apply
```

The first command prepares without calls. The second dispatches exactly one
`gpt-6.1-sol` and one `gpt-6-astra` rating, both at medium effort, without tools or
search, each in its own scope. The note rubric is copied verbatim from Nobel's
`paper_significance.py` / `strong_arm.prompt('note', ...)`. Its anchor is 5 for a
solid specialist contribution. The model sees only the released source and rubric,
plus the standard restricted source-pool instruction, never the other rating.

The dated manifest, source, PDF and bibliography hashes are verified first.
`threads/PAIR/significance/` stores the immutable binding, source, prompt, separate
dispatch records, raw responses, receipt snapshots and results, plus a combined result.
Ratings do not alter scientific status, PCE, presentation or release gates.
One fixed slot per account prevents a later source change from silently granting
another pair of calls. Rate only the final release. Twenty accounts mean at most
forty served rating attempts. There is no repeat count, reset, fallback or automatic retry.

Repeat the same apply command to resume. Saved raw responses are parsed without
another call, including after a crash before result installation. A dispatch with no
saved raw response is an uncertain outcome and stops for receipt inspection;
it is never silently repeated. Invalid output or provider failure is retained and
requires explicit operator resolution, not another paid attempt. A proved pre-admission
refusal can be retried after its cause is fixed. Existing campaign/parent stops,
provider pauses, budget guards, shared seats, ownership and run provenance apply.

## Bounded existing-engine continuations

`linewidth-action.json` and `Q053-P072-context.json` bind the original Gaussian
script and results. Both widths are full widths at half maximum. The script doubles
the positive half-maximum crossing; the JSON keys explicitly name FWHM. The permitted
change labels the existing numbers and preserves all synthetic-model caveats.
Existing `17673d9` supports this one-cycle continuation without restart or upgrade.

`q053-p011-action.json` contains the exact final editor feedback and a one-pass,
one-fact-check grant using the existing scientific evidence projection. It separates
main narrative from appendix and explicitly retains unresolved validation-set access,
candidate selection and replication criteria. No new evidence or computation is
requested. Existing `a2492b7` supports it. Each new allowance remains an explicit
operator decision; do not renew automatically or interrupt the active batch2 sequence.

## Validation

- 20 focused rating tests passed in the working tree and the verified frozen runtime.
- 45 rating/import/presentation/PCE recovery regression tests passed before the final
  two focused rating cases were added; both added cases then passed.
- Three actual dated releases passed read-only manifest/source/PDF binding checks.
- Copied linewidth deployment on frozen `17673d9`: two stub calls reached CLEARED;
  prior stages and science were preserved, with only state/active pointer advancing.
- Copied editorial continuation on frozen `a2492b7`: five stub role results reached
  accepted; all previous rounds and science preserved.
- No live calls, source-script execution, deployment writes or engine replacement.

## Subsequent cutoff clarification

After the FWHM clarification, the next recorded finding asks whether fixed excitation
cutoffs are total or per-mode. `Q053-P072-cutoff-context.json` binds the exact retained
Emmy derivation, which explicitly counts sectors through K total excitations and
separately distinguishes local cutoffs. `cutoff-action.json` supplies a fresh bounded
clarification grant on existing 17673d9. A copied current-state test reached CLEARED
with two stub calls and preserved previous history. No new scientific scope is chosen.
