# Repeat versus reinjection: claim baseline and pilot protocol

Prepared 2026-09-25, Europe/Paris. Status: protocol frozen for review;
experiments not launched. This document authorizes no model spending by itself.

## Question and scope

Does one generation of reinjection produce useful, supported claims beyond
what comparable additional research on original inputs produces?

Do not wait for saturation. Measure marginal yield in a repeat control alongside
the reinjection arm. This is a small, purposively selected exploratory pilot,
not an estimate of the universal causal effect of recursion.

Both previous campaigns researched and edited the same 14 pairs. Only DRAFT
outcomes proceeded to paper writing and review. The original campaign used
mixed models; the September 23 rerun used GPT-6-sol. Neither historical outcome
counts nor their effort totals constitute a controlled model comparison.

## Claim inventory before the pilot

This is a comparison of recorded arguments, not a fresh mathematical audit.
Claims below retain their assumptions; internal acceptance is not external
validation. O = original; R = September 23 rerun. Except where specified,
PAUSE does not mean refutation.

| Pair | Original journey and supported endpoint | Rerun journey and endpoint | Reconciliation |
|---|---|---|---|
| Q4P10 | Peer discipline proposal; missing behavioral evidence. PAUSE. | Scoring-transfer limits; missing behavioral evidence. PAUSE. | Shared unresolved empirical bridge. |
| Q3P9 | Horizon and action-interface confounds; experiment needed. PAUSE. | Contract representation confounded with terms and enforcement. PAUSE. | No demonstrated representation effect. |
| Q4P6 | Peer disagreement leads to population identification from shared noisy comparisons; finite-sample claims narrowed. DRAFT. | Potential-shaping cancellation and participation-boundary analysis. PAUSE. | Different branches; R does not refute O's identification result. |
| Q3P10 | Gross versus computation-adjusted auction welfare; live fee experiment demanded. PAUSE. | Exact gross benchmark, scheduler and withdrawal issues, avoided-call incentives. DRAFT. | Analytical refinement, not observed behavioral improvement; acceptance threshold differs. |
| Q7P1 | Uniform surrogate-error bounds; corrected welfare and participation claims; mechanism feasibility conditional. DRAFT. | Explicit curvature and surrogate-risk counterexamples plus conditional bounds. DRAFT. | Recurrent core distinction with complementary arguments; not two independent discoveries. |
| Q4P3 | Peer-error model and reviewer-evidence mismatch; discrimination experiment needed. PAUSE. | Sequential copying obstructs peer-scoring transfer. PAUSE. | Different objections, same unsupported transfer. |
| Q1P1 | Sharper P-side surrogate bound, but weak substantive use of Q. PAUSE. | Advice/oracle-cost advantage not established. PAUSE. | Useful analysis without demonstrated joint contribution. |
| Q3P3 | Institutional-control analogy; reviewer experiment remains missing. PAUSE-ON-ITERATE. | Grounded-review experimental design without outcome evidence. PAUSE. | Persistent empirical gap, not an exhausted scientific topic. |
| Q4P9 | Verification-order analogy withdrawn; standard information argument and confounded comparison. PAUSE. | Conditional path bound without causal contract evidence. PAUSE. | No established explanation of the observed format gap. |
| Q7P7 | Restricted voluntary migration mechanism and forecast-error certificate. DRAFT. | Dispatch coupling, carbon feedback, prior art and source-mechanism concerns. PAUSE. | Hold for assumption/source audit, not automatic rejection of O. |
| Q8P8 | Compliance versus rigidity hypothesis requires integrated experiment. PAUSE. | Corrects dispersion interpretation; variable in-hand object transform defeats wrist-only sufficiency. DRAFT. | Sharper conditional information argument, not measured system failure. |
| Q3P6 | Frozen-state comparator experiment needed. PAUSE. | No demonstrated transition-specific comparator bias. PAUSE. | Shared untested behavioral mechanism. |
| Q1P6 | Fixed-population reward ledger and participation-boundary repair. DRAFT. | Better contribution ranking need not improve gradient variance; critic-offset control proposed. PAUSE. | Complementary finite-training branch; do not lose R findings because of verdict. |
| Q1P2 | Calibrated room-level coverage gives simultaneous selective first-gate correctness. DRAFT. | Candidate retention and bounded-gap audits, with visibility limits. PAUSE. | R does not reconstruct or refute O's calibration theorem. |

Evidence locations, relative to repository root:

- Original: `threads/<pair>/ledger.jsonl`, `<pair>.verdict.json`, and
  `paper/paper.tex` where present.
- Rerun: the same layout under
  `experiments/2026-09-23-gpt-6-sol-rerun-01/threads/`.
- Rerun provenance and settings: its `manifest.json`.
- Q7P7's alleged source-condition contradiction is in the rerun verifier
  verdict. It remains an audit lead, not an independently validated finding
  of this inventory. Audit shared Q7 assumptions before treating dependent
  mechanism conclusions as established.

## Frozen seed selection

Use final accepted papers, never readable edits or intermediate drafts.
Select five distinct argument families rather than only the rerun's successes.
Each has an accepted internal paper status and `build_ok: true` at preparation.

| Seed | Campaign and pair | Reason for inclusion |
|---|---|---|
| S1 | O Q4P6 | Constructive peer-comparison identification branch absent from R. |
| S2 | O Q1P2 | Constructive calibration-to-first-gate certificate absent from R. |
| S3 | R Q3P10 | Computation-priced auction design and analytical constraints. |
| S4 | R Q7P1 | Surrogate-risk counterexamples and conditional bounds. |
| S5 | R Q8P8 | Conditional object-pose information limitation. |

Do not include O Q7P1 as a second seed: substantial overlap with S4.
Defer O Q7P7 pending its source-assumption audit. Defer O Q1P6 to keep this
pilot small and avoid overweighting reward shaping; retain its claims in the
novelty baseline. Selection is purposive, not randomized or exhaustive.
S4's mechanism statements remain conditional and do not certify feasibility
of Q7's source conditions. Its surrogate-objective distinction is the seed's
central contribution.

Seed identity is the following SHA-256 of `paper/paper.tex` at the evidence
locations above. Freeze the corresponding PDF, bibliography, compiled
bibliography and review record alongside it when staging inputs.

| Seed | TeX SHA-256 |
|---|---|
| S1 | `f4e70ebcaf3112e29b29680d48c64c7ffdbf23ab791ad484e36f24937c422ab4` |
| S2 | `5896b372b1fc75e409d05a320f6d9f83edf0d6d3f6f33229243046e066c6d974` |
| S3 | `2a2458b6414fc8047535184b0f88c50c25808df9a06e22a10b0243f1ca9795ea` |
| S4 | `f7075a418006a0c39b5ec5ed2216997bcc3e021cc2ca168346a25c9ead5353e9` |
| S5 | `c58e63010680796d1c486ff2af3dfe3fc80db63d45d739654f5b36ebea010556` |

## Fixed allocation: 14 research threads per arm

Control repeats the original 14 pairs with fresh context. Treatment replaces
P by an accepted paper. Match Q frequency exactly across arms. Use unique
treatment pairs, exclude pairing a seed with its own parent Q, and distribute
seeds approximately evenly. Rows are scheduling blocks, not independent
matched statistical observations. No new scan or outcome-dependent selection.

| Block | Repeat control | Reinjection |
|---|---|---|
| 01 | Q4P10 | Q4 S2 |
| 02 | Q3P9 | Q3 S1 |
| 03 | Q4P6 | Q4 S3 |
| 04 | Q3P10 | Q3 S2 |
| 05 | Q7P1 | Q7 S3 |
| 06 | Q4P3 | Q4 S4 |
| 07 | Q1P1 | Q1 S3 |
| 08 | Q3P3 | Q3 S4 |
| 09 | Q4P9 | Q4 S5 |
| 10 | Q7P7 | Q7 S2 |
| 11 | Q8P8 | Q8 S4 |
| 12 | Q3P6 | Q3 S5 |
| 13 | Q1P6 | Q1 S5 |
| 14 | Q1P2 | Q1 S1 |

Counts: Q1=3, Q3=4, Q4=4, Q7=2, Q8=1 in each arm;
S1=2, S2=3, S3=3, S4=3, S5=3. Treatment Q indices refer to the
unchanged original Q corpus. Preserve original Q/P corpus hashes from the
rerun manifest. Assign generated seeds distinct corpus IDs, not existing P IDs.

## Execution controls and preflight

1. Stage two fresh experiment roots and an external provenance manifest.
   Freeze engine commit, prompts, inputs, complete rendered full texts and
   configuration hashes. Keep the seeds' references and limitations intact;
   do not inject prior ledgers, this inventory, verdicts or review instructions
   into research contexts. Resolve bibliography/includes when rendering TeX.
2. Use the same current engine and prompts for both arms. GPT-6-sol, high
   reasoning, peers ada/emmy, seats=2, research rounds=4, repairs=1,
   paper rounds=3. Use rerun allowances: peer 1800 seconds/calls=2,
   consolidation 1800, verification 900, paper 1800, review 900, edit 900.
   Do not force all cases to exhaust their rounds or to write papers.
3. Propose a USD 200 API-equivalent admission cap per arm, USD 400 total,
   following the historical configuration. Confirm pricing and budget
   accounting before launch; historical rates are not a current price quote.
   Equal caps do not guarantee equal realized expenditure or completion.
   Do not raise a cap silently. Report budget-censored cases separately.
4. Alternate arms by block, reversing which arm starts on alternate blocks.
   Resume failed stages with the same identity rather than starting an
   unrecorded fresh scientific replicate. Log failures, retries and costs.
5. Run the existing Astra supervisor/runner arrangement with five-minute
   health checks and a six-hour session window. Supervisor cost is separate
   operational overhead and must also be recorded. Expiry is not scientific
   completion; explicitly hand off unfinished work.
6. Restrict each research session to its assigned sources and own fresh
   thread. Disable inherited project documents as in the prior rerun.
   Record whether isolation is instruction-based or enforced. Keep identical
   web-search policy in both arms and record discovered campaign leakage.
7. Before spending: validate all 28 pair identities, seed acceptance and hashes,
   full-text ingestion, resource limits, health visibility and resume commands.
   Record exact launch commands in the experiment manifest after staging;
   do not guess command-line flags or reuse the old experiment adapter blindly.

Only one recursive generation is allowed. No output of this pilot becomes
another input during the pilot. This protocol is ready for staging, not a
claim that staging and preflight have already passed.

## Evaluation and decision rule

Build a claim-level comparison, including findings in PAUSE threads, against
the union of both historical campaigns and the injected papers. The table
above is an index; assess novelty against the full relevant ledgers/papers,
not only these summaries. Keep full ancestry outside research contexts:
seed campaign/pair/artifact hash, parent Q/P, and pilot thread/claim.

For each candidate claim record its statement, assumptions, evidence location,
closest prior claim, substantive difference, support type and unresolved gap.
Classify it as repetition/reformulation, extension, correction/counterexample,
new connection, or unsupported proposal. A new application name or a DRAFT
verdict alone is not an advance. Novelty here means relative to the campaign
baseline; literature novelty needs separate support.

Use the same post-hoc rubric for both arms, initially hiding arm labels when
judging support and usefulness. Then reveal ancestry to assess inheritance and
novelty. Input content may reveal the arm, so do not claim perfect blinding.
Seek user adjudication of disputed material claims rather than deciding from
automatic verdict counts alone. Deduplicate across threads and report overlap.

Primary descriptive result: distinct supported substantive advances per arm,
with a short evidence-based account of usefulness. Also report joint results
that materially use both inputs versus results driven by one input alone,
paper acceptance, tokens, API-equivalent cost, wall time and censored work.
Compare yield per realized research cost as well as under equal admission caps.
Count operations/supervision separately. Do not treat correlated claims or
shared seeds as independent statistical samples.

If reinjection yields useful supported advances absent from the repeat arm,
consider a second generation using only adjudicated final papers. If both arms
mostly repeat the baseline, stop or change inputs rather than automatically
repeating again. If results are ambiguous or budget-censored, report that and
choose a focused follow-up. No saturation claim follows from this single pilot.

## Immediate next action

Review this frozen allocation and proposed spending ceiling, then stage and
preflight the two arms. Any change before launch gets a dated amendment;
changes after seeing outcomes must be reported as deviations, not silently
folded into the original protocol. No experiment was launched while preparing
this document.
