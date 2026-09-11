# Margin-Safe Hierarchical Constraint Propagation

## Sharpened question

I changed the initial question from "can P's concept lifecycle be made cost-aware and robust?" to a narrower one:

> When does P's room-to-door constraint propagation preserve small upstream geometric errors as small downstream errors, and can the failure cases be isolated for a costed fallback?

This is a useful meeting point because Q gives a sufficient condition for propagating an error guarantee through a pipeline, while P gives a deployed edge map whose thresholding violates that condition without an additional margin assumption.

## Source-supported setup

P makes hierarchical constraint propagation its central architectural claim: an instantiated room supplies walls that constrain door detection, with intended efficiency and reliability gains that are not yet quantitatively demonstrated (P lines 126, 148-150). Its actual door detector retains a point `p` only when `dist(p,W) <= delta`, with `delta = 0.15 m`, and later applies another hard threshold to a range derivative (P lines 358, 364-380). A door is therefore downstream of a room-derived wall set `W` through a discrete filter.

P also reports exactly the relevant upstream failures. Noise and odometry drift can cause an incorrect room model to be accepted (P lines 603-611), and a fixed accepted model can become inconsistent as exploration reveals more geometry (P lines 615-630). Its current topological success was measured only in simplified, tuned settings (P lines 481-486 and 527-559).

Q's error-propagation proposition requires the edge map between components to be Lipschitz, or to have another stated additive perturbation model; without it, Q explicitly says no transferred smoothness guarantee follows (Q lines 1095-1109). Q also requires fallback and sensing costs to be charged rather than inferred away (Q lines 968-979, 1114-1119, 1242-1258).

## Basic result

Let `W*` be the true wall set, `W_hat` its estimate, and assume their Hausdorff distance is at most `epsilon`. For a fixed point `p`, distance to a set obeys

`|dist(p,W_hat) - dist(p,W*)| <= epsilon`.

This yields two claims.

**Instability without margin.** The hard membership map `1[dist(p,W) <= delta]` is not globally Lipschitz from Hausdorff wall error to discrete membership error. For every positive `epsilon`, translate a wall by at most `epsilon` and place a critical point within that distance of the threshold boundary. Its membership flips. If that point is a required door-edge point, the candidate door can disappear despite arbitrarily small wall error. Thus a small room-geometry error need not imply a small topological error.

**Stability with margin.** If every point used by the downstream detector satisfies

`|dist(p,W*) - delta| > epsilon`,

then estimated-wall filtering and true-wall filtering agree for those points. This follows immediately from the distance inequality. The result is only for the first filter. The derivative, width, and segment-on-wall tests need their own margins before the full door output is stable.

This is modest but nontrivial: P supplies a concrete counterexample to automatic error composition, and Q identifies the missing interface property. Neither paper alone states the geometric condition.

## Construction suggested by the result

Replace the single threshold decision with an uncertainty band based on a certified or empirically calibrated wall-error bound `epsilon`:

- accept a point into the constrained detector if `dist(p,W_hat) + epsilon <= delta`;
- reject it if `dist(p,W_hat) - epsilon > delta`;
- send the remaining ambiguous band to a prediction-independent detector, an extra viewpoint, or deferred processing.

The first two decisions are certified under the Hausdorff bound. Only ambiguous cases consume fallback sensing or computation. This aligns with ada's independent proposal to interleave constrained and global detection, but supplies a precise trigger: geometric margin, not an uncalibrated confidence or residual alone.

The policy is not yet a competitive algorithm. To make a theorem possible, a paper must declare: the cost of an extra view or global scan, the loss of a missed or false door, whether wrong graph edits are reversible, and the comparator's information and sensing costs. Q's `kappa` accounting can then price fallback calls, but does not itself establish a ratio.

## Falsifiable study

A focused paper could contribute a margin theorem plus an experiment in P's existing Webots and real-robot system:

1. Estimate wall uncertainty from the pose graph and compute each candidate's threshold margin.
2. Compare hard hierarchical filtering, global door detection, and uncertainty-band hybrid filtering.
3. Sweep the noise ranges already proposed by P (P lines 609-611), plus controlled near-threshold wall and occlusion cases.
4. Report topology precision and recall, navigation loss, extra viewpoints, CPU time, and latency. Plot failure probability and fallback rate against normalized margin `margin / epsilon`.
5. Test the specific prediction that hard filtering has a sharp failure boundary near margin 1, while the hybrid retains topology at a cost concentrated in the ambiguous band.

The publication claim should be conditional: "hierarchical constraints are safe and efficient when their uncertainty margins are explicit." It should not claim general robustness for concept-first scene graphs.

## Assumptions and unresolved points

- A usable bound on Hausdorff wall error is not supplied by P. Pose-graph covariance is not automatically such a bound and may need calibration.
- Stability of point membership is weaker than stability of the detected door set. Each later threshold needs a corresponding margin, and data association can introduce additional discontinuities.
- A global detector is only prediction-independent relative to the room model. It is not error-free and needs its own baseline guarantee or empirical characterization.
- P's active movements make observations policy-dependent. A static perturbation theorem does not resolve Q's endogenous-error concern.
- No prior-work search was performed, so this note makes no novelty claim beyond the pairwise synthesis.

## Assessment

There is a credible publication line, stronger than a generic application of Q's checklist: characterize and repair discontinuous error amplification in hierarchical scene-graph perception. The smallest defensible contribution is the margin analysis plus a costed hybrid detector evaluated on P's system. A broad competitive-ratio claim would be premature without a full sequential objective and comparator.
