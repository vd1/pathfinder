# Priced certification of a conditional-CVaR cycle decision

## Scope and provenance

The supplied Q is a survey. Its notation requires the probability space of a guarantee to be
declared (Q, lines 257-265); its discussion of distributional advice warns that a fixed-decision
risk bound does not automatically bound the selected optimizer (Q, lines 600-602); its additive
composition statement needs conditional component bounds and a shared benchmark (Q, lines
1035-1067); and its proposed augmented ratio charges a declared amount per predictor invocation (Q,
lines 1242-1258). Q does not supply an obedience-cycle theorem. The supplied P supplies the
state-independent action-reward cycle test, an expected-empirical CVaR reversal, and deterministic
value-error certificates (P, lines 16-18, 24-72). P explicitly leaves a realised-batch guarantee
open (P, line 92). The question is therefore narrowed to a finite-signal, one-type policy with
conditional loss risk as reduced-form utility. Its answer does not transfer to ex-ante CVaR of a
complete plan or to a general learning-augmented pipeline.

## A confidence certificate and its price

Fix finite signals \(S\), available actions \(B\), and a prescribed action \(a(s)\in B\) at every
signal. Assume a generative oracle can sample the conditional loss of each action, including
unplayed deviations. For every queried cell \((s,b)\), draw \(m\) independent samples from a fixed
conditional loss distribution \(L_{s,b}\in[0,H]\). Let \(\beta\in(0,1]\) be upper-tail mass,
\(N=|S||B|\), and

\[
U(b,s)=-\operatorname{CVaR}_{\beta}(L_{s,b}),\qquad \widehat
U(b,s)=-\operatorname{CVaR}_{\beta}(\widehat F_{s,b}).
\]

Here \(\widehat F_{s,b}\) is the empirical distribution of that cell's realised batch. The union
bound below does not require independence across cells.

The variational formula and the hinge-loss integral give

\[
\operatorname{CVaR}_{\beta}(F)
=\min_{t\in[0,H]}\left\{t+\frac{1}{\beta}\mathbb E_F(L-t)_+\right\}, \qquad
\left|\operatorname{CVaR}_{\beta}(F)-\operatorname{CVaR}_{\beta}(\widehat F)\right|
\leq\frac{H}{\beta}\|F-\widehat F\|_{\infty}.
\]

The Dvoretzky-Kiefer-Wolfowitz inequality and a union bound imply that, with probability at least
\(1-\delta\), every queried utility lies in its realised interval \([\widehat U-e_m,\widehat
U+e_m]\), where

\[
e_m=\frac{H}{\beta}\sqrt{\frac{\log(2N/\delta)}{2m}}.  \]

This concerns a realised batch. P's \(q_m=\mathbb E[\operatorname{CVaR}_{\beta}(\widehat F)]\) is
an expected surrogate and is not a confidence interval. Its gap from true risk is a deterministic
bias after the loss law and batch size are fixed; the realised error
\(\operatorname{CVaR}_{\beta}(\widehat F)-\operatorname{CVaR}_{\beta}(F)\) is random. P's one-draw
example has true risk \(2\), expected empirical risk \(1\), and safe risk \(3/2\) (P, line 43). The
sign of every true obedience cycle is a third object: an exact property of the unknown utility
array, not of either estimate alone.

There are two sound outputs on the simultaneous-coverage event. For a feasible certificate, define

\[
w(a,b)=\max_{s:a(s)=a} \{\widehat U(b,s)-\widehat U(a,s)+2e_m\}.
\]

Edges leave only actions that the policy prescribes. If this graph has no positive directed cycle,
solve the finite difference constraints \(r(a)-r(b)\geq w(a,b)\). The reported reward \(r\) supports
the prescribed policy for every utility array in the confidence box, hence for the true array on the
coverage event. For an infeasible certificate, exhibit a prescribed-action cycle
\(a_1,\ldots,a_K,a_{K+1}=a_1\) and signals \(s_i\) prescribing \(a_i\) with

\[
\widehat C+2Ke_m<0,\qquad \widehat C=\sum_{i=1}^{K}
\bigl(\widehat U(a_i,s_i)-\widehat U(a_{i+1},s_i)\bigr).
\]

Its true cycle is negative on the coverage event, so no state-independent supporting reward exists.
Otherwise the procedure abstains. The graph step is P's rectangular-error test instantiated with
sample-derived intervals; it is not a new graph theorem.

Let \(K_{\max}=|B|\). If all nontrivial simple true cycles are at least \(\gamma>0\), or some true
simple cycle is at most \(-\gamma\), the procedure gives the correct positive or negative
certificate whenever \(4K_{\max}e_m<\gamma\). A sufficient fixed batch size is

\[
m>\frac{8H^2K_{\max}^2}{\beta^2\gamma^2} \log\frac{2N}{\delta}.  \]

With an explicitly assumed charge \(\kappa\) per sampled loss, the sampling bill is \(\kappa Nm\),
plus graph computation. Q charges per predictor invocation; equating one invocation with one draw is
an additional model choice. If one invocation returns a whole batch, a batch-generation cost
function must instead be specified.

## Exact feasibility and the boundary obstruction

Use P's two-signal, swapped-action construction with risky loss \(L=2X\),
\(X\sim\operatorname{Bernoulli}(p)\), and safe loss \(1\). Each signal prescribes its risky action.
At tail mass \(\beta=1/2\), for \(p<1/2\),

\[
\operatorname{CVaR}_{1/2}(L)=4p,\qquad C(p)=2(1-4p).
\]

The policy is feasible at \(p_-=1/4-\varepsilon\) and infeasible at \(p_+=1/4+\varepsilon\), with
cycle magnitudes \(8\varepsilon\), for \(0<\varepsilon<1/8\). Both models give positive probability
to every finite risky-loss transcript. Thus a distribution-free finite-sample rule that must always
give the correct exact answer cannot emit either answer on this subfamily. This rules out pathwise
exact verification from finite samples, while leaving high-confidence certification with abstention
possible.

There is also an identification obstruction before sampling error enters. Suppose only on-policy
losses are logged. In the same swapped-action pattern, each prescribed action can have deterministic
loss \(3/2\), while each unplayed deviation has deterministic loss \(2\) in world A and \(1\) in
world B. The on-policy logs have the same law in both worlds, regardless of sample count. Yet the
cycle sum is \(+1\) in A and \(-1\) in B. Counterfactual sampling, action coverage with a valid
estimator, or structural identification is therefore necessary to certify this test from data. Such
exploration can have a decision cost beyond the nominal sample charge.

For a nonabstaining rule whose answer is correct with probability at least \(1-\delta\) under both
models, let \(T\) be its number of informative risky draws, including an adaptive stopping time with
finite expectation. The transcript chain rule for relative entropy and data processing give

\[
\mathbb E_{p_-}T\;\operatorname{kl}(p_-,p_+) \geq\operatorname{kl}(1-\delta,\delta).  \]

For fixed \(\delta<1/2\), the required bill diverges as \(\Omega(\kappa\varepsilon^{-2})\),
equivalently \(\Omega(\kappa\gamma^{-2})\) when \(\gamma=8\varepsilon\). There is no uniform
finite-cost high-confidence exact yes/no test without a promised margin. This is a threshold-testing
obstruction, not a lower bound for all CVaR estimation settings.

## Reward cost is a separate constraint

P's cycle test allows unrestricted state-independent rewards. Exact support need not be cheap. For
two actions, requirements \(r(a)-r(b)\geq M\) and \(r(b)-r(a)\geq-M-\gamma\), with \(\gamma>0\),
have a nonpositive cycle, but every nonnegative supporting reward has a maximum payment of at least
\(M\). A costed decision theorem must say whether rewards are resource costs, and may impose \(0\leq
r(a)\leq R\). The feasible certificate then solves the same confidence-robust difference constraints
jointly with these caps. If that finite linear system is feasible, its reward is both statistically
certified for true obedience and pathwise capped at \(R\). Failure of this robust test is still
abstention; it does not establish that the true utility array violates the budget. A
budget-infeasibility certificate requires an optimistic bound or another dual witness.

There is a local support-cost comparison. Let \(w^*(a,b)=\max_{s:a(s)=a}\{U(b,s)-U(a,s)\}\), let
\(n=|B|\), and suppose each nontrivial simple true cycle has average edge weight at most
\(-\gamma<0\). On the coverage event, each robust empirical edge satisfies \(w^*(a,b)\leq w(a,b)\leq
w^*(a,b)+4e_m\). If \(e_m<\gamma/4\), both graphs have no positive cycle. For nonnegative rewards,
the coordinatewise least solution of their difference constraints is the maximum path-weight
potential starting at each action, with an empty path of weight zero. A maximal path can be simple,
so it has at most \(n-1\) edges. Consequently, if \(R^*\) and \(R_m^*\) are the smallest possible
true and confidence-robust maximum reward caps, respectively, then

\[
R^*\leq R_m^*\leq
R^*+4(n-1)e_m.
\]

If rewards are paid once and count as resource cost, \(\kappa Nm+R^*+4(n-1)e_m\) is a
confidence-qualified additive bound on sample plus maximum reward cost. This is a local benchmark
against an oracle that knows the true risk array. It is not Q's system offline optimum.

Under this section's per-edge margin \(\gamma\), certification requires
\(m>m_{\min}=8H^2\log(2N/\delta)/(\beta^2\gamma^2)\). Write
\(A=4(n-1)(H/\beta)\sqrt{\log(2N/\delta)/2}\). The preceding bound is \(R^*+\kappa Nm+A m^{-1/2}\).
For \(\kappa>0\), its continuous cost-minimizing batch size under the certification constraint is
\(\max\{m_{\min},(A/(2\kappa N))^{2/3}\}\), rounded upward to a valid integer with a strict margin.
This optimizes a sufficient upper bound for uniform sampling. It does not establish optimal adaptive
sample complexity.

## What does and does not compose

The certificate has a sampling probability of failure \(\delta\), not a pathwise guarantee. To pass
it into Q's expected-cost objective, the model must include sample randomness, a specified action
when the procedure abstains, and a bound on cost when coverage fails. Let \(D\) be downstream cost,
including any reward payouts counted as resource cost. If \(D\leq B\) throughout the coverage event,
including the abstention branch, and \(D\leq M\) on every path, then

\[
\mathbb E[\kappa Nm+D]\leq\kappa Nm+B+\delta M.
\]

A strict cycle-margin promise can make the procedure issue a certificate throughout the coverage
event; otherwise the fallback cost must be included in \(B\). Its feasibility and cost require their
own argument. For a component selected after history \(\mathcal H\), the same coverage and cost
claims must hold conditionally on every reachable \(\mathcal H\): fresh conditionally independent
draws from the specified cell laws, or a confidence method valid for adaptive sampling, can supply
that premise. A marginal \(1-\delta\) statement for one fixed policy does not supply Q's conditional
component bound (Q, lines 1035-1065). A competitive ratio additionally needs a specified positive
common offline benchmark and the benchmark/interface relations in Q's composition propositions.
Without a failure-cost cap, confidence coverage alone gives no finite expected-cost bound.

Existing CVaR estimation and fixed-confidence best-arm work means the concentration step is prior
machinery, not publication novelty: [NeurIPS 2021 risk-arm
identification](https://proceedings.neurips.cc/paper/2021/file/d69c7ebb6a253532b266151eac6591af-Paper.pdf)
and [CVaR concentration with fixed-budget identification](https://arxiv.org/abs/1901.00997).
[Risk-conscious Bayesian persuasion](https://arxiv.org/html/2605.12094v1) also uses a positive
margin to pass from approximate to strict incentive compatibility in a different model. A
substantive next theorem would optimize priced, possibly adaptive sampling around the graph's
critical cycles, with a matching instance-dependent lower bound and a declared downstream loss cap
or fallback. The two supplied papers do not prove that theorem.
