# Repeat versus reinjection: first readout

Prepared 2026-09-27, Europe/Paris. This is an operational readout and an
unblinded first inspection, not the protocol's final claim-level evaluation.
All 28 pipelines finished at 17:50:55 Paris time. The runner reports complete,
with no budget-censored arm.

The subsequent [Recursive Science note](../notes/recursive-science.tex)
contains the completed unblinded claim comparison, including all pilot pairs
and the earlier Q7 follow-ups. It supersedes the preliminary novelty judgments
below, especially the apparent novelty of the repeat arm's payment repair.

## Design and interpretation

The frozen pilot compares 14 fresh repeats of original pairs with 14 pairings
of original Q papers and five previously accepted final papers. Q frequencies
match across arms. Both arms use the same frozen engine, prompts and model
configuration. Only one generation of reinjection is included.

The question is whether reinjection adds useful supported results beyond
another repeat, not whether repeated runs have identical verdicts. Neither
internal acceptance nor a new application name establishes novelty.

Protocol: [frozen plan](2026-09-25-1623-repeat-versus-reinjection.md).
Experiment evidence lives under
`experiments/2026-09-25-repeat-injection/`, abbreviated E below.

## Recorded scientific endpoints

Every research thread has reached a terminal verdict and completed its edit.
All DRAFT paper pipelines are ACCEPTED. All 28 edits and ten papers report
successful builds.

| Endpoint | Repeat | Reinjection |
|---|---:|---:|
| Scheduled pairs | 14 | 14 |
| DRAFT, with internally accepted paper | 7 | 3 |
| PAUSE | 7 | 11 |
| Accepted fraction | 50.0% | 21.4% |

Repeat accepted pairs: Q4P10, Q7P1, Q3P3, Q4P9, Q7P7, Q3P6, Q1P6.
Reinjection accepted pairs: Q4P4 (S4), Q1P3 (S3), Q1P1 (S1).
In reinjection, P1 through P5 denote seeds S1 through S5, not original P papers.

The acceptance difference is descriptive. Pairs were purposively selected;
shared Q papers and seeds make outcomes dependent. Acceptance thresholds also
vary with the argument found. No causal effect or saturation estimate follows.

## Recorded workload

These totals sum the existing arm receipts, including recorded failed calls.
They exclude supervision and the historical cost of producing the five seeds.

| Receipt measure | Repeat | Reinjection |
|---|---:|---:|
| Calls | 119 | 105 |
| Completed / error | 117 / 2 | 105 / 0 |
| Input tokens, including cached tokens | 132,502,988 | 87,473,953 |
| Cached input tokens | 124,017,536 | 81,530,624 |
| Output tokens | 1,025,200 | 833,137 |
| API-equivalent recorded cost | USD 52.03 | USD 36.52 |
| Summed call duration | 7.60 hours | 5.74 hours |

The combined recorded equivalent is USD 88.55, not an additional subscription
invoice. One failed repeat call lacks usage and cost, so these are recorded
totals, not a complete metering guarantee. The other failed receipt retains
reported usage. Do not silently recode either failure using the new engine.
Summed call duration includes concurrent peers and is not elapsed wall time.
Elapsed time from staging to completion was 49.24 hours, including the long
interruption; the final resumed run lasted 2.03 hours. Neither duration is a
clean measure of scientific efficiency.

Supervision is separate overhead. Through the closing audit, 115 audit logs
contained 114 completed-turn usage records: 24,120,478 input tokens, including
18,601,984 cached tokens, and 244,038 output tokens. This is a
logged-usage subtotal, not a supervisor invoice or complete overhead estimate;
failed calls and separate authentication probes may not expose usage.

## Reinjection candidates worth auditing

These classifications are provisional comparisons to the named seed, not
novelty findings against all historical ledgers or the published literature.

### Q1P1: correcting the peer-ranking seed

S1 identifies rankings under shared comparisons and conditionally independent
peer errors. Its limitations say that correlated errors destroy the agreement
factorisation. The new paper supplies a common-flip counterexample: that
factorisation can survive even when an endpoint ranking reverses. It then
separates graphs that preserve ordinal information from cycles that identify
the missing numerical scale.

This looks like correction plus extension, rather than a renamed application.
The four-vertex example checks numerically: true endpoint difference 1 becomes
approximately -0.26458 after the stated transform. This limited check is not
an independent audit of the full graph and finite-sample results.

The journey matters: the peers first resolve the seed's internal Q/P labels,
then move from a prediction interface to a failure example and graph conditions.
The result remains conditional on a constant positive common-flip mean; it
does not establish truthful reporting or decision performance.

Evidence: `E/reinjection/threads/Q1P1/ledger.jsonl`, entries 4, 8, 11, 16, 26,
27; its `paper/paper.tex`; `E/seed-archive/S1/paper.tex`, limitations section.

### Q4P4: finite-batch risk changes implementability

S4 distinguishes true CVaR from expected empirical CVaR in a resource tax game.
The new pair uses a different mechanism-design Q. The peers explicitly reject
transferring the seed's tax conclusions and instead construct a two-signal
example: for every finite batch size, surrogate utilities pass the
state-independent obedience test while true conditional utilities fail it.

This is a candidate new connection built from inherited ingredients. Its
opposite reward inequalities give the contradiction directly. The instance
depends on batch size; this is not one fixed instance failing at every size.
State-dependent rewards and ex-ante plan CVaR are outside the result.

Evidence: `E/reinjection/threads/Q4P4/ledger.jsonl`, entries 1, 6, 9 through 16;
its `paper/paper.tex`; `E/seed-archive/S4/paper.tex`.

### Q1P3: a sharper auction baseline

S3 already supplies the gross-surplus ceiling of 7.5 and the token-cost
accounting. The new paper adds a conditional zero-token fixed-price comparator
and a rationing example where an arbitrarily small price change permits a
1.25 welfare loss. That is an extension candidate, not a new welfare ceiling.

The peers turn a broad prediction-cost analogy into a baseline and a boundary
on scalar price-error guarantees. Full execution and a stipulated response
model remain essential: neither construction is an observed auction result.

Evidence: `E/reinjection/threads/Q1P3/ledger.jsonl`, entries 10, 15, 19, 24;
its `paper/paper.tex`; `E/seed-archive/S3/paper.tex`.

## What the repeat arm prevents us from concluding

Repeats continue to generate different arguments. Q4P9 now has an all-board
contract/path feasibility witness; Q3P6 has a fixed-value information
counterexample; Q7P1 and Q7P7 derive a related transfer correction in different
applications. Their substantive novelty still needs the full baseline audit.

Do not count the shared Q7 correction twice. Likewise, auction information
limits in repeat Q3P6 and reinjection Q3P5 overlap as a family, even though
their verdicts differ. The new Q3P3 paper also reuses welfare-accounting
ingredients already present in the S3 seed family.

PAUSE threads must remain in the evaluation: reinjection Q3P2 records a
supported trade-count bound but judges it Q-only; Q7P2 records mechanism
corrections but no established joint result. Excluding them would confuse
scientific content with the pipeline's paper-writing decision.

## Integrity and remaining work

The running experiment has not been migrated to the newly patched engine.
All 720 protected files from the 23 pipelines completed before resumption were
rechecked and unchanged. No additional generation, new pair, or higher budget
has been introduced.

The final preflight passes the frozen-input and engine hashes. The final
outcomes were checked against all 28 terminal research/edit records and the
ten accepted paper records. Reference validation is not complete: all 28
editors report an arXiv HTTP 406 lookup failure, and reinjected local papers
also produce missing-public-identifier warnings. Successful compilation and
internal acceptance do not resolve these source checks.

Astra's closing audit 25 independently records all 28 pipelines complete,
successful runner exit, no active runner or calls, and all 720 protected
artifacts unchanged. The supervision session has also ended as complete.

The next evaluation must inventory claims in both arms, including PAUSE,
compare them with the full original and September 23 ledgers and papers,
deduplicate related claims, and separate genuine joint results from Q-only or
seed-only arguments. The planned label-hidden support/usefulness assessment
has not been performed; this readout cannot substitute for it.

Do not launch a second generation on acceptance counts alone. First adjudicate
the common-flip and CVaR-cycle candidates, audit their closest repeat and
historical counterparts, and resolve source/reference warnings. A focused
continuation may be justified even if reinjection does not win on paper count.
