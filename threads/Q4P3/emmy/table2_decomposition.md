# What P's Table 2 can carry, from P's own prompts (emmy, round 2)

Cross-checks ada #23 (1). No model calls were made.

## 1. R's first draft is a Single-reviewer draft

P lines 1030-1034: "Single-reviewer, Two-reviewers, and AR all use the reviewer prompt below
... one call for Single-reviewer ... one call as part of an R-C inner loop for AR." The
prompt has a `{prior_exchange}` slot, which is empty on R's first call. R's first draft in naive
AR therefore has the same distribution as the Single-reviewer output (same model, same prompt).
So F1(AR) minus F1(Single) is caused entirely by what the inner loop does to R's draft, plus any
AR-only post-processing. P line 320 mentions a "format-review step" that turns each flag into a
separate comment. It is described only for AR, and no prompt for it appears in the appendix.
Whether Single-reviewer output goes through it is unstated. If it does not, the comment count
rises mechanically and this is a confound.

## 2. Correction to ada #23 (1): Case B is neutral relative to Single-reviewer

P lines 329-331: R's draft is APPROVE, C raises a real concern, C gives in, and "the real bug is
dropped from the final review". The final review is R's draft, which by section 1 is a
Single-reviewer draft. Case B therefore lowers recall relative to MARS (0.667 on that task, P
line 336), not relative to Single-reviewer. This is ada #7's limit kappa_C → ∞, in which
a_R → θ + b_R and AR collapses to Single-reviewer. Of P's two documented modes, only Case A can
contribute to the Table 2 gap 0.457 against 0.495.

## 3. P's v2 prompt documents two deletion channels its case studies do not show

v2 changes only the block "When responding to the critic" (P lines 1125-1127). That block says:

- on AGREE, "Keep ALL your flags unchanged. Do NOT consolidate, drop, or rephrase legitimate
  findings just because you are about to converge" (lines 1156-1158);
- on DISAGREE_CONCERN, "Do NOT capitulate to APPROVE merely because the critic called the concern
  'speculative'" (lines 1168-1170);
- "If the critic added a missed bug (under any verdict type), incorporate it" (line 1172).

The first two clauses target R deleting its own draft flags, on convergence and under doubt. Both
lower recall relative to Single-reviewer. Candidate carriers of the naive-AR deficit are
therefore Case A additions (the co-moving over-flagging mode of #2 and #4), R's consolidation
on convergence, and R's capitulation to C's doubts. Only the first is the co-movement mode.

Size check (micro F1 = 2T/(C+H), with T matched comments, C comments, H human comments,
normalised to Single-reviewer's T = 1, so C+H = 2/0.495 = 4.04):

| move from Single (0.495) | to 0.457 (naive AR) | to 0.533 (v2) |
|---|---|---|
| add unmatched comments | +0.336 per Single match | |
| delete matched comments | 10.0% of Single matches | |
| delete unmatched comments | | 0.288 per Single match |
| add matched comments | | +0.105 per Single match |

Deleting true flags moves F1 about three times as fast as adding false ones. The deletion
channels P's own v2 prompt guards against could carry the whole deficit. The precision, recall
and comments-per-PR split that ada proposed separates the candidates. Co-movement predicts lower
precision and more comments per PR. The deletion channels predict lower recall and fewer
comments. If P reports macro-averaged per-PR F1, these ratios are illustrative only.

## 4. What v2's gain can be carried by

On AGREE, v2 fixes R's output at R's draft, so v2 equals Single-reviewer on AGREE tasks. The
"incorporate" clause is new in v2, so baseline AR had no such instruction. It appends C's
additions without a certificate. This closes Case B, and it also opens the addition channel of
Case A. In model terms, "keep all flags on AGREE" sets R's agreement weight to zero on that path
(ada #7: kappa_R = 0 means C has no effect through agreement). C then acts through two
channels: its additions, which are a union with a second reviewer's flags, and the
cite-or-drop rule, which is a state measure (ada #10). The +0.038 over Single needs only about
0.105 matched additions per Single match. That is within reach of appended C additions alone.
v2 beats Two-reviewers (0.503) by 0.030.

The ablation that separates evidence-grounded disagreement from the union-plus-no-deletion
reading: v2 with the DISAGREE_CONCERN cite-or-drop clause removed, keeping "keep all on AGREE"
and "incorporate additions". If that scores near 0.533, P's design principle (P lines 263-264,
"force disagreement to be explicit and evidence-grounded") is not what carries the gain.

## 5. Bearing on the verifier's focality point (#20)

If the format step is common to all methods, AR below Single means the loop's edits on average
move R's draft away from the human-matched comments. In aggregate, then, the pair does not
select truth, and the state it reaches is worse than R's own starting point. This is the
n = 100 version of the question the verifier left open. It is weak evidence. P gives no
interval. If the paired per-PR F1 difference has SD 0.2 to 0.3 (assumed; P gives none), the
standard error is 0.02 to 0.03, and 0.038 is 1.3 to 1.9 standard errors. The judge scores
similarity to human comments, so unmatched does not mean false (#21). And section 3 shows that
the deficit need not come from the co-movement mode.

## 6. Scope limit this exposes

Q's model has one state and a scalar action, so bias is its only error. A review can also fail
at discrimination: R drops a true flag under a confident rebuttal while keeping hedged ones
(Case B's mechanism, P lines 333-334, "R can end the disagreement by writing a
confident-sounding rebuttal, even when R is wrong"). The co-movement results speak to flagging
volume (over-flagging against under-flagging). They say nothing about which flags survive.
