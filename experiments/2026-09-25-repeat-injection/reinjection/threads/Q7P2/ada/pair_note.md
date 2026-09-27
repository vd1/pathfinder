# Q and P: a finite-iterate certificate and its obstruction

## What each paper supplies

Q's manager problem maximizes \(W(x)=\sum_n V_n(x_n)\) over compact convex local sets subject to
\(\sum_n x_n\leq c\) ([Q, lines 117-134](../inputs/Q.tex)). Each valuation is \(\alpha\)-strongly concave. Q proposes a
quadratic transfer whose equilibrium implements the optimum, balances the budget, and is individually
rational. Its stochastic proximal best-response scheme is claimed to converge in mean square under a
nonexpansiveness assumption ([Q, lines 410-519](../inputs/Q.tex)).

P proves a different kind of statement. A room-level split-conformal quantile of Hausdorff wall error,
together with the deterministic inequality
\(|\operatorname{dist}(p,\widehat W)-\operatorname{dist}(p,W^*)|\leq\varepsilon\),
certifies every non-abstained decision of one wall-distance
gate on a covered room ([P, lines 53-108](../inputs/P.tex)). Coverage is marginal over exchangeable
ground-truthed episodes. P supplies no calibration episodes or claim about later door, topology, or motion
stages ([P, lines 129-151](../inputs/P.tex)).

The sharpened pair question is whether a similarly calibrated scalar error can turn Q's asymptotic equilibrium
claim into a finite-iterate welfare certificate. This changes the initial question from certifying uncertain
resource capacity: neither paper connects P's walls to Q's road or charging capacities.

## A valid conditional transfer

For any feasible \(x\) and any \(\lambda\geq0\), define

\[
G(x,\lambda)=\lambda^\top c+\sum_n\sup_{z_n\in\mathcal X_n}
  \{V_n(z_n)-\lambda^\top z_n\}-W(x).
\]

Weak duality and strong concavity give, without using Q's game monotonicity claim,

\[
0\leq W(x^o)-W(x)\leq G(x,\lambda),\qquad
\|x-x^o\|^2\leq\frac{2G(x,\lambda)}{\alpha}.
\]

For the second inequality, strong concavity at the constrained maximizer gives
\(W(x^o)-W(x)\geq\alpha\|x-x^o\|^2/2\). The candidate \(x\) can be any finite iterate that passes the
known-capacity feasibility check. A nonnegative price message can provide \(\lambda\), although its quality
affects certificate tightness.

Suppose a frozen audit procedure computes an estimate \(\widehat G_i\) and a trusted oracle computes \(G_i\)
on each of \(n\) exchangeable calibration episodes. Set \(R_i=(G_i-\widehat G_i)_+\). P's order-statistic
rule, with \(k=\lceil(n+1)(1-\gamma)\rceil\) and the infinity convention, gives a radius
\(\varepsilon_\gamma\) satisfying
\(\Pr\{G_{\mathrm{new}}\leq\widehat G_{\mathrm{new}}+\varepsilon_\gamma\}\geq1-\gamma\).
On that coverage event, if the new allocation is
feasible, the two displayed bounds hold with \(G\) replaced by \(\widehat G+\varepsilon_\gamma\). Abstain if
feasibility fails or the certified welfare gap is too large. The probability of an incorrect issued
certificate is at most \(\gamma\) marginally over all new episodes; the error probability conditional on
issuance is not controlled. One episode-level score covers both welfare and allocation distance, so no
separate per-agent calibration is required.

This is a mathematical construction, not a ready mechanism. Q says \(V_n\) and \(\mathcal X_n\) are private
([Q, lines 108-139](../inputs/Q.tex)); it does not supply trusted value oracles for the calibration scores or
truthful reports of the local dual subproblems. P's rank argument requires those scores and exchangeability. Q
also allocates exactly the requested \(x_n\), so feasibility cannot be presumed away from equilibrium ([Q,
lines 144-151](../inputs/Q.tex)).

The generic idea is already close to prior work. Li et al. use conformal prediction to tighten primal and dual
optimality bounds ([arXiv:2503.04071](https://arxiv.org/abs/2503.04071)). Fabiani and Franci report
distribution-free finite-data equilibrium-distance certificates for stochastic games ([European Journal of
Control, DOI 10.1016/j.ejcon.2026.101558](https://doi.org/10.1016/j.ejcon.2026.101558)). The searches were
`conformal prediction duality gap optimization solution certificate approximate optimality`, `conformal
prediction primal dual gap stochastic optimization certificate`, and `conformal prediction equilibrium gap
games certificate`. No Q-specific novelty follows from the transfer alone.

## Why the advertised Q guarantee cannot be imported

Q's P1(ii) asks \(\Psi+\Psi^\top\preceq-\upsilon I\) with \(\upsilon>0\) ([Q, lines
200-215](../inputs/Q.tex)); its P2(i) asks \(\sum_m A_{nm}^n=0\) for every agent ([Q, lines
239-250](../inputs/Q.tex)). For any nonzero common-price direction \(v=(0,q,\ldots,0,q)\), the price-price
blocks of \(\Psi\) give

\[
v^\top(\Psi+\Psi^\top)v
=-2\sum_n q^\top\Bigl(\sum_m A_{nm}^n\Bigr)q=0.
\]

P1(ii) would make this strictly negative. The two conditions therefore have no common solution in the stated
full price space. This is an algebraic incompatibility, independent of sample size or valuation curvature;
Emmy obtained the same general argument independently in `emmy/pair_note.md`. In particular, a strong
monotonicity residual bound cannot be used to justify the explicit payment in Q's Proposition 2.

There is also a separate mismatch in Q's dynamic argument. Removing opponent-only terms from Q's explicit
payment (40) gives the own-strategy part

\[
\frac{\widehat t_n^{\mathrm{true}}}{\alpha}
=\frac12p_n^\top p_n-\frac{p_n^\top x_n}{N-1}
+\frac{N\bar p_{-n}^\top x_n}{(N-1)^2}
-\frac{p_n^\top(\bar p_{-n}+\bar x_{-n}-c)}{N-1}.
\]

The printed reduction has \(-p_n^\top p_n/2\), a negative rather than positive coefficient on
\(\bar p_{-n}^\top x_n\), and a positive rather than negative coefficient on \(p_n^\top\bar x_{-n}\) ([Q, lines
429-443](../inputs/Q.tex)). Its proximal update therefore optimizes a different payoff unless those matrices
are corrected and the convergence assumptions are checked again. Q's numerical schedule
\(Q_i=\lceil0.96^{i+1}\rceil=1\) for every iteration also does not instantiate Theorem 4's geometrically
growing sample size ([Q, lines 519 and 679](../inputs/Q.tex)).

For a direct scalar check, set \(N=2\), \(x_1=x_2=c=p_2=0\), \(p_1=\alpha=1\). Equation (40) gives
\(t_1=1/2\), while the printed reduction gives \(\widehat t_1=-1/2\). The opponent-only terms vanish at this
profile.

## Research judgment

The strongest supported finding is the incompatibility inside Q, which could motivate a focused correction
note. P suggests a finite-iterate audit protocol, but it cannot repair the incompatible LMI conditions, supply
trusted calibration data, or make strategic reports truthful. A publishable Q–P synthesis remains open:
construct a corrected mechanism with an auditable finite-iterate quantity, then test a nonvacuous calibrated
certificate on independent valuation-profile episodes. The two inputs alone do not establish such a result.
