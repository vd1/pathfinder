# Risk-adjusted implementation versus surrogate learning

## Correct risk functional

P defines upper-tail CVaR for losses. For Q's stochastic satisfaction, the corresponding risk-averse valuation is the lower-tail functional
\[
R_n(x_n)=-\operatorname{CVaR}_{\beta_n}(-\psi_n(x_n,\xi_n)).
\]
Since coherent CVaR is translation equivariant and Q's payment is deterministic conditional on the message profile,
\[
-\operatorname{CVaR}_{\beta_n}(-\psi_n(x_n,\xi_n)+t_n(s))
=R_n(x_n)-t_n(s).
\]
Thus risk should be applied to net utility or satisfaction consistently. Applying P's upper-tail loss CVaR directly to satisfaction would optimize the favorable tail and is the wrong sign.

## Exact mechanism layer

Q's implementation proof compares the planner and player optimality conditions. Its essential object is the valuation, not the expectation representation. Replace \(V_n\) by \(R_n\). If \(R_n\) is strongly concave and upper semicontinuous, the planner has a unique allocation. Generalized KKT conditions can use supergradients, so differentiability is not essential to the price-alignment argument. The quadratic payment still supplies the same common-price and complementarity equations. Budget balance is an algebraic calculation at that common-price equilibrium and does not depend on smoothness.

A transparent sufficient primitive condition is that every sample satisfaction \(\psi_n(\cdot,\xi_n)\) is uniformly strongly concave. Via the risk-envelope representation, \(R_n\) is the infimum over admissible probability reweightings of expected satisfaction. Every reweighted expectation has the same strong-concavity modulus, and their infimum preserves it. Q assumes only that \(\mathbb E[\psi_n]\) is strongly concave, which is not sufficient to infer this property for \(R_n\).

Exact individual rationality also needs risk-normalized nonparticipation, such as \(\psi_n(0,\xi_n)=0\) almost surely, hence \(R_n(0)=0\). Q's weaker condition \(\mathbb E[\psi_n(0,\xi_n)]=0\) does not imply \(R_n(0)=0\).

Q's original expected-value assumptions do not transfer to CVaR. On \([-1,1]\), let two equiprobable satisfaction samples be \(\psi(x,1)=-3\) and \(\psi(x,2)=3-2x^2\). Then \(V(x)=-x^2\) is strongly concave and \(V(0)=0\), while at tail probability \(1/2\), \(-\operatorname{CVaR}_{1/2}(-\psi(x,\xi))=-3\) is constant. Thus the central obstruction is loss of curvature, not the CVaR kink alone. Uniform samplewise strong concavity is one sufficient repair; adding a deterministic quadratic regularizer is another, but the latter changes preferences and welfare.

## Which social risk objective is implemented?

There are two distinct risk-aware planner objectives. The separable objective compatible with Q is
\[
\sum_n -\operatorname{CVaR}_{\alpha}(-\psi_n(x_n,\xi_n)).
\]
If social risk instead means tail risk of total loss, the objective is
\[
-\operatorname{CVaR}_{\alpha}\left(-\sum_n\psi_n(x_n,\xi_n)\right).
\]
They are generally unequal. P explicitly records CVaR subadditivity and calls the difference between the sum of local CVaRs and CVaR of the sum a diversification price. The second objective depends on the joint law and is generally nonseparable, so Q's planner KKT condition no longer contains only the private marginal valuation of agent \(n\). Consequently, replacing each \(V_n\) by an individual CVaR can at best implement the first objective. It does not implement aggregate tail welfare except in special dependence cases.

This is an economic target mismatch even before smoothing or sampling. A mechanism for aggregate CVaR would need to internalize a distribution-dependent cross-agent risk externality, plausibly requiring joint tail samples or additional messages. Q's fixed deterministic quadratic payment family has no demonstrated way to encode that arbitrary joint-law term while valuations remain private. P's statement that equality holds if and only if losses move entirely in tandem is stronger than needed here and should not be inherited without checking; the subadditivity inequality alone establishes the wedge.

## Learning layer and target mismatch

Q's Algorithm 1 computes a sample-average proximal best response, then applies a Krasnoselskij update to the game map. P's Algorithm 1 takes a projected gradient step for a consensus optimization problem. The nodes in P hold copies of a common decision, whereas Q's players control distinct allocation-price messages. P therefore supplies an estimator and error bounds, not a best-response theorem that can be inserted unchanged.

With fixed smoothing radius and fixed finite sample size, P proves convergence to an optimizer of an expected empirical-smoothed surrogate \(\widetilde C\), not to the true CVaR optimizer. Its true-objective residual has order
\[
\delta_{\max}+\frac{e_s}{\delta_{\min}}.
\]
Used in a game algorithm, the same estimator would define a surrogate game unless smoothing vanishes and sample sizes grow. If the exact game's optimality map is \(\nu\)-strongly monotone and the surrogate map differs uniformly by at most \(b\), the variational-inequality comparison gives the allocation-message bound
\[
\|\widetilde s^*-s^*\|\leq \frac{b}{\nu}.
\]
P's empirical gradient bound suggests a component of \(b\) proportional to \(e_s/\delta_{\min}\). Objective smoothing contributes an approximation error proportional to \(\delta_{\max}\), but converting that value error into a pointwise equilibrium bound requires either a gradient regularity assumption or a strong-convexity argument, typically producing a square-root dependence from a uniform value bound. This conversion is not proved by either paper.

At the exact equilibrium of the surrogate planner and surrogate game, Q's payment identities can still give exact budget balance because the identities are target-relative. Relative to the true CVaR game, allocation implementation is approximate. Individual rationality for true risk utility is also only approximate unless the valuation approximation is one-sided; a uniform valuation error \(\epsilon_n\) yields at best a participation loss controlled by a constant multiple of \(\epsilon_n\).

## Proposed publishable question

Can a quadratic, budget-balanced mechanism exactly implement the lower-tail-CVaR social optimum under nonsmooth strongly concave valuations, while a zeroth-order risk oracle learns an approximate equilibrium with an explicit mechanism-level deviation bound, and can smoothing and sample schedules be chosen so that the deviation vanishes?

The key result should separate economics from computation:

1. exact strong Nash implementation, budget balance, and individual rationality for the true lower-tail-CVaR game under primitive samplewise curvature and baseline assumptions;
2. a game-specific zeroth-order proximal or forward-backward algorithm, not P's consensus update verbatim;
3. finite-time or asymptotic bounds translating CVaR estimation and smoothing errors into equilibrium distance, welfare loss, and participation slack;
4. exact budget balance at a surrogate equilibrium, alongside approximate true allocation and true individual rationality.

This is stronger and more precise than asking whether all of Q's guarantees simply survive insertion of P's estimator. They do not share a compatible iteration, and fixed P parameters cannot yield exact true-CVaR implementation.

An arguably sharper publication question is whether one can design a privacy-preserving extension of Q that implements aggregate-CVaR welfare rather than the conservative sum of individual CVaRs, and quantify the unavoidable diversification wedge when only local zeroth-order CVaR oracles of P's kind are available. This exposes a target-identification problem that neither an exact game solver nor vanishing estimator bias resolves.
