# Cross-check of the Margin-Safe Gate

## Verdict

Emmy's first-gate theorem is correct under its stated Hausdorff-error assumption. It also reveals a stronger reason to isolate that gate: P filters the point set before constructing the polar scan and differentiating it. A membership change can therefore alter the domain or adjacency used by the next stage, not merely one independent binary label.

## Direct verification

Let the true and estimated wall sets be \(W^*\) and \(\widehat W\), with Hausdorff distance at most \(\varepsilon\). For nonempty closed sets in the same metric space,

`|dist(p, W*) - dist(p, W_hat)| <= epsilon`.

Consequently:

- `dist(p, W_hat) + epsilon <= delta` certifies that P's true-wall gate accepts \(p\).
- `dist(p, W_hat) - epsilon > delta` certifies that the true-wall gate rejects \(p\).
- If neither condition holds, the true decision is not identified by this bound.

These statements exactly support the proposed uncertainty band. The strict and weak inequalities also match P's acceptance convention `dist(p,W) <= delta` (P, lines 358 and 364).

## Downstream amplification

P does not apply the gate to a fixed list of independently scored candidates. It first forms the retained points \(p_i\), then extracts \(\rho = p_i(\phi,k=K)\), differentiates \(\rho\), thresholds the derivative, and pairs all resulting peaks (P, lines 358 and 364-380). Without a specified sampling and interpolation convention, deleting a near-boundary point can change which samples are adjacent in \(\phi\). Pair enumeration can then turn a changed peak set into many changed candidate pairs.

Thus the first-gate margin theorem does not extend by counting ambiguous input points. A full stability result needs an interface contract after filtering, such as a fixed angular grid plus a declared fill rule, a minimum angular separation, derivative margins relative to \(\lambda\), and margins for width and segment-on-wall tests. This is a concrete instance of Q's claim that downstream composition needs metrics and sensitivity facts for every edge (Q, lines 1095-1109).

## Recommended paper claim

The smallest defensible claim is not that the full door detector is certified. It is:

> Hierarchical geometric constraints can be made selectively safe at their first discontinuous interface; an uncertainty band identifies when constrained processing may proceed and when a costed alternative is required.

The experiment should separately report the size of the ambiguous band, fallback cost, and downstream door/topology error. It should include adversarial near-threshold layouts, since P's broad random-noise sweep alone may rarely place decisive points near \(\delta\). Q's cost accounting supports charging fallback invocations (Q, lines 1242-1258), but no competitive ratio follows without a comparator and a guarantee for the fallback.

## Remaining obstacle

P supplies no certified Hausdorff bound for its estimated walls. GTSAM covariance is not automatically such a bound. A practical paper must either calibrate a finite-sample coverage statement for \(\varepsilon\) or present the result as a sensitivity analysis parameterized by \(\varepsilon\). The latter is already falsifiable but is weaker than run-time certification.
