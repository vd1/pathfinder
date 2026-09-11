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
