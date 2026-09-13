# Astra medium pilot: accepted pairs

## Scope and selection

The pilot reran `Q4P6` and `Q7P1`, the highest-ranked shortlist pairs whose
existing paper had an accepted status. Their shortlist scores were 3150 and
2200. The earlier pilot instead used the highest-ranked pairs overall,
`Q4P10` and `Q3P9`.

This was fresh discovery from the source pair, not a review or continuation
of the previously accepted paper. Agents did not receive that paper as a
seed connexion. The scope was research followed by a readable note, without
paper authoring or paper review. Consequently, `DRAFT` below is a research
outcome, not a new paper acceptance.

All researcher, consolidator, verifier and editor calls used `gpt-6-astra`
with `medium` reasoning, ChatGPT Pro authentication and no fast-tier override.
The experiment used copied engine code, prompts and sources in this directory.
The historical research baseline for these pairs used `gpt-5.6-sol`, so this
is not a controlled Astra-versus-Opus-5 comparison.

## Observed usage

| Measure | Result |
| --- | ---: |
| Weekly allowance remaining before | 97% |
| Weekly allowance remaining after | 94% |
| Observed change | 3 percentage points |
| Elapsed time, including final accounting | 23 min 22 sec |
| Completed Codex sessions | 13 |
| Input tokens | 11,435,009 |
| Cached input tokens, included above | 10,119,552 |
| Uncached input tokens | 1,315,457 |
| Output tokens | 90,456 |
| Reasoning output tokens, included above | 18,690 |

The before/after readings share the same weekly reset. They are whole-number,
account-wide measurements: rounding, this conversation and concurrent account
activity prevent exact attribution of the difference to the child agents.
They measure subscription allowance, not a dollar invoice. Receipt prices of
zero are unpriced placeholders, not a measured zero cost.

Across the earlier highest-ranked-pair pilot and this accepted-pair pilot,
the observed allowance moved from 99% to 94% remaining. Different research
paths and repair loops make this a pilot observation, not a fixed per-pair rate.

| Pair | Sessions | Input tokens | Cached input | Output tokens |
| --- | ---: | ---: | ---: | ---: |
| Q4P6 | 6 | 5,332,650 | 4,682,752 | 32,143 |
| Q7P1 | 7 | 6,102,359 | 5,436,800 | 58,313 |

All sessions exited successfully. Measurement records are in
[usage-before.json](usage-before.json), [usage-after.json](usage-after.json)
and the per-call metadata and event streams under `telemetry/`.

## Outcomes and quality comparison

| Pair | Historical research | Historical paper | Astra research | Readable note |
| --- | --- | --- | --- | --- |
| Q4P6 | DRAFT, round 2 | Accepted | PAUSE, round 1 | Done |
| Q7P1 | DRAFT, round 2 | Accepted | DRAFT, round 1 | Done |

### Q4P6: useful audit, different direction

The earlier result constructed a conditional label-free identification bridge:
overlapping observers of the same latent comparison identify reliabilities,
then a connected Bradley--Terry comparison graph identifies contribution
rankings. Its accepted paper explicitly left truthful-data bootstrapping,
finite-sample robustness and dynamic participation unresolved.

Astra pursued participation accounting instead. It derived the boundary
transfers left when potential-based shaping increments are omitted during
absence, supplied an exact conditional re-entry example and settlement, and
separated repeated judgments of fixed evidence from genuinely fresh evidence.
The readable note carefully distinguishes synthetic calculations from an
observed exploit in P.

The verifier paused this direction because the reward mask and a feasible
evidence-withholding action were not established for P, while the generic
mathematics specializes known results. This does not refute the earlier
identification theorem. The new account is useful for an implementation audit,
but it did not produce a stronger publication candidate than the old paper.

Read [Astra's note](threads/Q4P6/edited/note.pdf), its
[research account](threads/Q4P6/Q4P6.tex), or the
[verifier decision](threads/Q4P6/Q4P6.verdict.json).

### Q7P1: substantially richer conditional result

The earlier accepted paper proved a uniform error bound between true CVaR and
an expected empirical-smoothed surrogate. Welfare, allocation and participation
bounds followed, but implementing the surrogate through Q's mechanism and
handling the feasible-set mismatch remained conditional or unresolved.

Astra's record adds substantive material:

- A direct incompatibility between Q's strict matrix certificate and its
  implementation equality, plus an explicit participation counterexample.
- An opponent-only payment correction preserving best responses and restoring
  equilibrium participation and budget balance under implementation assumptions.
- A weighted monotonicity argument giving unique implemented allocations without
  requiring unique prices, under an explicit additional curvature condition.
- An asymmetric surrogate-error interval. Under convexity and centered
  smoothing, its oscillation gives welfare loss at most the sum of the error
  widths, rather than the earlier bound of twice that sum. The analogous
  participation bound also improves, and unilateral regret is quantified.
- Inward-shifted query points that preserve the original decision set and its
  zero outside option, with explicit additional approximation error.
- A replacement nested proximal-point learner for the fixed surrogate, instead
  of claiming that P's estimator directly validates Q's original update rule.

The verifier supported this conditional package as `DRAFT`. The readable note
explains the counterexample and repairs, with references to the longer peer
proofs. It is a stronger technical starting point than the old research note,
but not an independently certified theorem or an accepted replacement paper.
Full prior-work comparison, efficient oracle complexity, joint capacity
feasibility of exploratory queries and exact population-risk learning remain
open. The original accepted bound is not invalidated by these additions.

Read [Astra's note](threads/Q7P1/edited/note.pdf), its
[research account](threads/Q7P1/Q7P1.tex), or the
[verifier decision](threads/Q7P1/Q7P1.verdict.json).

## Preservation and limitations

Before/after hashes confirm that all 94 protected original files are unchanged;
see [originals-verification.json](originals-verification.json). Existing accepted
papers were not modified or replaced.

The pipeline reports successful PDF builds for the readable notes. Its external
arXiv checks encountered HTTP 429 for Q4P6 and HTTP 503 for Q7P1, so bibliographic
metadata was not fully verified. See [outcomes.json](outcomes.json).

This comparison is a qualitative reading of the generated accounts and the
historical notes and papers, not an independent reproduction of every proof.
Research directions, historical prompt versions and sampling differ. The sample
supports trying Astra on substantive follow-up work, not a general model ranking.
