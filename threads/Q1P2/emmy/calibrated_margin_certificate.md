# Calibrating the Missing Wall-Error Radius

## Revised question

The verifier exposed a gap in the earlier proposal: P's pose-graph covariance does not imply the assumed Hausdorff bound. I therefore sharpen the question again:

> Can P's empirical room-estimation pipeline produce a statistically valid wall-error radius that makes the first room-to-door gate selectively safe on a new room?

The answer is conditionally yes at the room-population level. It is not a deterministic or per-room safety result.

## Construction from the pair

Fix P's complete room-fitting pipeline, including its empirically tuned thresholds. On `n` calibration rooms with reference wall sets `W*_j`, run that pipeline without refitting it and record

`R_j = d_H(W_hat_j, W*_j)`.

For target miscoverage `alpha`, let `k = ceil((n + 1)(1 - alpha))` and let `epsilon_alpha` be the `k`th smallest calibration score. If `k > n`, use an infinite radius, which correctly yields no informative certification. For an exchangeable calibration sample and new room, the rank argument for split conformal prediction gives

`Pr[d_H(W_hat_new, W*_new) <= epsilon_alpha] >= 1 - alpha`,

up to the usual handling of ties, for example conservative ordering or randomized tie breaking.

Now run the earlier margin rule on every scan point `p`:

- certify acceptance when `dist(p, W_hat_new) + epsilon_alpha <= delta`;
- certify rejection when `dist(p, W_hat_new) - epsilon_alpha > delta`;
- otherwise mark the point's dependency region ambiguous and use the declared regional fallback.

On the single wall-coverage event, the distance-to-set inequality holds for every `p`. Consequently all certified first-gate decisions in that room simultaneously match the decisions obtained from the reference walls. This is stronger than a pointwise union bound and introduces no dependence on the number of scan points. Marginally over a new exchangeable room,

`Pr[all certified first-gate decisions are correct] >= 1 - alpha`.

This is the problem-specific reduction Q says is necessary: calibration coverage becomes correctness of P's first discontinuous interface through the Hausdorff distance lemma and margin rule. Neither calibration alone nor P's covariance supplies that reduction.

## Why P can test it

P already has a Webots pipeline with known simulated geometry, empirically tuned detection thresholds, and controllable LiDAR, odometry, and angular noise (P lines 484-486 and 609-611). Those ingredients can create disjoint training, calibration, and test rooms. P also reports real-room operation but only a maximum robot-position error, not wall-set coverage (P line 505), so a real test needs independently surveyed or otherwise reference-quality walls.

The key experiment is calibration rather than another average-error table. For each noise regime and room family, report empirical room-level coverage, radius size, fraction of scan dependency regions sent to fallback, first-gate disagreement against reference walls, final door recall and topology error, compute, and motion. Calibration must occur at the independent room or trajectory-cluster level, not by treating correlated LiDAR points or frames as exchangeable examples. A held-out stress set should include P's own failure types: high noise, partial occlusion, L-shaped rooms mistaken for rectangles, and newly revealed openings (P lines 609 and 615-619).

## What the result does not establish

- Exchangeability is substantive. A radius calibrated on P's simplified tuned rooms does not cover a new building, sensor, noise regime, or adaptively chosen next room merely by conformal terminology. Q explicitly warns that non-exchangeable extensions require model-specific penalties (Q line 1204).
- Marginal room-level coverage is not conditional safety for a particular room or for rare layouts. Stratifying by a predeclared noise or geometry class may improve relevance but consumes calibration data and needs coverage reported per stratum.
- A wrong-topology room estimate can have a large Hausdorff score. Calibration tolerates such failures only through their population frequency; it cannot certify a visibly suspect individual estimate unless another valid conditioning or abstention mechanism is proved.
- Coverage certifies only the wall-distance gate. P next resamples a polar scan, differentiates, thresholds, and pairs peaks (P lines 358 and 364-380). Full door correctness still requires a fixed-grid dependency contract and margins for later thresholds.
- The guarantee says nothing about the accuracy or cost of the regional fallback. Q requires separate evidence for fallback feasibility and accounting (Q lines 1109 and 1114-1119).

## Publication claim

The most defensible paired paper is now narrower and better supported:

> Calibrated selective constraint propagation for concept-first perception: a finite-sample, room-level guarantee for P's first discontinuous wall-to-door interface, coupled to an interface-aware regional fallback and evaluated under controlled shift.

Its formal contribution is the chain from conformal wall-set coverage to simultaneous first-gate correctness. Its empirical contribution is to measure when that chain remains calibrated and whether the selective fallback preserves P's intended efficiency gain. A compute-only dovetail bound can remain secondary under explicit completeness and preemption assumptions. Active-motion competitiveness should not be claimed.

## Remaining unresolved issue

The largest unresolved issue is the deployment population. P's preliminary rooms are simplified and its parameters are setup-specific (P lines 484-486). Without a defensible sampling unit and target distribution, the conformal theorem is formally correct but operationally weak. The proposed paper must define that population before collecting calibration data and must treat distribution shift as an evaluated failure mode, not hide it inside the coverage statement.
