# A one-query CVaR lift and quantile predictions

## Source facts

P defines each local CVaR by minimizing over a threshold
(lines 327--338). It queries \(s_k^i\) full noisy losses at the same
perturbed decision, then computes empirical CVaR (lines 404--445).
Its DKW error is proportional to \(1/\sqrt{s_k^i}\), multiplied by
\(d/\delta_i\) in the gradient (lines 1289--1324). P assumes
samplewise convexity, Lipschitz continuity, and bounded losses
(lines 495--501). Q requires a specified prediction target and error,
and separates error-sensitive guarantees from robustness
(lines 260--263 and 298--342).

A predicted threshold does not reduce the number of losses needed by
P's empirical estimator. The following construction changes the
estimator.

## Lifted construction

For each agent, define

\[
F_i(x,t)=t+\alpha_i^{-1}\mathbb E_\xi[(J^i(x,\xi)-t)_+],
\qquad t\in[-U_i,U_i].
\]

Then \(C^i(x)=\min_t F_i(x,t)\). The sample function
\(f_i(x,t;\xi)=t+\alpha_i^{-1}(J^i(x,\xi)-t)_+\) is jointly convex.
Retain a local threshold \(t_k^i\), mix only the decisions as P does,
and query one fresh loss
\(Z_k^i=J^i(y_k^i+\delta_i u_k^i,\xi_k^i)\). Update using

\[
g_{x,k}^i=\frac{d}{\alpha_i\delta_i}(Z_k^i-t_k^i)_+u_k^i,
\qquad
g_{t,k}^i=1-\alpha_i^{-1}\mathbf 1\{Z_k^i>t_k^i\}.
\]

At equality, choose a valid hinge subgradient. Project the decision
onto P's shrunken feasible set and the threshold onto \([-U_i,U_i]\).
Because \(t_k^i\) is fixed before \(u_k^i\), subtracting it from the
one-point scalar leaves the \(x\) expectation unchanged. The
conditional expectations give a gradient in \(x\) and a subgradient
in \(t\) of

\[
F_{i,\delta}(x,t)
=\mathbb E_{\nu\sim\operatorname{Unif}(\mathbb B)}
F_i(x+\delta_i\nu,t).
\]

There is no empirical-CVaR plug-in bias or DKW term. This uses known
analytic dependence on \(t\) while keeping P's zeroth-order oracle
in \(x\).

## Error and robustness

Let \(p_{i,k}=\Pr\{Z_k^i>t_k^i\mid\mathcal F_k\}\). Since
\(|Z_k^i|,|t_k^i|\le U_i\),

\[
\mathbb E[\|g_{x,k}^i\|^2\mid\mathcal F_k]
\le \frac{4d^2U_i^2}{\alpha_i^2\delta_i^2}p_{i,k},
\]

\[
\mathbb E[|g_{t,k}^i|^2\mid\mathcal F_k]
=1-\frac{2p_{i,k}}{\alpha_i}
+\frac{p_{i,k}}{\alpha_i^2}
\le 1+\frac{p_{i,k}}{\alpha_i^2}.
\]

The cap \(p_{i,k}\le1\) is prediction independent. If the loss
distribution has density at most \(M_i\) around an upper-tail
quantile \(q_i(y_k^i)\), samplewise \(L_i\)-Lipschitz continuity gives

\[
p_{i,k}\le\alpha_i+
M_i\bigl(|t_k^i-q_i(y_k^i)|+L_i\delta_i\bigr),
\]

provided the density bound covers the entire interval crossed by
the threshold error and perturbation. Choose any \(q_i\) satisfying
\(\Pr\{J^i(y_k^i,\xi)>q_i\}\le\alpha_i\). If this keeps
\(p_{i,k}=O(\alpha_i)\), the second moment improves from order
\(\alpha_i^{-2}\) to order \(\alpha_i^{-1}\) at fixed \(\delta_i\).
A good initial prediction alone does not ensure this occupancy
condition at later steps.
Low occupancy alone is not evidence of useful advice: the no-advice
choice \(t=U_i\) makes the hinge gradient zero initially, while its
threshold update pushes \(t\) downward. An overlarge threshold can
also make \(p_{i,k}\) small while increasing the lifted objective.
An advice claim needs a causal comparison to this no-advice rule and
an error measure that also controls threshold excess objective or
distance to a valid quantile.

The lifted smoothing error satisfies

\[
|F_{i,\delta}(x,t)-F_i(x,t)|
\le L_i\delta_i/\alpha_i.
\]

The optimized lifted objective has the sharper bound
\[
\left|\min_tF_{i,\delta}(x,t)-C^i(x)\right|
\le L_i\delta_i.
\]
Indeed, \(F_{i,\delta}\) represents CVaR of
\(J^i(x+\delta_i\nu,\xi)\) over the joint random pair
\((\nu,\xi)\). Couple this loss to \(J^i(x,\xi)\). Their difference
is at most \(L_i\delta_i\) almost surely, so CVaR monotonicity and
translation invariance give the claim.

For the centralized single-agent case, this gives a complete
finite-time statement. Let \(x^\star\) minimize \(C\), set
\(z_\delta=(1-\delta/r)x^\star\), and choose
\(t^\star_\delta\in\arg\min_t F_\delta(z_\delta,t)\). Let
\(H_T=\sum_{k<T}\eta_k\) and return the step-size-weighted average
\(\bar x_T\). The projection recursion and convexity give

\[
\mathbb E[C(\bar x_T)-C(x^\star)]
\le \frac{\|x_0-z_\delta\|^2+|t_0-t^\star_\delta|^2}{2H_T}
+\frac{1}{2H_T}\sum_{k<T}\eta_k^2
\mathbb E\!\left[
\frac{4d^2U^2p_k}{\alpha^2\delta^2}
+1-\frac{2p_k}{\alpha}+\frac{p_k}{\alpha^2}
\right]
+L\delta
\left(2+\frac{\|x^\star\|}{r}\right).
\]

Here the current threshold is measurable before the fresh direction
and loss, and \(\bar x_T\) is an average of unperturbed decisions.
The first numerator is prediction sensitive if \(t_0\) is initialized
from clipped advice about the smoothed upper-tail quantile at
\(z_\delta\). Its threshold coordinate is uniformly bounded by
\(4U^2\). This comparator target may differ from the unsmoothed
quantile at \(x^\star\) without an additional quantile-stability
assumption. The \(p_k\) terms are prediction sensitive only with
calibration along the trajectory. This is an additive gap guarantee,
matching P's metric; Q's competitive-ratio definitions do not
transfer literally.

The projected stochastic subgradient recursion over \(x\) and the
local thresholds, with P's disagreement lemma (lines 529--538),
should give an ergodic true-CVaR gap bounded by initial distance,
weighted second moments, network disagreement, and
\(O(\max_i L_i\delta_i)\), with one loss query per agent per
iteration. Clipping a predicted \(t_0^i\) to \([-U_i,U_i]\) gives
a prediction-independent initial-distance cap \(4U_i^2\).
This is a proof outline, not a completed distributed theorem.
The network comparison must use the fixed-threshold Lipschitz bound
\(|F_{i,\delta}(x,t)-F_{i,\delta}(x',t)|\le
L_i\|x-x'\|/\alpha_i\), because each agent carries its own
\(t_k^i\). The sharper \(L_i\) bound for optimized CVaR does not
apply before minimizing over \(t\). Hence a distributed rate can
have additional risk-level dependence in its disagreement term;
the single-agent query exponents cannot be transferred unchanged.

## Publication assessment

Soma and Yoshida already use joint decision and threshold
CVaR stochastic gradient updates in a first-order setting:
https://arxiv.org/abs/2002.05826.
Wang, Shen, and Zavlanos analyze sampled one-point CVaR estimates
in online games:
https://proceedings.mlr.press/v162/wang22w.html.

The possible contribution is a time-varying-network, one-query
zeroth-order theorem removing P's finite-batch residual, with a
conditional tail-occupancy variance improvement from quantile advice.
A paper needs a complete distributed recursion, a causal mechanism
maintaining threshold calibration, comparisons under matched query
budgets and risk levels, and experiments. Accurate one-shot quantile
advice has no demonstrated asymptotic query-complexity gain.
