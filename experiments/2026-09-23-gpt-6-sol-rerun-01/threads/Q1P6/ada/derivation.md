# Comparison-derived potentials as control variates

## Scope and source passages

Q defines consistency, robustness, and smoothness against an algorithmic
objective and an offline benchmark (Q, lines 298–344). Q also asks that
prediction calls be priced (Q, lines 1242–1259). P uses an LMM to compare
active agents, fits Bradley–Terry scores, and applies their softmax as a
potential (P, lines 281–349). P's statistical proposition estimates an LMM
latent preference vector (P, lines 358–378), while its Shapley interpretation
assumes that vector equals the true Shapley vector (P, lines 380–389).

## Exact cancellation

For one agent, write the scalar coordinate of P's potential as
\(\psi_t\), and assume the same realized \(\psi_t\) is used on the
incoming and outgoing transitions. For an episode ending at \(T\),

\[
G_t^{\mathrm{shape}}
=\sum_{u=t}^{T-1}\gamma^{u-t}
\left[r_u+\rho(\gamma\psi_{u+1}-\psi_u)\right]
=G_t-\rho\psi_t+\rho\gamma^{T-t}\psi_T.
\]

P sets terminal \(\psi_T=0\), so the last term vanishes. At a fixed
initial condition, the shaped and original total returns differ only by
the pre-action quantity \(-\rho\psi_0\), for any comparison accuracy.
Consequently, exact optimization of the shaped objective gives no
nontrivial comparison-error curve for optimal return. This statement
requires terminal treatment and consistent reuse of each realized
potential. A nonterminal rollout cut with an omitted boundary term does
not satisfy it.

The same cancellation applies to exact temporal-difference advantages.
If an exact critic represents
\(V_t^{\mathrm{shape}}=V_t-\rho\psi_t\), then

\[
\delta_t^{\mathrm{shape}}
=r_t+\rho(\gamma\psi_{t+1}-\psi_t)
+\gamma V_{t+1}^{\mathrm{shape}}-V_t^{\mathrm{shape}}
=r_t+\gamma V_{t+1}-V_t=\delta_t.
\]

Thus GAE built from exact critics is identical. P actually trains with
MAPPO and GAE (P, lines 778–816), so an explanation of its empirical
gain must address finite critic fit, representation, optimizer dynamics,
or other implementation effects.

## A finite-sample target

Consider a likelihood-ratio gradient term at pre-action history \(h\):
\(Z=\nabla\log\pi(A\mid h)\), with original return-to-go \(G\).
Assume an LMM query is completed before \(A\) is sampled and its output
does not depend on \(A\). Then any baseline \(b(h)\) gives
\(\mathbb E[Z(G-b)\mid h]=\mathbb E[ZG\mid h]\).
If \(W(h)=\mathbb E[\|Z\|^2\mid h]>0\), the baseline minimizing the
conditional second moment is

\[
b^*(h)=\frac{\mathbb E[\|Z\|^2G\mid h]}{W(h)},\qquad
M_h(b)-M_h(b^*)=W(h)(b-b^*)^2,
\]

where \(M_h(b)=\mathbb E[\|Z\|^2(G-b)^2\mid h]\). P's potential is
the baseline \(b=\rho\psi_i(h)\). The identity controls a single
gradient term's second moment, not the full trajectory-gradient variance
or a MAPPO convergence rate. The query output may be random; the same
identity holds after conditioning on it, provided the policy action is
sampled afterward and the score identity remains valid.

An error budget can separate statistical aggregation error from semantic
mismatch. Let \(c^*\) be the LMM's latent scores, let
\(\psi^*=\operatorname{softmax}(c^*)\), and let \(\hat\psi\) use an
estimated score. Since softmax is \(1/2\)-Lipschitz in Euclidean norm,

\[
\|\hat\psi-\psi^*\|_2\leq\tfrac12\|\hat c-c^*\|_2.
\]

For a single coordinate, the baseline error obeys

\[
(\rho\hat\psi_i-b^*)^2
\leq \tfrac{\rho^2}{2}\|\hat c-c^*\|_2^2
+2(\rho\psi_i^*-b^*)^2.
\]

The first term can decrease with valid, repeated comparator samples.
The second remains even if the LMM's ranking is recovered perfectly or
equals a Shapley ranking. Neither ranking accuracy nor Shapley alignment
implies closeness to the variance-minimizing baseline.

For query count \(K\) and per-query cost \(\kappa\), a concrete objective
is the expected gradient second moment plus \(\kappa K\). Under a
fixed pre-action history and fixed target \(b^*\), another query pays
only if its expected reduction in
\(W(h)(\rho\hat\psi_{i,K}-b^*)^2\) exceeds \(\kappa\).
The comparison error must be evaluated against this downstream target,
not just agreement with an ordinal label. P's experiments report both
more successful learning with extra queries (P, lines 540–562) and
roughly 30 hours versus 16 hours for 50 million steps compared with
MAPPO (P, lines 778–793), making the trade-off experimentally testable.

## Constraints on a publication claim

This is a candidate analysis and experiment, not an established MAPPO
theorem. A strong study would derive a bound for a specified approximate
critic or optimizer, then test query policies at equal wall-clock budget.
It would measure baseline error or gradient second moment as well as
ordinal accuracy and success rate. The oracle model must say whether
repeated calls are independent and how score bias changes across states.
P's connected-graph condition alone does not ensure a finite unregularized
Bradley–Terry estimate for separated comparisons (P, lines 313–329,
363–378), so a regularized or bounded estimator is needed before using
its stated rate in this argument.

The control-variate and optimal-baseline facts are prior work, not new
theorems: [Greensmith et al. (2004)](https://jmlr.csail.mit.edu/papers/volume5/greensmith04a/greensmith04a.pdf)
derive optimal baselines and gradient-error bounds. Multi-agent potential
shaping and invariant policy gradients also appear in
[Li et al. (2022)](https://proceedings.mlr.press/v162/li22w/li22w.pdf).
Any publication contribution here must therefore come from the
comparison-to-optimization interface, a correct cost-aware query policy,
or a validated approximate-MAPPO mechanism. The two identities above
alone are insufficient.
