# Ada: repaired payments and the economic meaning of a CVaR surrogate

## Assessment and revised question

The abstract-selected proposal cannot be carried out literally. Q's strict uniqueness LMI conflicts with its
implementation constraints, and its printed example payment can violate individual rationality even for
deterministic strongly concave valuations. P supplies an estimator of a different, fixed objective when batch sizes
remain finite. The useful question is therefore: can a corrected payment mechanism implement that surrogate
exactly, with quantitative guarantees for actual risk preferences, without requiring strong monotonicity in the
economically undetermined common-price direction?

The concrete results below are algebraic counterexamples, a payment correction preserving all best responses, and a
perturbation theorem. Emmy is investigating the separate weighted monotonicity and learning certificate. A complete
theorem for Q's original VS-PBR iteration is not established here.

## Source anchors

- Q, lines 126-137, Assumption `valuation_function_assumption`: twice differentiable, strongly concave expected
  valuations, normalized at zero. Its following remark explicitly distinguishes curvature of the expectation from
  samplewise curvature.
- Q, lines 202-216, `existence_uniqueness_cond_eq`: strict negative definiteness of the symmetric pseudogradient
  majorant.
- Q, lines 244-255, `nash_implementation_cond_eq`: price-block row sums vanish.
- Q, lines 387-442, `IR_cond_eq` and `eq40`: IR certificate and claimed feasible payment.
- Q, lines 449-481: the printed reduced tax, the proximal best-response map, and separately assumed
  nonexpansiveness.
- Q, lines 509-520 and 600-619: sampling-error lemma and the mean-square convergence argument.
- P, lines 328-342: upper-tail CVaR defined through threshold minimization; its risk parameter is a tail
  probability.
- P, lines 375-445: ball smoothing, sphere estimator, fresh independent empirical batches.
- P, lines 495-511: samplewise convexity, bounded losses, and Lipschitz continuity.
- P, lines 866-879: fixed deterministic expected empirical smoothed surrogate and its unbiased gradient identity.
- P, lines 919-947: limiting true-objective gap obtained through gradient mismatch.
- P, lines 1292-1314: integrated DKW bound for empirical CVaR value error.

## Q's strict certificate is infeasible

For any nonzero resource vector \(v\), take the message-space direction

\[
h=\operatorname{col}((0,v),\ldots,(0,v)).
\]

Q's condition P2(i) gives \(\sum_m A^n_{nm}=0\) for each player. From its displayed definition of \(\Psi\),

\[
h^\top(\Psi+\Psi^\top)h
=-2\sum_n v^\top\left(\sum_m A^n_{nm}\right)v=0.
\]

P1(ii) instead requires this expression to be at most \(-\upsilon N\|v\|^2<0\). The contradiction is independent of
satisfaction functions and of CVaR. It disproves feasibility of the simultaneous sufficient conditions, not
existence of every possible implementing mechanism. Emmy independently obtained this argument in ledger entry 1.

## Explicit IR failure and an exact repair

Use \(\gamma\) for the scale called \(\alpha\) in Q's payment, to distinguish it from CVaR tail probability. Let

\[
b_N=\frac{N^2-N+1}{(N-1)^2},\qquad
\bar p_{-n}^{\rm av}=\frac{1}{N-1}\sum_{m\ne n}p_m.
\]

At uniform prices \(p_n=p\), with \(p^\top(\sum_nx_n-c)=0\), direct collection of Q's `eq40` gives

\[
t_n^Q=\gamma b_Np^\top(x_n-c/N).
\]

Also the printed coefficients satisfy \(\sum_m a_m^n=\gamma c/[N(N-1)]\), contrary to P4(ii) when capacity is
positive.

For a concrete counterexample take \(N=3\), one resource, \(\gamma=c=1\), and \(\mathcal X_n=[0,1]\). Set

\[
V_1(x)=10x-x^2/2,\qquad V_2(x)=V_3(x)=0.1x-x^2/2.
\]

At \(x=(1,0,0)\), \(p=(9,9,9)\), each player's cost Hessian with respect to its own allocation and price is

\[
\begin{pmatrix}1&-1/2\\-1/2&1\end{pmatrix}\succ0.
\]

The own-price derivatives vanish, the first allocation derivative vanishes, and the other allocation cost
derivatives equal \(8.9>0\) at their lower bound. These are sufficient KKT conditions for an NE. But
\(t_1^Q=10.5\), while \(V_1(1)=9.5\), so the first player's equilibrium utility is \(-1\). This also satisfies Q's
valuation normalization and curvature assumptions.

Define a corrected payment

\[
t_n^{\rm new}=t_n^Q+r_n,\qquad
r_n=\gamma(b_N-1)(\bar p_{-n}^{\rm av})^\top
\left(\sum_{m\ne n}x_m-\frac{N-1}{N}c\right).
\]

The adjustment depends only on opponents' messages, so NE, exact PBR maps, and optimization subproblems are
unchanged. At uniform complementary prices it gives

\[
t_n^{\rm new}=\lambda^\top(x_n-c/N),\qquad \lambda=\gamma p.
\]

Thus payments sum to zero. Suppose \(0\in\mathcal X_n\), normalized concave valuations admit planner KKT
conditions, and the equilibrium allocation solves that planner problem. A supporting supergradient \(g_n\) and the
normal-cone KKT relation give

\[
V_n(x_n)-V_n(0)\ge g_n^\top x_n\ge\lambda^\top x_n.
\]

Consequently

\[
V_n(x_n)-t_n^{\rm new}\ge\lambda^\top c/N\ge0.
\]

This uses subgradients and remains valid for nonsmooth risk valuations. It does not establish equilibrium
implementation or learning convergence by itself; it repairs transfers whenever those properties are supplied. It
also replaces, rather than satisfies, Q's original sufficient coefficient constraints.

## P's fixed-batch objective admits a sharper value bound

Write \(\beta_n\in(0,1)\) for tail probability, and set

\[
C_n(x)=\operatorname{CVaR}_{\beta_n}[J_n(x,\xi)],\qquad
H_{n,s}(x)=\mathbb E[\widehat C_{n,s}(x)].
\]

Assume P's boundedness \(|J_n|\le U_n\), samplewise convexity, Lipschitz constant \(L_n\), and fresh iid batches
from a distribution independent of the query point. Define

\[
e_n=\frac{U_n}{\beta_n}\sqrt{\frac{2\pi}{s_n}}.
\]

The threshold representation and interchange inequality for an infimum give \(H_{n,s}(x)\le C_n(x)\). P's
integrated DKW calculation gives \(\mathbb E|\widehat C_{n,s}(x)-C_n(x)|\le e_n\). Hence, for every deterministic
query point,

\[
C_n(x)-e_n\le H_{n,s}(x)\le C_n(x).
\]

This is a bound between deterministic functions with constants uniform in the query point. It does not require a
bound on the expectation of a supremum of random empirical errors, nor a covering-number argument.

Now let

\[
\widetilde C_n(x)=\mathbb E_{v\sim\operatorname{Unif}(\mathbb B)}
H_{n,s}(x+\delta_nv).
\]

On any domain where all these queries are allowed, convexity and the centered perturbation imply
\(C_{n,\delta}(x)\ge C_n(x)\), while Lipschitz continuity gives \(C_{n,\delta}(x)\le C_n(x)+L_n\delta_n\).
Combining these facts proves

\[
-e_n\le\widetilde C_n(x)-C_n(x)\le L_n\delta_n.
\tag{A}
\]

Thus the oscillation of the deterministic surrogate error is at most \(w_n=e_n+L_n\delta_n\). This is sharper than
deriving a bound from P's gradient mismatch, which introduces an inverse smoothing radius.

### Consequence for P itself

P proves almost-sure convergence to a minimizer of the average \(\widetilde C_n\) on its contracted domain
\(\mathcal X_\delta\). Comparing objective values in (A) at that minimizer and at
\(z_\delta=(1-\delta_{\max}/r)x^*\), using P's scaled-comparator bound, gives

\[
\mathcal C(x_\infty)-\mathcal C(x^*)
\le\frac1m\sum_{n=1}^m(e_n+L_n\delta_n)
+\frac{D_xL_{\max}\delta_{\max}}{r}.
\tag{B}
\]

Boundedness transfers the same bound to the limiting expected gap. For fixed batches this replaces the stated
asymptotic order by \(O(\delta_{\max}+s_{\min}^{-1/2})\). It does not remove the inverse-radius variance penalty
from finite-time optimization.

## Economic perturbation theorem

For this paragraph assume perturbations are permitted on a neighborhood of each entire local strategy set,
including zero. This is an extra oracle assumption relative to Q. Alternatively a boundary-safe smoothing
construction must be analyzed separately. Q's nonnegative and possibly lower-dimensional allocation sets do not
satisfy P's ambient origin-centered ball assumption.

Normalize true and surrogate risk valuations as

\[
V_n(x)=C_n(0)-C_n(x),\qquad
\widetilde V_n(x)=\widetilde C_n(0)-\widetilde C_n(x).
\]

For random satisfaction \(\psi_n\), the appropriate loss is \(J_n=-\psi_n\). Cash translation invariance permits
deterministic taxes to be placed outside the risk measure. A zero expected satisfaction at the outside action does
not imply zero CVaR; this normalization or a specified risk-adjusted outside option is necessary.

Suppose a corrected mechanism has an NE \(\widetilde s\) implementing a minimizer \(\widetilde x\) of
\(\sum_n\widetilde C_n\) over the original coupled feasible set, and is budget balanced and individually rational
for \(\widetilde V_n\). Then (A) yields:

- Exact budget balance at \(\widetilde s\), because transfers depend on messages, not which valuations we use to
  assess them.
- Actual unilateral improvement is at most \(w_n\) for player \(n\), because taxes cancel in the comparison between
  true and surrogate payoff differences.
- Actual normalized utility is at least \(-w_n\), since \(|V_n(x)-\widetilde V_n(x)|\le w_n\).
- Actual welfare loss is at most \(\sum_nw_n\), since \(\widetilde x\) minimizes the surrogate objective.

If \(\sum_n C_n\) is \(m_0\)-strongly convex on the feasible set, its unique minimizer \(x^*\) further satisfies

\[
\|\widetilde x-x^*\|^2\le\frac{2}{m_0}\sum_nw_n.
\tag{C}
\]

These are properties of a surrogate equilibrium, not a theorem that P's distributed consensus method computes an NE
of Q's game. P's estimator can be used inside an optimization method for each best response, with analytic payment
derivatives, but that additional algorithm must be specified.

Samplewise strong convexity of \(J_n\) is sufficient for strong convexity of its CVaR, empirical CVaR, and these
expected smoothed surrogates: subtract the common quadratic, then apply convexity and cash translation invariance.
Strong convexity of the expected loss alone, as allowed in Q, is insufficient.

## Conditional bridge to inexact PBR

This subsection is a conditional error-propagation result. It does not repair Q's
nonexpansiveness assumption. I independently checked Emmy's ledger entry 10:
for three players with unit curvature and tax scale, an interior consensus-price
perturbation of the correctly differentiated PBR has squared amplification
\(1+1/(2D^2)>1\), where \(D=(\mu+1)^2-1/4\). Increasing the proximal parameter
does not restore Euclidean nonexpansiveness in that example. Exact rational checks
are in `ada/check_algebra.py`.

Suppose, separately, that the exact true-risk PBR map is nonexpansive on a compact message domain, has a nonempty
fixed-point set, and every local true proximal objective is \(a_0\)-strongly convex. If an inner method returns a
feasible point with expected surrogate proximal objective gap at most \(h_k\), (A) gives

\[
\mathbb E\|\widehat T_{n,k}(s)-T_n(s)\|^2
\le\frac{2}{a_0}(h_k+w_{n,k}).
\tag{D}
\]

Proof: surrogate suboptimality plus the oscillation bound gives true proximal objective suboptimality at most
\(h_k+w_{n,k}\); strong convexity gives (D). This avoids any smoothness assumption on the true CVaR.

If \(\sum_k\sqrt{h_k+\sum_nw_{n,k}}<\infty\), the expected response errors are summable. They are therefore
summable almost surely. The averaged nonexpansive iteration has the usual summable-error quasi-Fejer argument:
distances to fixed points converge and its residual vanishes; finite-dimensional compactness identifies a
fixed-point limit. Boundedness gives mean-square convergence to that possibly random limit. A unique equilibrium
would make the limit deterministic, but uniqueness cannot be imported from Q's infeasible LMI.

For example, \(\delta_{n,k}=O((k+1)^{-3})\), \(s_{n,k}\ge c(k+1)^6\), and \(h_k=O((k+1)^{-3})\) suffice. This is a
sufficient schedule, not an efficient complexity result. P's gradient estimator can address the inner surrogate
problem, but its magnitude grows inversely with the smoothing radius; fixed inner effort does not meet the required
accuracy. Nonexpansiveness of the outer map and boundary-safe queries remain unproved for the proposed repaired
game.

Emmy's more promising replacement, ledger entry 11, uses the resolvent of the
weighted monotone game operator, rather than the simultaneous PBR map. Weighting
the price block by \((N-1)/N\) cancels consensus cross-coupling. I checked the
remaining disagreement-block Schur condition:

\[
m>\frac{\gamma(2N-1)^2}{4(N-1)^4}.
\]

This gives coercivity in allocations and price disagreement, but not common
prices. For a fixed surrogate, each resolvent subproblem becomes strongly
monotone and has an unbiased bounded oracle from P plus analytic payment
derivatives. Projected stochastic approximation can then give inner mean-square
error of order \(1/T_k\). Taking \(T_k\) faster than a quadratic power of the
outer index makes norm errors summable and supports inexact proximal-point
convergence. This changes Q's algorithm and supplies a credible route to the
fixed-surrogate equilibrium assumed in the economic theorem. A full statement
must include the normal cones, price cap, and the oracle-neighborhood assumption.

## CVaR can destroy price uniqueness at interior allocations

Take three players, unit payment scale, \(\mathcal X_n=[0,1]\), capacity \(3/2\),
tail probability \(1/2\), and equiprobable signs \(Z=\pm1\). Set

\[
J_n(x,Z)=x^2-3x+Z(x-1/2).
\]

Every sample is strongly convex with modulus two. Its CVaR is

\[
C_n(x)=x^2-3x+|x-1/2|.
\]

The unique planner allocation is \(x_n=1/2\). At that point
\(\partial C_n(1/2)=[-3,-1]\), so every multiplier \(\lambda\in[1,3]\)
satisfies planner KKT. The own joint cost is convex, and every uniform price
\(p_n=\lambda\) with that multiplier satisfies the game KKT conditions.
Thus all allocation choices are interior, yet the true-risk mechanism has a
continuum of equilibrium common prices. This is a specific effect of a CVaR
kink, beyond the boundary-induced multiplier nonuniqueness already possible
in Q. Normalizing valuations at zero has no effect on this conclusion.

## Why finite sampling is an economic change

For a batch containing a single sample, empirical CVaR equals that sample for every tail probability. Thus its
expectation is the ordinary mean loss, regardless of the nominal risk level. Consider \(x\in[0,1]\), tail
probability \(0.2\), and

\[
J(x,Z)=x^2-x+4Zx,\qquad \mathbb P(Z=1)=0.1.
\]

The true CVaR is \(C(x)=x^2+x\), minimized at zero. The expected one-sample surrogate is \(H_1(x)=x^2-0.6x\),
minimized at \(0.3\). Its actual CVaR loss is \(0.39\). For sufficiently small ball smoothing, the quadratic
surrogate only gains a constant near its interior minimizer, so the discrepancy persists. This bounded, samplewise
strongly convex example shows why fixed-batch convergence alone does not implement the intended risk preference.

## Prior-work check and publication threshold

Queries run: `empirical CVaR sample average approximation expected bias uniform convergence stochastic
optimization`; `risk averse games CVaR Nash equilibrium zeroth order bandit finite sample`.

The search found substantial adjacent work, so a generic CVaR-game or sampled-equilibrium claim is not a credible
novelty claim:

- Wang, Shen, and Zavlanos, [Risk-Averse No-Regret Learning in Online Convex
  Games](https://proceedings.mlr.press/v162/wang22w.html), already use one-point CVaR gradient estimation with
  bandit feedback and prove regret guarantees.
- Wang, Shen, Zavlanos, and Johansson, [Learning of Nash Equilibria in Risk-Averse
  Games](https://arxiv.org/abs/2403.10399), establish a first-order CVaR-game learning result under strong
  monotonicity.
- [Sample average approximation of conditional value-at-risk based variational
  inequalities](https://link.springer.com/article/10.1007/s11590-023-01996-9) studies consistency and exponential
  convergence of SAA equilibrium approximations, including routing applications.

I checked these primary landing pages and abstracts, not their complete proofs. The narrower candidate contribution
is a corrected quadratic mechanism with exact transfer guarantees and an explicit surrogate-to-actual welfare and
incentive theorem, supported by a learning proof that handles the common-price degeneracy. Bound (B) is a useful
additional correction to P, but by itself appears too short and standard a perturbation argument to justify a
substantial new paper. A complete algorithmic certificate, boundary treatment, price-identification assumptions,
and comparison against the closest full papers were unresolved at the initial synthesis.
The continuation below resolves the first two under explicit assumptions.

## Continuation: feasible queries without removing the outside option

After reading Emmy's complete proof in ledger entry 17, I independently checked the
boxed-equilibrium and inner-iteration arguments. Comparing any boxed equilibrium
to a planner KKT equilibrium contained in the box forces equal allocations and
zero price disagreement by the weighted coercivity inequality. Hence capacity is
already feasible before invoking the boxed price stationarity conditions. Slack
resources force zero price; binding resources allow a capped common multiplier.
Thus no strict interior assumption on the reference price is needed. The inner
mean-square recurrence and summable outer error argument are valid for fixed
surrogate parameters. This supplies a complete conservative convergence
certificate for the changed learner, conditional on its stated assumptions.

The remaining boundary issue admits a direct repair using P's smoothing identity
and a chain rule. Suppress the player index. Assume a known relative interior ball
\(a+r\mathbb B\subset X\), where the ball lies in the affine hull of the compact
convex local set \(X\). Work in orthonormal coordinates in this hull, of dimension
\(d\). Since \(0\in X\), the hull is a linear subspace. Singleton sets require no
allocation oracle and can be handled separately. For
\(0<\varepsilon<1\) and \(0<\delta<\varepsilon r\), define

\[
A_\varepsilon(x)=(1-\varepsilon)x+\varepsilon a,
\qquad q(x,v)=A_\varepsilon(x)+\delta v.
\]

Every query with \(x\in X\) and \(\|v\|\le1\) belongs to \(X\), because

\[
q(x,v)=(1-\varepsilon)x
+\varepsilon\left(a+\frac{\delta}{\varepsilon}v\right)
\in X.
\]

Define the deterministic surrogate on the original decision set by

\[
K(x)=\mathbb E_{v\sim\operatorname{Unif}(\mathbb B),\xi^{1:s}}
\widehat C_s(q(x,v)).
\]

The strict radius inequality leaves a uniform interior query margin. The same
formula is defined for decision points in a relative neighborhood of \(X\),
although every loss query still belongs to \(X\). P's sphere identity and the
affine chain rule give

\[
\widehat g_K(x)
=(1-\varepsilon)\frac{d}{\delta}
\widehat C_s(q(x,u))u,
\qquad
\mathbb E[\widehat g_K(x)\mid x]=\nabla K(x),
\qquad
\|\widehat g_K(x)\|\le(1-\varepsilon)\frac{dU}{\delta}.
\tag{E}
\]

The gradient and perturbations are relative to the local hull; the gradient can
be lifted to the resource space by its orthonormal basis. Normal cones absorb
orthogonal components in the equilibrium conditions. This modifies the oracle
queried by the learner while keeping the decision set unchanged.

If every sample loss is \(m\)-strongly convex on \(X\), then \(K\) is
\(m(1-\varepsilon)^2\)-strongly convex: the affine query map scales differences
by \(1-\varepsilon\), and empirical CVaR, expectation, and smoothing preserve
the resulting common curvature. Emmy's implementation and learning proofs apply
provided

\[
\min_n m_n(1-\varepsilon_n)^2
>\frac{\gamma(2N-1)^2}{4(N-1)^4}.
\tag{F}
\]

This can be met by sufficiently small contractions whenever the original
inequality has strict slack. With three players and \(m_n=\gamma\), any common
\(\varepsilon<3/8\) suffices.

Let \(R=\sup_{x\in X}\|x-a\|\) and retain the value-error constant \(e\) from
(A). The earlier one-sided bound applied at \(A_\varepsilon(x)\), followed by
Lipschitz continuity, gives

\[
-e-L\varepsilon R\le K(x)-C(x)
\le L\varepsilon R+L\delta.
\tag{G}
\]

Therefore the surrogate error has oscillation at most

\[
w^{\rm feasible}=e+2L\varepsilon R+L\delta.
\tag{H}
\]

Normalize the valuation as \(K(0)-K(x)\). Decision zero remains feasible and
normalized even though the oracle estimates this baseline using interior loss
queries. All economic perturbation conclusions above hold with
\(w_n^{\rm feasible}\) replacing \(w_n\): exact equilibrium budget balance,
exact surrogate IR, actual unilateral regret and IR shortfall bounded by the
local oscillation, welfare loss bounded by the sum, and the corresponding
strong-convexity allocation error bound. Choosing
\(\delta=\varepsilon r/2\) gives error order
\(O(s^{-1/2}+\varepsilon)\), with deteriorating oracle variance as
\(\varepsilon\) decreases.

This requires local knowledge of an interior point, an inradius, and affine-hull
coordinates, as well as fresh loss samples at arbitrary locally feasible query
points. It requires no losses outside the local feasible sets. If queries must
themselves satisfy a joint capacity constraint, or if only the realized allocation
can be observed, this oracle model requires additional coordination or a different
analysis. The contraction idea is elementary and is not asserted to be a new
smoothing method. Its role here is to preserve the outside option needed by the
corrected mechanism while using P's value oracle.

The current supported contribution is a corrected surrogate mechanism, feasible
local queries, explicit actual-risk economic error bounds, and a conservative
mean-square allocation learner. Outstanding publication questions are the closest
full-literature comparison and efficient total oracle complexity. Exact
population-risk learning with changing parameters and convergence of Q's original
VS-PBR remain unproved. Unique prices are unnecessary for this result and fail
in the interior CVaR example above.
