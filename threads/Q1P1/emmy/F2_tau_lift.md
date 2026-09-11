# F2. Lifting tau moves finite-sample CVaR error from the bias channel to the variance channel

## Construction
For agent i, phi_i(x, tau) = tau + (1/alpha_i) E[(J^i(x, xi) - tau)_+]. For each xi the integrand is jointly convex
in (x, tau) when J^i(., xi) is convex, so phi_i is jointly convex, and C^i(x) = min_tau phi_i(x, tau) with the
minimiser at VaR, which lies in [-U_i, U_i] under P's boundedness assumption.
The network problem min_x (1/m) sum_i C^i(x) equals min over (x, tau_1, ..., tau_m) of (1/m) sum_i phi_i(x, tau_i).
Only x is shared; each tau_i is private. P's mixing step is applied to x only.

Estimator (one query, one sample): draw w uniform on the unit sphere of R^{d+1}, query J^i at y + delta w_x,
form p = (tau + delta w_tau) + (1/alpha_i)(J^i(y + delta w_x, xi) - tau - delta w_tau)_+, and set
g = ((d+1)/delta) (p - b) w with b any F_k-measurable baseline (ada #3). Then E[g | F_k] is the gradient of the
ball-smoothed phi_i at (y, tau). There is no plug-in bias, because p is an unbiased sample of phi_i at the query point.

## Bias and variance
- Bias channel: |phi_i,delta - phi_i| <= L_phi delta with L_phi <= sqrt(L_i^2 + 1)/alpha_i. Partial minimisation in
  tau keeps a uniform value error, so the limiting true gap is O(L_phi delta + D L delta / r). There is no e_s term, and
  the sampling condition (8) is not needed. If the loss density at VaR is bounded, the tau part of the error is second order.
- Variance channel: |p| <= U_i (1 + 2/alpha_i) on the clipped tau range, so the pathwise G is about (d+1) U_i (1 + 2/alpha_i)/delta.
  A batch of s samples at the same query point divides the noise part of E||g||^2 by s but does not change the bias.

## Comparison with P (corrected by F1)
Plug-in limit: Theta(L delta + (U/alpha)/sqrt(s)), tight for the algorithm (F1 step 5).
Tau-lift limit: O(L delta / alpha) in the worst case, and O(L delta) plus a second-order tau term under a bounded density.
With delta_k -> 0, tau-lift converges to the true optimum with s = 1. The corrected plug-in stalls at O(e_s) for fixed s.

## Numerics (check_tau_lift.py)
Instance of F1 step 5a with alpha = 0.1, s = 16, delta = 0.3, 200 runs, 3e5 iterations, residual baseline.
Plug-in: ergodic x = -0.697 in every run, true gap 0.1311 (F1 predicts 0.1313).
Tau-lift (hybrid: ZO in x, exact tau subgradient at the sphere point): x = +0.700 in every run, gap 0.0232, which is
exactly the X_delta shrinkage. The hybrid has a ball/sphere mismatch between the x and tau components that I have
not analysed. The joint (d+1)-dim version is in check_tau_joint.py.

## How this combines with ada's baseline
After lifting, both the sampling noise and the baseline error enter only E||g||^2. The fixed point then depends
on delta alone, and every prediction or sampling choice changes only the transient. That gives the natural LAA contract:
consistency = transient with an accurate baseline, robustness = at most 4 times the unbaselined transient (clipping),
and a limiting neighbourhood O(delta) for every prediction.

## Update after check_tau_joint.py (joint (d+1)-dim smoothing in (x, tau))
Same instance, 200 runs, 4e5 iterations:
- delta = 0.3: ergodic x = -0.104 (sd 0.036), true gap 0.0852, fraction x > 0 = 0.00. Edge gap would be 0.0232.
- delta = 0.1: ergodic x = +0.647 (sd 0.097), true gap 0.0273, fraction x > 0 = 0.99. Edge gap 0.0077.
Mechanism: with A Bernoulli, phi(x, .) is piecewise linear in tau with slope 1 - 1/alpha = -9 below the lower atom,
0 on a flat stretch of width (1-x)/2 between the atoms, and 1 above. Smoothing in tau with radius delta leaves the
minimum unchanged only while the flat stretch is wider than 2 delta, i.e. x <= 1 - 4 delta (= -0.2 at delta = 0.3).
Beyond that, the steep side is averaged in and adds an artificial penalty that grows with x, which pushes the
fixed point back to about -0.1. This is the O(L_phi delta) = O(delta/alpha) smoothing bias predicted above, and
atomic losses realise it, the same class that makes the plug-in e_s floor tight.
Revised claim: tau-lifting removes the e_s floor, and with delta_k -> 0 it converges with s = 1. For a fixed delta it
trades Theta((U/alpha)/sqrt(s)) for O(L delta/alpha), so it beats the plug-in only in part of the parameter range.
The hybrid (smooth x only, exact tau subgradient) avoided the tau-smoothing penalty and reached the edge in all runs,
but I have no proof for it (its x and tau components come from ball and sphere smoothing respectively).
