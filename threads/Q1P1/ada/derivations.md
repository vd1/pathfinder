# ada: derivations for the pair Q (LAA survey) x P (distributed ZO CVaR)

Notation follows P. C^i(x) = CVaR_{alpha_i}[J^i(x,xi)], |J^i| <= U_i, J^i(.,xi) convex and L_i-Lipschitz.
One-point estimator (P, eq. estimated gradient): g = (d/delta_i) Chat_s(y + delta_i u) u, u ~ Unif(S^{d-1}).

Define
- Cbar_s(x) := E_xi[Chat_s(x)]  (expected empirical CVaR with s samples)
- Ctilde_s(x) := E_nu[Cbar_s(x + delta nu)], nu ~ Unif(B)  (this is P's Ctilde^i in the proof of Thm 2)
- C_delta(x) := E_nu[C(x + delta nu)]  (P eq. smoothed cvar)

## F1. The finite-sample term in P is O(e_s), not O(e_s / delta_min)

Facts taken from P:
1. E[g_k^i | F_k] = grad Ctilde_{s_k^i}(y_k^i) (P eq. surrogate-unbiased-gradient; P states it for fixed s,
   and the same identity holds step by step for a deterministic schedule s_k^i).
2. Ctilde_s is convex and L-Lipschitz (P, proof of Thm 2: empirical CVaR is convex and L-Lipschitz per realization).
3. |Chat_s(x) - C(x)| <= (2U/alpha) sup_z |Phat - P| (P, Lemma cvar-estimation-error, from wang2022risk Lemma 3),
   and E sup_z |Phat - P| <= sqrt(pi/(2s)) (DKW, P appendix).

New step (uniform value bound). Let b_s := sup_x |Cbar_s(x) - C(x)|. By 3,
    b_s <= sup_x E|Chat_s(x) - C(x)| <= (U/alpha) sqrt(2 pi / s).
Also Cbar_s <= C pointwise, since Chat_s is a minimum over tau of a sample average and E[min] <= min E.
Hence Ctilde_s - C_delta takes values in [-b_s, 0] uniformly in x.

Corrected inner-product step (replaces P eq. Exp<g,y-z>, which bounds the bias by D_x E||e_k^i||):
    E[<g, y - z> | F_k] = <grad Ctilde(y), y - z> >= Ctilde(y) - Ctilde(z) >= C_delta(y) - C_delta(z) - b_s.
Averaging over agents and using P's sampling condition (1/m) sum_i 1/sqrt(s_k^i) <= e_s, the finite-sample part of D_1 becomes
    sqrt(2 pi) max_i (U_i/alpha_i) e_s        (corrected)
instead of
    sqrt(2 pi) d D_x max_i (U_i/(alpha_i delta_i)) e_s   (P).
The ratio is at least d D_x / delta_max >= 2d, because delta_max < r <= D_x/2.

Theorem 2 by the value route: xbar_inf in argmin_{X_delta} Ctilde gives
    C_delta(xbar_inf) - C_delta(z_delta) <= Ctilde(xbar_inf) + b_s - Ctilde(z_delta) <= b_s,
where P uses the gradient route D_x ||grad Ctilde - grad C_delta|| <= D_x d sqrt(2 pi) max(U/(alpha delta)) e_s.

Consequence: the conclusions of Thm 1, Cor 1, Prop 2, Thm 2 and Cors 2-3 hold with O(delta_max + e_s) in place of
O(delta_max + e_s/delta_min). The transient term rho_beta(T)/delta_min^2 is unchanged; it comes from |g| <= dU/delta.

The order in e_s cannot be improved in general. Take X in {0,1} with P(X=1) = alpha. Then CVaR_alpha = 1 and
Chat_s = min{1, K/(alpha s)} with K ~ Bin(s, alpha), so 1 - E Chat_s = E[(1 - K/(alpha s))_+], which is about
sqrt((1-alpha)/(2 pi alpha s)). The bias is Theta(1/sqrt(s)).

Implications:
- For target accuracy eps with delta ~ eps, P's bound needs e_s ~ eps^2, so s ~ eps^-4 samples per iteration;
  the corrected bound needs e_s ~ eps, so s ~ eps^-2.
- P's remark that a diminishing delta_k forces growing s_k is not supported by the corrected bound: delta enters only
  through the variance.
- P's abstract claim that the distributed bound "matches the parameter dependence of the centralized benchmark"
  compares two upper bounds that share this artifact. In Q's Axis-B terms (Q Sec. 4, "Axis B"), this is an
  achieved-bound comparison (E0 vs E0), not matched dependence.

## F2. A prediction as a baseline: robustness in the bias channel by construction

Estimator with an F_k-measurable baseline b (fixed before u_k^i and the batch are drawn):
    g^b = (d/delta)(Chat_s(y + delta u) - b) u.
- Unbiasedness: E[(d/delta) b u | F_k] = (d/delta) b E[u] = 0, so E[g^b | F_k] = grad Ctilde(y) for every b.
  The corrected F1 bias bound holds for ANY prediction.
- The second moment is exact: ||g^b||^2 = (d/delta)^2 (Chat_s(y + delta u) - b)^2, because ||u|| = 1.
- Decomposition with eta := |C(y) - b|:
    Chat_s(yhat) - b = [Chat_s(yhat) - C(yhat)] + [C(yhat) - C(y)] + [C(y) - b],
    E[(Chat_s - C)^2] <= (2U/alpha)^2 E[KS^2] <= 4U^2/(alpha^2 s)   (DKW: E[KS^2] <= 1/s),
    so E||g^b||^2 <= 3 d^2 (L^2 + eta^2/delta^2 + 4U^2/(alpha^2 s delta^2)).
- Compare P (b = 0): ||g||^2 <= d^2 U^2/delta^2.
  Consistency (eta = 0): 3 d^2 L^2 + 12 d^2 U^2/(alpha^2 s delta^2). This is free of delta except through s delta^2.
  Robustness: clip b to [-U, U], which gives ||g^b||^2 <= 4 d^2 U^2/delta^2 almost surely (factor 4 over P).
  Smoothness: quadratic in eta/delta.
- Where the prediction can come from: a point prediction of the scalar C^i(y) (Q Table predtypes, point object);
  a distributional prediction Fhat of the loss law at y (Q P5), with b = CVaR_alpha(Fhat) and
  eta <= (2U/alpha)||Fhat - F||_inf (P's Lemma) or eta <= W1(Fhat, F)/alpha; or residual feedback,
  b = Chat_{k-1}(yhat_{k-1}) (own history, prior art below).
- Exact P4 aggregation. Take candidate baselines b^(1..M), including b = 0 (P itself) and residual feedback, and let
  the weights w_k be F_k-measurable. The loss (Chat_k - sum_j w_j b_k^(j))^2 can be observed for every w after the
  query (full information) and is exp-concave on a bounded range, so exponentially weighted aggregation controls
  sum_k eta_k^2 ||g_k||^2 by the best candidate on the realized trajectory plus an aggregation regret term
  (constants not worked out; the losses carry weights eta_k^2 (d/delta)^2).
  The convergence proof only sums realized second moments along the realized iterates, so no counterfactual
  trajectory, state migration or cost reduction is needed. Q's P4 caveat ("one also needs a reduction from l_t to
  algorithm cost, a compatible state or migration rule", Q Sec. 4 item P4) is discharged exactly here.
- Taxonomy: this is not P1 (no trust branch), P2, P3 or P5 as Q defines them. The prediction enters through a
  zero-mean channel, which is the device behind REINFORCE baselines and prediction-powered inference. Q states that
  P1-P5 are "non-exclusive and incomplete" (Q Sec. 2.4); this device is a candidate missing mechanism, one where
  robustness of the mean is unconditional and only the variance depends on the error.

## Prior art located (searches run, not a novelty claim)
- Queries: "residual feedback zeroth-order CVaR risk-averse learning one-point estimator";
  "learning-augmented zeroth-order optimization predictions baseline control variate robustness consistency";
  "distributed zeroth-order optimization residual feedback Shen Zhang Nivison Bell Zavlanos".
- Residual feedback for one-point ZO: Zhang, Zhou, Ji, Zavlanos, https://arxiv.org/abs/2006.10820
- Residual feedback for zeroth-order CVaR gradients in online convex games: Wang, Shen, Zavlanos, ICML 2022,
  https://arxiv.org/abs/2203.08957 (this is P's [wang2022risk]).
- Asynchronous distributed ZO with residual feedback: Shen, Zhang, Nivison, Bell, Zavlanos, CDC 2021
  (cited in https://arxiv.org/pdf/2409.15680).
So the baseline device for ZO-CVaR is not new. What my searches did not surface: (i) reading it as an LAA
mechanism with unconditional bias-robustness, (ii) exact P4 aggregation over baselines, (iii) the F1 correction,
which makes variance the only channel through which delta hurts.

## Not verified
- P's disagreement lemma (Sundhar Ram Lemma 4.1) with projection onto X_delta; I take it as stated.
- The constants 3 and 4U^2/(alpha^2 s) above are crude (DKW-based).

## F2 experiment on P's sensor problem (ada/sim_baseline.py; raw output ada/sim_baseline_out.txt)

Setup as in P Sec. 6: m = 16, d = 10, ER(0.4) graph with Metropolis weights, s = 64, alpha = 0.5, delta = 0.4,
eta_k = c1/(k+1)^0.55, K = 3000 iterations, 3 seeds, x* approximated by x_true (lam = 1e-4, noise sd 0.01).
Entries: final ||xbar - x*||^2.

| baseline b                     | c0=0, c1=0.004 | c0=100, c1=0.004 | c0=100, c1=0.02 |
|--------------------------------|----------------|------------------|-----------------|
| none (P)                       | 0.33           | 17.2             | 59              |
| resid (own previous value)     | 0.038          | 0.11             | 1e-4            |
| oracle C(y)                    | 0.048          | 0.048            | 3e-4            |
| oracle + N(0,1)                | 0.039          | 0.039            | 7e-4            |
| oracle + N(0,100)              | 0.055          | 0.055            | 0.038           |
| clip(10 C + 100, 0, U)         | 76             | 84               | 58              |
| FTL over {none, resid, adv}    | 0.038          | 0.19             | 1e-4            |

c0 is a constant added to every loss; it leaves the optimizer unchanged. Readings:
- The clipped wrong baseline is catastrophic because U is 1e4 to 1e5 while C is small, so robustness relative to the
  worst-case bound says little on this instance. Aggregation that includes b = 0 is what protects.
- P's estimator is not translation invariant; baseline variants are (resid up to its first step, where b = 0).
- 3 seeds only; qualitative.

Wang-Shen-Zavlanos 2022 (arXiv 2203.08957), eq. (15): residual feedback g = (d/delta)(CVaR[F_t] - CVaR[F_{t-1}]) u,
with the remark that its mean equals that of the plain estimator. The device is theirs; P cites this paper and does not
use it.

## F2b. Resolving the ball/sphere mismatch in the tau-lift (response to emmy #8)

phi(x, tau, xi) = tau + (1/alpha)(J(x, xi) - tau)_+ is jointly convex. The hybrid in emmy #8 takes
- x-part (d/delta) phi(x + delta u, tau) u with u on the sphere: unbiased for grad_x of F_ball(x,tau) = E_nu phi(x+delta nu, tau);
- tau-part d_tau phi(x + delta u, tau) at the same sphere point: unbiased for d_tau of the sphere average, not of F_ball.
The pair is not the gradient of one function. Two exact fixes:
1. Gaussian smoothing: one query at x + delta v, v ~ N(0, I), gives unbiased estimates of both partial derivatives of
   F_gauss(x,tau) = E_v phi(x + delta v, tau). Perturbations are unbounded, so feasibility needs truncation; the bias is L delta sqrt(d).
2. Two queries: the sphere point for the x-part, and a ball point x + delta R w (w on the sphere, R with density d r^(d-1)) for the tau-part.
Bias of either: min_tau F_ball(x, .) is the CVaR of the mixture law of J(x + delta nu, xi), and each loss moves by at most L delta,
so it lies in [C(x) - L delta, C(x) + L delta]. There is no e_s term and no delta/alpha term. Convergence constants are not derived.

## Concessions after emmy #5
- The baseline device is prior art (residual feedback: Zhang et al., Automatica 2022, https://arxiv.org/abs/2010.07378, and
  Wang-Shen-Zavlanos 2022). Inside Q, optimistic OMD hints (Q, OCO paragraph) already give "bad hint costs a constant factor".
  The claim is limited to the LAA contract (bias-robust for any prediction, exact P4 aggregation), not the device.
- P's disagreement term is pathwise in G; with a baseline it has to be redone with E||g_l|| (linear in ||g||), not cited.

## F5. Round 2: checks of emmy #19 (F4) and a one-sided bound for the lifted surrogate

### (a) emmy F4(d) checked against the text of 2203.08957
Source: arXiv PDF of https://arxiv.org/abs/2203.08957, text extracted with pdftotext (layout partly garbled).
- Algorithm 1, line 2: n_t = ceil(b U^2 (T - t + 1)^a). Lines 4 to 12: every agent plays xhat = x + delta u for n_t rounds,
  builds the EDF from these fresh samples (eq. 2) and sets ghat = (d_i/delta) CVaR[Fhat] u (eq. 3). The samples are drawn
  after u and independently of it.
- Eq. (6): |eps| <= (U/alpha) sqrt(ln(2/gamma)/(2 n_t)). Lemma 4: sum_t |eps| <= B1, B1 of order (1/alpha) sqrt(2 ln(2T/gamma)/b) T^(1-a/2).
- Lemma 5: R <= Err(ZO) + Err(CVaR), where Err(ZO) = D^2/(2 eta) + d^2 U^2 eta T/(2 delta^2) + (4 sqrt N + Omega) L0 delta T
  and Err(CVaR) = (d_i/delta) D_x B1.
- Appendix A.4, eq. (21): the CVaR error enters as E[(d_i/delta) ||eps|| ||x_t - x*||]. This is the gradient-error step that F1 replaces.
F1 applied: under their Assumption 1 the empirical CVaR is convex in x_i for every sample realization, so
h_t(x_i) := E_{w_i in ball, u_{-i} on spheres} E_xi CVaR[Fhat](x_i + delta w_i, x_{-i,t} + delta u_{-i}) is convex, E_t ghat = grad h_t(x_t),
and h_t - C_i^delta lies in [-beta_{n_t}, 0] with beta_n = (U/alpha) sqrt(pi/(2n)) (their Lemma 3 plus E sup|Fhat - F| <= sqrt(pi/(2n))).
Then sum_t beta_{n_t} <= (1/alpha) sqrt(pi/(2b)) T^(1-a/2)/(1 - a/2), with no d, no D_x and no 1/delta. With delta ~ T^(-1/4) and
eta ~ T^(-3/4), expected regret is O(T^(3/4) + T^(1-a/2)/alpha). The corrected exponent max(3/4, 1 - a/2) is strictly below
their 1 - a/4 for every a in (0,1), and a = 1/2 reaches T^(3/4). Emmy's numbers are confirmed.
Side remark on their high-probability claim. In eqs. (21) to (23) the left side is random, while the right side carries
expectations. B1, which bounds sum |eps| only with high probability, is then substituted for E sum ||eps||. As written this is
an expectation argument. The stated "with probability at least 1 - gamma" would need an extra concentration step for
sum <ghat - E_t ghat, x_t - x*>. So an expectation-only redo is a like-for-like comparison with what their proof shows. This is
my reading of the extracted text.

### (b) 2512.22986 (varying risk levels) has the same routing
Checked in the formula alt-text of the arXiv HTML source (https://arxiv.org/html/2512.22986). The zeroth-order proof has
sum_t (d U D_x)/(delta alpha_t) sqrt(ln(2T/gamma)/(2 n_t)) <= c d U D_x sqrt(ln(2T/gamma))/(sqrt(2) delta alpha_min) T^(1-a/2).
The same paper's first-order bound is O~(T^(2/3) V_T^(1/3) + T^(1-a/2)), where the sampling term is added separately and has no delta.
F1 gives the zeroth-order bound this same additive form. Their zeroth-order Theorem 2 splits at a = 4/5:
O~(T^(1-a/4) V_T^(1/5)) for a <= 4/5 with delta = T^(-a/4) V_T^(1/5), and O~(T^(4/5) V_T^(1/5)) for a > 4/5. The sampling term
R~12 carries (d/delta) D_x T^(1-a/2)/alpha_min. With F1 it becomes O((U/alpha_min) T^(1-a/2)) with no delta, so delta can take
the a > 4/5 value for every a. That gives O~(T^(4/5) V_T^(1/5) + T^(1-a/2)/alpha_min), and the T^(4/5) regime is reached from
a = 2/5 (about T^(7/5) samples) instead of a > 4/5 (about T^(9/5)), taking V_T >= 1. The F1 step holds for any comparator that
is fixed within a step, so a dynamic comparator does not block it. I have not traced their interval partition.

### (c) The lifted surrogate is biased upward only
Let F(x, tau) = E_nu E_xi phi(x + delta nu, tau, xi), with nu uniform on the ball (or nu ~ emmy's kernel p, which is symmetric),
and G(x) = min_tau F(x, tau). Then
    C(x) <= C_delta(x) <= G(x) <= C(x) + L delta.
The first inequality is Jensen (C convex, E nu = 0). The second is min_tau E_nu[.] >= E_nu min_tau[.] = E_nu C(x + delta nu).
The third is emmy F4(a). So the two methods sit on opposite sides of C_delta. The plug-in surrogate Ctilde_s lies in
[C_delta - b_s, C_delta] (F1: sampling pulls it down), and the lifted G lies in [C_delta, C + L delta] (lifting pushes it up).

### (d) Centralized rate for the lifted, baseline-subtracted method (centralized part of item (1) in ledger #16)
Iterate z_k = (x_k, tau_k) in X_delta x [-U, U]. Estimator (two-query ball version, ledger #15, or emmy's one-query kernel):
    g_x = (d/delta)(phi(y + delta u, tau, xi) - b) u,   g_tau = 1 - (1/alpha) 1{J(y + delta nu', xi') > tau},   b F_k-measurable.
Its conditional mean is E_nu of a measurable joint subgradient selection of phi(., ., xi) at (y + delta nu, tau). For a.e. nu,
J(., xi) is differentiable at y + delta nu, and on the event J = tau the pair (grad_x phi, 1) is a valid element of the joint
subdifferential, since the level set of J(., xi) has measure zero wherever grad J is nonzero. So the mean is a joint subgradient
of F at z_k for every b. Projected SGD with steps eta_k and ergodic average zbar_K = (xbar_K, taubar_K) gives
    E F(zbar_K) - min F <= eps_opt := [D_x^2 + 4U^2 + (G_x^2 + G_tau^2) sum eta_k^2] / (2 sum eta_k),
with G_tau <= max(1, 1/alpha - 1), and G_x^2 <= (d/delta)^2 U^2 (1 + 2/alpha)^2 at b = 0 (P's worst case is (d/delta)^2 U^2).
The minimizing tau is a VaR of the mixture law, so it lies in [-U, U] and min F over X_delta x [-U, U] = min_{X_delta} G.
Using G(xbar) <= F(xbar, taubar), G <= C + L delta, and (1 - delta/r) x* in X_delta (P's shrinkage):
    E C(xbar_K) - C* <= L delta (1 + D_x/r) + eps_opt.
There is no e_s and no 1/alpha in the limit. The batch size s affects only G_x^2. With a baseline b close to E_xi phi(y, tau, xi) and a batch of s,
    G_x^2 <= 3 d^2 [ (L/alpha)^2 + Var_xi(phi)/(s delta^2) + eta^2/delta^2 ],   Var_xi(phi) <= (4U^2/alpha^2) P(J > tau),
which is about 4U^2/alpha once tau is near VaR. The (L/alpha)^2 term is the 1/alpha^2 variance price emmy noted in #7.
Distributed: the objective (1/m) sum_i F_i(x, tau_i) is jointly convex with tau_i private, so mixing acts on x only and each tau_i
takes a local projected step. I expect P's disagreement analysis to carry over with x as the only consensus variable. Not derived.
(Closed by emmy F6, ledger #23; checked in F7 below.)

## F7. Round 3: check of emmy F6, and the diminishing-delta case it left open

### (a) F6 checked
- Like for like: P Theorem 1 bounds C(xhat_T) with xhat_T = sum eta_k xbar_k / sum eta_k (P.tex:667), which is the quantity F6 bounds.
- y^i_k lies in X_delta (a convex combination of points of X_delta), and sum_i ||y^i_k - xbar_k|| <= sum_j ||x^j_k - xbar_k||
  (double stochasticity), so the step from y^i to xbar costs (L/alpha)_max times P's disagreement sum.
- Fact (C): |(a - tau)_+ - (b - tau)_+| <= |a - b| gives (L_i/alpha_i)-Lipschitz in x for every tau. Correct, and not improvable
  by shrinking T_i to the range of mixture VaRs, since a VaR at one x can sit below the support at another x.
- Final step: C <= C_delta <= G_i (Jensen, then min of an expectation >= expectation of the min). This holds for the min over
  T_i too, because restricting tau only raises the min. t_i = VaR of the mixture law at z lies in [-U_i, U_i] since |J| <= U.
- Disagreement lemma: the Sundhar Ram recursion is linear in eta_l ||g_l|| with deterministic eta, so E and sum commute. Agree.
- Numerics (emmy/check_dist_lift.out): the plug-in method stalls at the wrong end, and its gap GROWS as delta shrinks
  (0.131 at 0.3, 0.146 at 0.1), because X_delta widens toward the surrogate argmin. This shows directly that the plug-in floor is
  e_s and not delta. ball2 and kernel sit 0.0008 to 0.005 above the edge gaps. With eta_k = 0.3 (k+1)^(-0.6) and K = 2e5, the
  transient is of order K^(-0.4), about 0.008 before constants, and the ergodic average carries early iterates near x = 0,
  so the excess is consistent with the transient.
  CORRECTION after emmy #24: for ball2 the excess is only partly transient. With the tilts, the exact ball2 surrogate argmin
  lies inside X_delta (+0.655 at delta 0.3, +0.887 at 0.1, by emmy's quadrature), so part of the excess is the upward bias
  G > C of F5(c). The simulated +0.631 and +0.869 sit short of those argmins, and that remaining gap is the transient. For the
  kernel the argmin stays at the edge, so its excess is transient only.

### (b) Diminishing delta_k with s = 1: exact convergence
F6 lists "diminishing delta_k (the surrogate drifts)" as not derived. The drift does not matter, because the recursion
telescopes distances, not function values. Only the comparator has to move.
Setting: delta_k nonincreasing, x^i_{k+1} projected onto X_{delta_k}, F_i^(k) the surrogate at delta_k, and (A) holds for
F_i^(k) at step k. Comparators: z_k = (1 - delta_k/r) x* in X_{delta_k} (P's shrinkage), and FIXED t_i = VaR_alpha(J^i(x*)).
- Moving z: ||y - z_{k+1}||^2 <= ||y - z_k||^2 + 3 D_x ||z_k - z_{k+1}||. The z_k move monotonically along a segment of
  length delta_0 ||x*||/r, so the total extra is at most 3 m D_x delta_0 ||x*||/r, a constant.
- Lower side: F_i^(k)(xbar_k, tau) >= G_i^(k)(xbar_k) >= C^i(xbar_k), then convexity of C for the ergodic average. Joint
  convexity at the ergodic pair is not needed.
- Upper side: F_i^(k)(z_k, t_i) <= t_i + (1/alpha) E(J^i(x*) - t_i)_+ + (L_i/alpha) E||z_k + delta_k nu - x*||
  <= C^i(x*) + (L_i/alpha) delta_k (1 + ||x*||/r).
Result:
  E[C(xhat_T) - C*] <= (L/alpha)_avg (1 + ||x*||/r) sum eta_k delta_k / sum eta_k
      + [D_x^2 + 4U^2 + 3 D_x delta_0 ||x*||/r + sum eta_k^2 Sbar_k^2 + 2 (L/alpha)_max (1/m) sum eta_k E sum_j ||xbar_k - x^j_k||] / (2 sum eta_k),
with Sbar_k^2 = O(d^2 U^2 (1 + 2/alpha)^2 / delta_k^2) at b = 0. The disagreement sum is O(sum eta_l^2 / delta_l) / (1 - beta).
So if delta_k -> 0, sum eta_k = infinity and sum_{k<T} eta_k^2/delta_k^2 = o(sum_{k<T} eta_k), then E C(xhat_T) -> C*
with ONE sample per query (two for ball2). Example: eta_k = (k+1)^(-a), delta_k = (k+1)^(-b), with 0 < 2b < a <= 1.
The price of a fixed tau comparator is that 1/alpha comes back in the smoothing term. It still vanishes, and at fixed delta
F6's L delta (no 1/alpha) stands.
Contrast: the plug-in method at fixed s has the floor Theta(e_s) (F1), so exact convergence needs s_k -> infinity. P Remark 2
("diminishing delta forces growing s") is therefore a property of the plug-in estimator, not of zeroth-order CVaR.

### (c) Sample complexity for target accuracy eps (fixed horizon, orders in eps only)
All three need T ~ eps^(-4) iterations, which is also the number of communication rounds (delta ~ eps, eta ~ eps^3, because
the transient carries 1/delta^2). They differ only in samples per iteration:
- P's stated bound, delta + e_s/delta: s ~ eps^(-4), total ~ eps^(-8).
- Same algorithm, corrected bound (F1), delta + e_s: s ~ (U/alpha)^2 eps^(-2), total ~ eps^(-6).
- Lifted (F6 plus (b)): s = 1 (or 2), total ~ eps^(-4), with 1/alpha^2 moved into the variance constant.
Batching does not shorten the plug-in transient, since its variance (d/delta)^2 Chat^2 comes from u, not from xi. So the gains
are in samples, not in communication. Constants in d, U and alpha are not optimized here.
