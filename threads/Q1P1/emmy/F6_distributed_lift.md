# F6. The distributed lifted method: P's proof carries over, and the limit is L delta with no e_s

This closes the distributed half of item (1) in ada #16 and #21 (ada F5(d) did the centralized half).

## Setting
P's Algorithm 1 under P's assumptions: graph assumptions (P.tex:351-364: jointly connected, doubly stochastic W_k),
J^i(., xi) L_i-Lipschitz and convex for every xi (P.tex:496-499), and |J^i| <= U_i.

Method. Agent i holds x^i_k in X_delta and tau_{i,k} in T_i = [-U_i, U_i]. Only x is sent and mixed:
y^i_k = sum_j w^{ij}_k x^j_k, as in P eq. (update y). Agent i builds (g_x^i, g_tau^i) with either
the two-query ball estimator (ada #15, fix ii) or the one-query kernel estimator (emmy F4(b)), using any F_k-measurable
baseline b^i_k in g_x^i. It then updates
x^i_{k+1} = P_{X_delta}[y^i_k - eta_k g_x^i] and tau_{i,k+1} = P_{T_i}[tau_{i,k} - eta_k g_tau^i].
A batch of s >= 1 samples, averaged inside phi, only lowers variance. Communication is exactly P's.

Objects. F_i(x, tau) = E_nu E_xi phi_i(x + delta_i nu, tau, xi) is jointly convex. G_i(x) = min_{tau in T_i} F_i(x, tau).
Phi(x, tau_1, ..., tau_m) = (1/m) sum_i F_i(x, tau_i).

## Three facts used
(A) E[(g_x^i, g_tau^i) | F_k] is a joint subgradient of F_i at (y^i_k, tau_{i,k}) for every baseline (ada F5(d), including
the a.e. argument on the event J = tau).
(B) C^i <= C^i_delta <= G_i <= C^i + L_i delta_i (ada F5(c), emmy F4(a)).
(C) F_i(., tau) is (L_i/alpha_i)-Lipschitz for every tau, because phi_i(x, tau) - phi_i(x', tau) =
(1/alpha_i) E[(J(x) - tau)_+ - (J(x') - tau)_+]. The factor 1/alpha is attained when tau lies below the support of J,
where grad_x phi = (1/alpha) E grad J. It enters the disagreement term only.

## One-step recursion
For z in X_delta and t in the product of the T_i, nonexpansiveness of the product projection gives
  ||x^i_{k+1} - z||^2 + (tau_{i,k+1} - t_i)^2 <= ||y^i_k - z||^2 + (tau_{i,k} - t_i)^2
      - 2 eta_k <g^i, (y^i_k - z, tau_{i,k} - t_i)> + eta_k^2 ||g^i||^2.
By (A) and joint convexity, the conditional mean of the inner product is at least F_i(y^i_k, tau_{i,k}) - F_i(z, t_i).
By (C) this is at least F_i(xbar_k, tau_{i,k}) - F_i(z, t_i) - (L_i/alpha_i) ||y^i_k - xbar_k||.
Sum over i with the potential V_k = sum_i ||y^i_k - z||^2 + sum_i (tau_{i,k} - t_i)^2. The tau-parts are not mixed, and
P eq. (y<=x) (P.tex:601-605) handles x. With S_i^2 := sup E[||g^i||^2 | F_k]:
  E[V_{k+1} | F_k] <= V_k - 2 m eta_k [Phi(xbar_k, tau_k) - Phi(z, t)]
      + 2 eta_k (L/alpha)_max sum_j ||xbar_k - x^j_k|| + eta_k^2 sum_i S_i^2.
This is P's recursion (P.tex:575-580) with three changes. D_1 drops out, because the bias now sits inside Phi and is
handled by (B) at the end. L_max becomes (L/alpha)_max in the disagreement term. G_i^2 becomes the second moment S_i^2.

## Bound
Telescope with eta-weights. Use joint convexity of Phi at the ergodic pair (xhat_T, tauhat_T), and
C(xhat) = (1/m) sum_i C^i(xhat) <= (1/m) sum_i G_i(xhat) <= Phi(xhat, tauhat), which is (B) plus the definition of G_i.
Take z = (1 - delta_max/r) x* (P's comparator) and t_i = argmin_tau F_i(z, tau). This is a VaR of the mixture law, so it
lies in T_i. Then Phi(z, t) = (1/m) sum_i G_i(z) <= C(z) + (1/m) sum_i L_i delta_i, and V_0/m <= D_x^2 + 4 U_max^2:

  E[C(xhat_T) - C*] <= (1/m) sum_i L_i delta_i + L_max delta_max ||x*||/r
      + [ D_x^2 + 4 U_max^2 + Sbar^2 sum_k eta_k^2 + 2 (L/alpha)_max (1/m) sum_k eta_k E sum_j ||xbar_k - x^j_k|| ] / (2 sum_k eta_k),

with Sbar^2 = (1/m) sum_i S_i^2.

Disagreement. P's Lemma 4.1 (Sundhar Ram; P.tex:529-536) uses the gradient only through the linear terms
eta_l ||g_x^j||, which include the projection error ||P(r) - r|| <= eta ||g_x|| (y is in X_delta). The recursion is
linear in these norms, so it holds in expectation with G_j replaced by M_j := sup E[||g_x^j|| | F_k] <= S_j. The
tau-parts do not enter, since tau is not mixed. For the two-query ball estimator, ||g_x|| <= d U (1 + 2/alpha)/delta
pathwise, so P's lemma applies verbatim. For the kernel estimator the score is unbounded near the sphere, so only the
expectation version applies. P's bound K_0 + K_1 G_max sum eta^2 (P.tex:757) then holds with M_max in place of G_max.

## Reading
- The limiting neighbourhood is (1/m) sum_i L_i delta_i + L_max delta_max ||x*||/r. It has no e_s, no 1/alpha, and no
  sampling condition (P eq. (8)), and it holds with s = 1. The corrected plug-in limit (F1) is O(L delta + e_s), so the
  lifted method removes the finite-sample floor in the distributed setting too, and communication is unchanged.
- The price is confined to the transient. The disagreement term carries (L/alpha)_max and S_i^2 carries 1/alpha^2.
  Each agent also keeps a private scalar and needs either a second query or a heavier-tailed one-query score (emmy F4(b)).
- Baselines (ada F2) enter through S_i^2 and M_i only. The aggregation contract (emmy #13, ada #17) carries over
  unchanged, because the regret argument uses the realized sum of eta_k^2 ||g_x||^2.
- Not derived: diminishing delta_k (the surrogate F_i then drifts with k), a last-iterate version (P Thm 2), and
  high-probability versions. The tau-projection radius U_i can be replaced by any interval that contains the VaRs of
  the mixture laws on X_delta.
- Numerics: emmy/check_dist_lift.py, output in emmy/check_dist_lift.out. Exact surrogate fixed points:
  emmy/check_dist_lift_fixedpoint.py, output in emmy/check_dist_lift_fixedpoint.out.

## Numerics (m = 4 ring, alpha = 0.1, 100 runs, 2e5 iterations, residual baselines)
Agent i has loss J^i = (atomic F1 loss) + kappa_i q with kappa = (0.3, -0.3, 0.1, -0.1). The network objective is the
F1 instance, and the agents' own minimizers sit at opposite ends. With the tilts the alpha-tail of the ball mixture
is no longer the A = 1 group near the edge, so G > C there and the lifted fixed point moves inside X_delta. This
instance therefore exercises the upward bias (B), which the single-agent instance in F4(c) did not.

| variant | delta | ergodic xbar | surrogate argmin | true gap (sim) | gap at surrogate argmin | edge gap |
|---|---|---|---|---|---|---|
| plug-in, s = 16 (P) | 0.3 | -0.699 | left end | 0.1312 | | 0.0232 |
| plug-in, s = 16 (P) | 0.1 | -0.890 | left end | 0.1459 | | 0.0077 |
| lifted ball2, s = 1 | 0.3 | +0.631 | +0.655 | 0.0285 | 0.0266 | 0.0232 |
| lifted ball2, s = 1 | 0.1 | +0.869 | +0.887 | 0.0101 | 0.0087 | 0.0077 |
| lifted kernel k = 3, s = 1 | 0.3 | +0.690 | +0.700 | 0.0239 | 0.0232 | 0.0232 |
| lifted kernel k = 3, s = 1 | 0.1 | +0.889 | +0.900 | 0.0085 | 0.0077 | 0.0077 |

All 100 lifted runs end on the correct side, and final disagreement is at most 0.001 in every row. The lifted runs
sit slightly short of their surrogate argmin, which fits a transient in a second-half ergodic average. The upward bias
max_x [(1/m) sum_i G_i - C] is 0.0128 (ball, delta = 0.3) and 0.0020 (kernel), far below L delta, so the instance does not
test whether L delta is tight. The ball and kernel surrogates differ, and here the kernel's centre-heavy mixing gives the
smaller bias.
