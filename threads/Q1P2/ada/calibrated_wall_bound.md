# Calibrating the Missing Wall-Set Bound

## Why the claim changes

P's pose graph produces corrected landmarks and then selects room corners using structural priors (P 348-350). It does not give a coverage guarantee for wall error. P also reports that noise and drift can lead to accepted incorrect rooms (P 609-611). Therefore pose-graph covariance cannot be substituted for the assumption `d_H(W_hat,W*) <= epsilon`.

The defensible repair is statistical. It changes the proposed claim from deterministic per-run certification to finite-sample marginal coverage under exchangeability.

## Split-conformal construction

Use `n` calibration episodes, independent of any data used to choose the room estimator. Each episode must provide the estimated wall set `W_hat_i` and a ground-truth wall set `W*_i` in the same frame and with a fixed wall-set definition. Simulation or motion-capture geometry can supply the latter. Define the scalar residual

`R_i = d_H(W_hat_i, W*_i)`.

For target miscoverage `alpha`, let `k = ceil((n+1)(1-alpha))`. Let `epsilon_alpha` be the `k`th smallest calibration residual, using `+infinity` if `k > n`. If the calibration episodes and one future episode are exchangeable, the rank argument gives

`Pr[d_H(W_hat_new, W*_new) <= epsilon_alpha] >= 1-alpha`.

Ties can make coverage conservative. This is marginal coverage over episodes, not conditional coverage for each geometry or noise level. If episodes are collected along one temporally dependent robot run, or deployment shifts outside the calibration distribution, the statement does not apply without a suitable dependent-data or shift-aware method.

## Consequence for P's first gate

On the covered event, the distance-to-set inequality holds simultaneously for every queried point `p`:

`|dist(p,W_hat_new) - dist(p,W*_new)| <= epsilon_alpha`.

Therefore P's wall filter at `delta = 0.15 m` (P 358, 364) can make the following joint first-gate decisions:

- accept when `dist(p,W_hat_new) + epsilon_alpha <= delta`;
- reject when `dist(p,W_hat_new) - epsilon_alpha > delta`;
- otherwise mark the dependency region ambiguous and invoke a declared regional fallback.

With probability at least `1-alpha`, every non-ambiguous accept or reject agrees with the true-wall first gate for that episode. This is stronger than separately calibrating individual points because the conformal score controls the complete wall set. It still says nothing by itself about P's polar-scan derivative, peak pairing, width test, or segment test (P 366-380).

## Validation protocol and failure test

The experiment should split episodes into training, calibration, and test sets. It should report test coverage of `R <= epsilon_alpha`, interval width, ambiguous dependency-region rate, regional fallback cost, door recall, and topology error. Coverage should also be stratified by P's proposed LiDAR noise, odometry drift, and angular uncertainty sweep (P 609-611), but stratified plots are diagnostics unless calibration was designed to guarantee groupwise coverage.

A useful negative result is possible: if the calibrated quantile is at or above `delta`, nearly all decisive regions may become ambiguous. The theorem would remain valid but the hybrid would provide no useful efficiency gain. This directly tests whether P's hierarchical constraint is operationally useful once uncertainty and fallback cost are included, as Q requires for interface composition and safety mechanisms (Q 1095-1119).

## Remaining limits

- Ground-truth walls and the estimated walls need a common, reproducible set definition, including occluded or unobserved wall portions.
- Exchangeability is a substantive deployment assumption and does not cover temporal invalidation or novel room classes.
- Regional fallback completeness and validation remain assumptions.
- Compute cost and active-motion cost remain separate; no competitive ratio follows from calibration.
- No prior-work search was performed, so this note makes no novelty claim against the external literature.
