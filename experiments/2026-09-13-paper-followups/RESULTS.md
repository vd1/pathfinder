# Paper follow-ups and tutoring recommendation

## Q4P6: separate corrected copy

The [corrected paper](threads/Q4P6/paper/paper.pdf) addresses the local
exposition findings from the targeted reassessment. Its central population
identification theorem and proof are unchanged.

- The account of P now distinguishes its claimed statistical convergence from
  the population inversion actually used in this paper.
- Graph coverage is explicitly sufficient, not necessary. A triangle is a
  convenient calibration device, and full edge coverage is stronger than needed
  for identifying scores on a connected spanning subgraph.
- The empirical discussion distinguishes observer-moment checks from P's
  comparator diagnostics. Passing the checks does not establish truthfulness,
  conditional independence, the latent model, or contribution semantics.

The original accepted version remains untouched. This is an exposition-corrected
copy, not a new automated acceptance. Its provenance is recorded in
[corrections.json](threads/Q4P6/paper/corrections.json).

The PDF builds successfully and has 7 pages. Artifact gates report no errors;
the source retains 39 long-line warnings. The opening page was visually inspected.

## Q7P1: paper cycle completed

The [new manuscript](threads/Q7P1/paper/paper.pdf), *Corrected quadratic payments
for a fixed CVaR surrogate*, reached `ACCEPTED` in paper-review round 1 using
Astra medium for authoring and independent review. The input was the earlier
Astra research draft, copied into this experiment, not the historical paper.

The reviewer supports the conditional payment correction, implementation,
economic-error bounds and replacement learner. The author credits the existing
CVaR estimator and generic proximal method, limiting the contribution to the
specific correction and its economic consequences. Internal acceptance is not
external peer review or exhaustive novelty verification.

Minor findings remain recorded in [review.json](threads/Q7P1/paper/review.json):

- Separate notation for messages and batch sizes, and for loss bounds and payoffs;
  explicitly state positive integer batch sizes.
- Define the relevant coefficient blocks used in the certificate obstruction.
- Define the proximal parameter and display the recorded counterexample column.

These findings did not trigger another author round under the existing protocol.
The accepted manuscript is preserved as reviewed rather than silently amended.

The PDF has 9 pages and builds successfully. The author reports passing artifact
gates, no undefined citations or overfull boxes, and visual inspection of all
pages; its opening page was also inspected by the supervising agent. The
pipeline's arXiv metadata lookup timed out. The reviewer considered the author's
recorded bibliographic verification, but that does not turn the failed automated
lookup into a successful check.

## Usage and preservation

| Measure | Result |
| --- | ---: |
| Author/reviewer calls | 2 |
| Elapsed interval between quota snapshots | 10 min 49 sec |
| Weekly allowance remaining | 94% to 93% |
| Input tokens | 1,779,552 |
| Cached input tokens, included above | 1,575,552 |
| Uncached input tokens | 204,000 |
| Output tokens | 16,259 |
| Reasoning output tokens, included above | 1,574 |

Quota readings are rounded and account-wide, including concurrent activity.
They are not a dollar invoice or an exact per-call subscription charge.
[Before](usage-before.json) and [after](usage-after.json) snapshots and raw
telemetry retain the measurement evidence.

All 123 protected original files have unchanged hashes; see
[originals-verification.json](originals-verification.json). No historical paper,
research output, or root pipeline configuration was replaced.

## Suggested tutoring paper

Start with the corrected **Q4P6**, *From Truthful Peer Signals to Contribution
Rankings: A Conditional Interface for Q and P*.

Its central question is concrete: how can noisy observers reveal a ranking
without anyone supplying the correct answers? The conditional result is short
enough to reconstruct, and its limitations lead directly to the distinction
between statistical identification and incentives.

A backwards-learning route would be:

1. Start with the ranking claim in the corrected paper and a small observer example.
2. Derive how shared-item agreements reveal reliability under the stated noise model.
3. Recover pairwise probabilities and connect them to the ranking component of
   [P6, MARS-RA](https://arxiv.org/abs/2607.27967).
4. Ask why observers would report their signals truthfully, leading into the
   incentive questions of [Q4, Mechanism Design for Alignment and Control](https://arxiv.org/abs/2609.01595).
5. Return to the paper and identify the assumptions that prevent a complete
   incentive-compatible implementation, especially the truthful-data bootstrap.

This is a recommendation and learning outline, not a launched tutoring agent.
