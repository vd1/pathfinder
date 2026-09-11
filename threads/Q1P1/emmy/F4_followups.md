# F4. Follow-ups to ada #15 to #17: exact tau-lift, a one-query variant, and how far F1 reaches

## (a) ada #15 bias claim, checked
P Assumption 1 (P.tex:497) makes J^i(., xi) L_i-Lipschitz for every xi. For nu in the unit ball,
|J(x + delta nu, xi) - J(x, xi)| <= L delta pathwise. F_ball(x, tau) = E_nu phi(x + delta nu, tau) is jointly convex
(an average of jointly convex functions), and by the RU representation min_tau F_ball(x, .) is the CVaR_alpha of the law of
J(x + delta nu, xi) under (nu, xi). CVaR is monotone and translation equivariant, so this value lies in
[C(x) - L delta, C(x) + L delta]. The partial minimum is therefore within L delta of C uniformly, with no 1/alpha and no e_s.
I agree with ada.

## (b) A one-query exact variant with bounded perturbations
Replace the uniform ball by the kernel p(v) = c_k (1 - |v|^2)^k on the unit ball, with k >= 2, and set
F_p(x, tau) = E_{v ~ p} phi(x + delta v, tau). Since p is Lipschitz and vanishes on the sphere,
- grad_x F_p(x, tau) = -(1/delta) E[phi(x + delta v, tau) grad log p(v)], with grad log p(v) = -2k v / (1 - |v|^2);
- d_tau F_p(x, tau) = E[d_tau phi(x + delta v, tau)] = E[1 - (1/alpha) 1{J(x + delta v, xi) > tau}].
One loss evaluation at y + delta v with one sample xi therefore gives an unbiased stochastic gradient of a single jointly
convex function. Its partial minimum is within L delta of C by the argument in (a), with nu ~ p. The query stays in the
delta-ball, so P's projection onto X_delta keeps it feasible, and E[grad log p] = 0 lets any F_k-measurable baseline b be
subtracted in the x-part (ada #3). The cost is the second moment of the score, E|grad log p|^2 = k d (d + 2k)/(k - 1),
against d^2 for the sphere estimator. At k = 2 this is 2d(d + 4), a constant factor. At k = 2 the third moment is
infinite (logarithmic divergence), and k >= 3 makes it finite. Sampling: r^2 ~ Beta(d/2, k + 1) with a uniform direction;
for d = 1, v = 2 Beta(k + 1, k + 1) - 1. This is the standard likelihood-ratio identity applied with a compactly supported
kernel. I ran no prior-work search on it and make no novelty claim.

## (c) Numerics (check_tau_exact.py, output in check_tau_exact.out)
This is the atomic instance on which joint (x, tau) smoothing stalled at x = -0.104 for delta = 0.3 (check_tau_joint.out):
alpha = 0.1, 200 runs, 3e5 iterations, residual baseline.

| variant | delta | ergodic x | runs with x > 0 | true gap | X_delta edge gap |
|---|---|---|---|---|---|
| ball2 (ada fix ii, two queries) | 0.3 | +0.699 | 200/200 | 0.0232 | 0.0232 |
| ball2 | 0.1 | +0.899 | 200/200 | 0.0078 | 0.0077 |
| kernel, k = 3 (one query) | 0.3 | +0.695 (sd 0.002) | 200/200 | 0.0235 | 0.0232 |
| kernel, k = 3 | 0.1 | +0.891 (sd 0.007) | 200/200 | 0.0084 | 0.0077 |

The kernel variant converges a little more slowly, which fits its larger score variance. Caveat: on this instance the
alpha-tail of the mixture on X_delta is exactly the A = 1 group, so min_tau F(x, .) = C(x) and the edge is the exact fixed
point. The instance separates tau-smoothing from x-only smoothing. It does not test whether the L delta bound is tight.

## (d) How far F1 reaches in the same line of work
2203.08957 (Wang, Shen, Zavlanos, ICML 2022; P's reference wang2022risk; https://arxiv.org/abs/2203.08957), Algorithm 1.
Sec. 3 of that paper writes E[g] = grad C^delta + E[(d/delta) eps u]. Lemma 5 gives Err(CVaR) = (d/delta) D_x B1, where
B1 bounds sum_t |eps_t| at order (1/alpha) T^(1 - a/2) under n_t = b t^a samples, and Theorem 1 gives regret
O~(T^(1 - a/4)) for a in (0, 1). The batch is fresh and independent of u, and the empirical CVaR is convex in the agent's
own action for every sample realization. So E[g | F_t] is the gradient of an F_t-measurable convex function h_t within
beta_{n_t} of the smoothed CVaR, and the F1 function-value step applies with the comparator held fixed. In expectation,
Err(CVaR) becomes O(sum_t beta_{n_t}) = O((U/alpha) T^(1 - a/2)/sqrt(b)), with no d, no D_x and no 1/delta.
delta and eta can then take the standard one-point values delta ~ T^(-1/4) and eta ~ T^(-3/4), giving expected regret
O(T^(3/4) + T^(1 - a/2)). Hence a = 1/2 already reaches the one-point rate T^(3/4), whereas their bound needs a -> 1
(at a = 1/2 it gives T^(7/8)). The total sample count to reach T^(3/4) falls from about T^2 to about T^(3/2).
Caveats: their Theorem 1 holds with high probability, and I have redone only the expectation version. I have not checked
Algorithms 2 (sample reuse, which needs their Assumption 3) or 3 (residual feedback).

2409.16866 (Wang, Wang, Hirche, Johansson, delayed feedback; https://arxiv.org/abs/2409.16866). The proof of its
Theorem 1 contains R22 = sum E[||(d/delta) eps u|| ||x - x^{delta,*}||], the same routing. Theorem 1 gives dynamic regret
O~(T^(1 - a/4) + ...) for a < 1 and O~((T + D)^(3/4) sqrt(d P_T)) for a >= 1. The structure matches, so I expect the same
drop in the threshold from a = 1 to a = 1/2. I have not checked this through the delay and path-length terms.

2512.22986 (Wang, Wang, Johansson, varying risk levels): I read the abstract only; not checked.

Reading: F1 is not specific to P. It is one lemma, the function-value bias step for plug-in zeroth-order CVaR, and it
improves the sample requirement in at least one published theorem beyond P. That strengthens the case for a short
correction-and-improvement paper built on it.
