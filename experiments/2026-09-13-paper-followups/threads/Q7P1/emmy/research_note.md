# A corrected risk-surrogate mechanism: obstructions, repair, and learning

Emmy, 13 September 2026. This note records a derivation from the supplied papers, cross-checked with Ada through
the ledger. It is a research result and publication lead, not a claim of established novelty.

## Assessment and changed question

The abstract-selected proposal cannot inherit Q's advertised guarantees. Its strict uniqueness LMI is
incompatible with its implementation equalities, its explicit tax can violate individual rationality, and its
Euclidean proximal-best-response assumption fails even in a simple interior quadratic example. These failures
occur before introducing CVaR.

The concrete replacement question is: can a corrected quadratic mechanism implement the welfare optimum of P's
fixed expected empirical-smoothed CVaR surrogate, with exact equilibrium budget balance, controlled
participation and welfare errors relative to true risk preferences, and a valid sampled-feedback equilibrium
algorithm?

There is a positive static answer under the assumptions below. An opponent-only rebate fixes individual
rationality, and a weighted monotonicity calculation establishes implementation at every equilibrium, with a
unique allocation but possibly multiple common prices. A nested proximal-point algorithm gives a conservative
constructive convergence result using P's oracle. This changes Q's algorithm; it does not prove that Q's VS-PBR
works for CVaR.

Ada develops the sharper economic perturbation bounds. The distinctive pairing is the separation between an
exactly implemented statistical surrogate and approximate incentives under true preferences. Generic CVaR game
learning and generic proximal equilibrium algorithms already exist.

## Source map

- Q, Section 2, valuation assumption, lines 122-133: twice differentiable strongly concave expected valuations.
  The following remark explicitly distinguishes expected curvature from samplewise curvature.
- Q, Section 3, Proposition `existence_uniqueness_prop`, lines 200-238: strict LMI for the full message
  pseudogradient.
- Q, Theorem `nash_implementation_theorem`, lines 240-326: implementation equalities, especially P2(i), and
  symmetric prices.
- Q, Proposition `IR_prop`, lines 386-404, and Proposition `prop2`, lines 410-438: IR coefficient conditions and
  the explicit tax `eq40`.
- Q, Section 4, lines 443-525: the claimed reduction to an aggregate tax, PBR, price compactness, assumed
  nonexpansiveness, and the sample error lemma. The displayed matrices in the aggregate reduction have signs and
  coefficients inconsistent with direct differentiation of `eq40`; all calculations here use `eq40` itself.
- P, CVaR definition, lines 332-345: upper-tail loss CVaR, with risk parameter equal to tail mass.
- P, algorithm and assumptions, lines 379-524: empirical CVaR, ball smoothing, one-point estimator, samplewise
  convexity, boundedness, and Lipschitz continuity.
- P, last-iterate theorem and proof, lines 853-983: the fixed expected empirical-smoothed objective and
  `eq:surrogate-unbiased-gradient`.
- P, appendix CVaR error calculation, lines 1290-1340: distribution-function error and its expectation bound
  before multiplication by the inverse smoothing radius.

Labels are the primary references; source line numbers are provided for navigation.

## The strict LMI cannot coexist with implementation

Q requires simultaneously

\[
\Psi+\Psi^\top\preceq-\upsilon I,\qquad \upsilon>0,
\qquad \sum_m A_{nm}^n=0\quad\text{for every }n.
\]

Take the message-space vector with zero allocation components and identical nonzero price components:

\[
v=\operatorname{col}((0,h),\ldots,(0,h)),\qquad h\ne0.
\]

By Q's definition of the price-price blocks of \(\Psi\),

\[
v^\top\Psi v=-\sum_n h^\top\left(\sum_m A_{nm}^n\right)h=0.
\]

Consequently \(v^\top(\Psi+\Psi^\top)v=0\), contradicting the strict negative bound. This is an algebraic
infeasibility certificate for the simultaneous conditions, not a numerical failure to solve an LMI. It does not
imply that the explicit mechanism has no equilibria, or that no other uniqueness proof is possible.

## An actual failure of individual rationality

Write Q's tax scale as \(a>0\), reserving \(m\) for valuation curvature and \(\rho\) for CVaR tail mass. Q uses
the same symbol for scale and curvature. Set

\[
N=3,\quad K=1,\quad a=1,\quad c=1,\quad
\mathcal X_n=[0,1],
\]

\[
V_1(x)=10x-x^2/2,\qquad V_2(x)=V_3(x)=x-x^2/2.
\]

The planner optimum is \(x^\star=(1,0,0)\), with valid coupling multiplier \(\lambda=9\). At uniform prices
\(p_n=9\), the allocation derivatives of utility are zero for agent 1 and negative for agents 2 and 3 at their
lower bounds. Every price derivative is zero. Each own loss Hessian is

\[
\begin{pmatrix}1&-1/2\\-1/2&1\end{pmatrix}\succ0.
\]

Thus these KKT conditions are sufficient for a Nash equilibrium. Direct substitution into Q's `eq40` gives

\[
(t_1,t_2,t_3)=(21/2,-21/4,-21/4),\qquad
V_1(1)-t_1=-1<0.
\]

This contradicts the claimed IR property. The example is deterministic and therefore also applies to any CVaR
level. Ada independently obtained the same taxes using a different low valuation coefficient for the other
agents.

More generally, at common prices \(p\) and complementary capacity,

\[
t_n=a b_N p^\top(x_n-c/N),\qquad
b_N=\frac{N^2-N+1}{(N-1)^2}.
\]

Also, the coefficients of `eq40` satisfy

\[
\sum_m a_m^n=\frac{a c}{N(N-1)},
\]

which violates Q's P4(ii) whenever capacity has a positive component. Budget balance at these equilibria does
hold.

## A weighted operator repairs allocation implementation

Assume each cost \(f_n=-V_n\) is continuous and \(m\)-strongly convex on its compact convex allocation set, with
a convex extension to a neighborhood sufficient for the subgradient and normal-cone sum rules. Assume the
planner problem has a primal-dual KKT solution. A suitable relative Slater condition suffices. Prices initially
range over the nonnegative orthant.

Stack all allocations first and all prices second. Tensor every matrix below with \(I_K\). Define the consensus
and disagreement projectors

\[
\Pi=\frac{\mathbf1\mathbf1^\top}{N},\qquad
\Delta=I-\Pi,\qquad
\kappa_N=\frac{2N-1}{(N-1)^2}.
\]

Direct differentiation of `eq40` yields the own-cost subgradient operator

\[
F_x\in\partial f(x)+a(\Pi-\kappa_N\Delta)p,
\]

\[
F_p=\frac{aN}{N-1}\Delta p
-\frac{a}{N-1}\mathbf1\left(\sum_n x_n-c\right).
\]

Multiply the price rows by \((N-1)/N\), leaving allocation rows unchanged. This positive block scaling preserves
the product-set optimality conditions. The resulting operator is

\[
G_x\in\partial f(x)+a(\Pi-\kappa_N\Delta)p,
\qquad
G_p=a\Delta p-a\Pi x+\frac{a}{N}\mathbf1c.
\]

For differences \(u=x-x'\), \(v=p-p'\), and any corresponding subgradient selections,

\[
\begin{aligned}
\langle G(s)-G(s'),s-s'\rangle
&\ge m\|u\|^2+a\|\Delta v\|^2
-a\kappa_N\langle\Delta u,\Delta v\rangle\\
&=m\|\Pi u\|^2
+\left(m-\frac{a\kappa_N^2}{4}\right)\|\Delta u\|^2
+a\left\|\Delta v-\frac{\kappa_N}{2}\Delta u\right\|^2.
\end{aligned}
\]

The consensus cross terms cancel exactly. Therefore if

\[
m>\frac{a(2N-1)^2}{4(N-1)^4},
\]

the operator is monotone and its equality directions have \(u=0\) and \(\Delta v=0\). For Q's choice \(m=a\),
this holds for every \(N\ge3\). The bound also implies \(m>a/(N-1)^2\), which makes each own cost jointly
strongly convex in its allocation and price. This supplies the required sufficiency of own KKT conditions
without twice differentiability.

**Implementation theorem.** Under these assumptions, every planner KKT pair \((x^\star,\lambda)\) produces an
equilibrium \((x^\star,\mathbf1\lambda/a)\). Conversely, every equilibrium has allocation \(x^\star\), has
common prices, and those prices multiplied by \(a\) are valid planner multipliers.

To prove existence, substitute the KKT pair into the displayed operator; the allocation conditions coincide with
planner stationarity and the price conditions coincide with capacity complementarity. Own convexity makes the
pair an NE. For any other equilibrium, add the two variational inequalities and apply the monotonicity bound.
Its nonnegative terms must vanish, giving the same allocation and zero price disagreement. At common prices, the
original price optimality conditions impose the capacity inequalities and complementarity, while allocation
optimality imposes planner stationarity. This proves the converse.

The theorem deliberately does not assert a unique full message profile. Strongly convex primal objectives do not
ensure unique multipliers. For example, a strongly concave valuation kink at a binding allocation can support an
interval of common prices. Even smooth valuations with active local bounds can have nonunique coupling
multipliers. A separate multiplier-uniqueness assumption would give full NE uniqueness.

## Rebate correction and exact economic properties

Add to Q's tax the opponent-only term, independently derived by Ada and Emmy,

\[
r_n(s_{-n})=
\frac{aN}{(N-1)^3}
\left(\sum_{j\ne n}p_j\right)^\top
\left(\sum_{j\ne n}x_j-\frac{N-1}{N}c\right),
\qquad t_n^{\rm corr}=t_n+r_n.
\]

It does not change any best response, PBR step, equilibrium, or own-cost operator. At every equilibrium
characterized above, capacity complementarity gives

\[
t_n^{\rm corr}=\lambda^\top(x_n^\star-c/N).
\]

Thus \(\sum_n t_n^{\rm corr}=0\). Suppose also \(0\in\mathcal X_n\) and \(V_n(0)=0\). Planner stationarity and
the subgradient inequality give

\[
V_n(x_n^\star)\ge\lambda^\top x_n^\star,
\qquad
U_n^{\rm corr}(s^\star)\ge\lambda^\top c/N\ge0.
\]

In detail, choose \(g_n\in\partial f_n(x_n^\star)\), \(v_n\in N_{\mathcal X_n}(x_n^\star)\), with
\(g_n+\lambda+v_n=0\). Feasibility of zero gives \(v_n^\top x_n^\star\ge0\). Evaluating the convex subgradient
inequality at zero yields \(0\ge f_n(x_n^\star)+\lambda^\top x_n^\star\), as required.

In the counterexample the corrected taxes are \((6,-3,-3)\), with utilities \((7/2,3,3)\). The correction need
not satisfy Q's advertised coefficient templates; the economic properties follow directly. No off-equilibrium
budget-balance claim is made.

## Exactly what P can supply

For loss \(J_n\), define

\[
C_n(x)=\operatorname{CVaR}_{\rho_n}[J_n(x,\xi)],\qquad
V_n(x)=-C_n(x)+C_n(0).
\]

Cash translation makes a deterministic tax enter utility additively. The target is a sum of individual risks, as
in P; it is not the CVaR of the aggregate random loss.

If every sample loss is \(m\)-strongly convex, then population CVaR, empirical CVaR, the expected empirical
CVaR, and its ball-smoothed version are all \(m\)-strongly convex. To see this, apply samplewise strong
convexity before applying the monotone, convex, cash-translation-invariant risk functional. The deterministic
quadratic deficit passes through unchanged. The same argument applies to the finite empirical risk functional
and then to expectation and smoothing.

Expected strong convexity alone does not suffice. With equal-probability losses \(10-x^2\) and \(3x^2-10\) on
\([0,1]\), the expectation is \(x^2\), but upper-tail CVaR at tail mass \(1/2\) is \(10-x^2\). Its normalized
risk valuation is convex. This is permitted by Q's expected-curvature assumption and excluded by the stronger
samplewise assumption required here. Q's quadratic-plus-random-linear simulation losses do meet the samplewise
curvature requirement.

For fixed sample size \(b_n\) and radius \(\delta_n\), P supplies

\[
\widetilde C_n(x)
=\mathbb E_{\nu,\xi^{1:b_n}}
\left[\widehat C_{n,b_n}(x+\delta_n\nu)\right],
\qquad
\mathbb E[\widehat g_n\mid x]=\nabla\widetilde C_n(x),
\]

\[
\|\widehat g_n\|\le\frac{d_nU_n}{\delta_n}.
\]

Therefore the preceding static theorem applies to \(\widetilde f_n=\widetilde C_n-\widetilde C_n(0)\). Fixed
samples implement this surrogate, not the population risk preferences. Ada's objective-level comparison uses the
bound, already present inside P's appendix proof,

\[
\sup_x|\widetilde C_n(x)-C_n(x)|
\le L_n\delta_n+\frac{U_n\sqrt{2\pi}}{\rho_n\sqrt{b_n}}.
\]

This is a supremum of differences of deterministic expected functions, obtained from a uniform-in-point
expectation bound. It is not an assertion that the expected supremum of the random empirical error has the same
bound. Normalizing both functions at zero can double this error. Transferring economic guarantees requires that
normalization and a common feasible allocation domain.

Ada subsequently sharpened this symmetric bound, and I checked the argument in `ada/research-note.md`. The
empirical threshold minimum is downward biased in expectation, and centered convex smoothing is upward biased.
With

\[
e_n=\frac{U_n\sqrt{2\pi}}{\rho_n\sqrt{b_n}},\qquad
w_n=e_n+L_n\delta_n,
\]

the sharper statement is

\[
-e_n\le\widetilde C_n(x)-C_n(x)\le L_n\delta_n.
\]

The oscillation of the error is therefore at most \(w_n\). At the corrected surrogate equilibrium, budget
balance is exact, actual unilateral improvement is at most \(w_n\), actual normalized participation utility is
at least \(-w_n\), and actual welfare loss is at most \(\sum_n w_n\). If population total cost has curvature
\(m\), then

\[
\|\widetilde x-x^\star\|^2\le\frac{2}{m}\sum_n w_n.
\]

These statements compare the error at two allocations, so they use its oscillation directly and avoid the factor
two from the symmetric bound. They do not remove the inverse-radius variance penalty in finite-time
optimization. Together with the static theorem and learning construction here, they give the intended combined
result.

P assumes a full-dimensional ball about the origin inside its feasible set. Q's nonnegative allocation domains
and network-flow equalities do not satisfy that assumption literally. Smoothing in the affine hull and
translating an interior center handles equality constraints, but inward shrinking can remove zero and invalidate
the IR proof. A clean sufficient assumption for the combined construction is a bounded loss-evaluation oracle on
a fixed relative neighborhood of each original allocation set. Perturbations are then queries, while allocations
stay in the original set. This is an extra assumption, potentially natural with a simulator but potentially
unsuitable for literal physical bandit actions.

### A locally feasible query construction preserving the outside action

Ada's ledger entry 20 supplies a better alternative, which I independently checked. Suppose agent \(n\) knows
a relative interior ball \(a_n+r_n\mathbb B\subseteq\mathcal X_n\), with the ball taken in the affine hull.
Keep the entire original decision set, including zero. Fix \(0<\varepsilon_n<1\) and
\(0<\delta_n<\varepsilon_nr_n\), and query at

\[
q_n(x,u)=(1-\varepsilon_n)x+\varepsilon_na_n+\delta_nu.
\]

For every decision \(x\in\mathcal X_n\) and sphere or ball direction, this is a convex combination of
\(x\) and a point in the known interior ball, hence belongs to \(\mathcal X_n\). Only queries are contracted;
the set of decisions and the zero outside option are preserved. Define the new fixed surrogate

\[
K_n(x)=\mathbb E_{v,\xi^{1:b_n}}
\widehat C_{n,b_n}(q_n(x,v)).
\]

P's smoothing identity and the chain rule give an unbiased allocation-gradient oracle

\[
\widehat g_n^K(x)=
\frac{(1-\varepsilon_n)d_n}{\delta_n}
\widehat C_{n,b_n}(q_n(x,u))u,
\qquad
\mathbb E\widehat g_n^K(x)=\nabla K_n(x).
\]

The gradient is taken in the affine hull and lifted to the ambient allocation coordinates if needed. Its norm
is at most \((1-\varepsilon_n)d_nU_n/\delta_n\). The strict radius inequality leaves a margin for smoothing
near every point of the original decision set. Samplewise curvature \(m_n\) becomes
\(m_n(1-\varepsilon_n)^2\). Thus the weighted implementation theorem requires

\[
m_{\rm eff}:=\min_n m_n(1-\varepsilon_n)^2
>\frac{a(2N-1)^2}{4(N-1)^4}.
\]

With \(R_n=\sup_{x\in\mathcal X_n}\|x-a_n\|\), the error interval is

\[
-e_n-L_n\varepsilon_nR_n
\le K_n(x)-C_n(x)
\le L_n\delta_n+L_n\varepsilon_nR_n.
\]

Indeed, apply the previous one-sided smoothing bound at the contracted center, then use Lipschitz continuity
to compare that center with \(x\). Consequently every economic perturbation bound above holds with

\[
w_n^K=e_n+2L_n\varepsilon_nR_n+L_n\delta_n.
\]

Normalize the surrogate valuation as \(K_n(0)-K_n(x)\). Its exact IR proof remains valid because zero is still
a feasible decision. This construction removes the external-neighborhood oracle assumption when the local
relative interior ball is known. It guarantees local query feasibility; it does not impose aggregate capacity
feasibility during exploratory queries or other off-equilibrium play.

## Why the existing PBR certificate does not transfer

For \(N=3\), \(a=m=1\), identical quadratic valuations, and an interior equilibrium, consensus perturbations of
Q's PBR have Jacobian

\[
T_{\rm cons}=
\begin{pmatrix}\mu+1&-1/2\\-1/2&\mu+1\end{pmatrix}^{-1}
\begin{pmatrix}\mu&-3/2\\1&\mu+1\end{pmatrix}.
\]

Let \(D_\mu=(\mu+1)^2-1/4\). Its price column is

\[
\begin{pmatrix}-(\mu+1)/D_\mu\\1-1/(2D_\mu)\end{pmatrix},
\qquad
\left\|T_{\rm cons}\begin{pmatrix}0\\1\end{pmatrix}\right\|^2
=1+\frac{1}{2D_\mu^2}>1.
\]

Choose, for example, \(\mathcal X_n=[0,2]\), \(c=3\), and \(V_n(x)=2x-x^2/2\). Then \(x_n=p_n=1\) is interior,
so small perturbations genuinely realize this Jacobian. The full stacked input and output norms both have the
same factor \(\sqrt N\); the expansion persists. Thus for every \(\mu>0\), the directly differentiated `eq40`
PBR is not Euclidean nonexpansive on this example. This refutes an automatic quadratic-case justification of Q's
assumption, but not the conditional fixed-point theorem or convergence of suitably damped dynamics by a
different proof.

## A conservative sampled-feedback convergence construction

This section changes the learning rule and only claims convergence to a fixed surrogate equilibrium. Fix the
batches and radii. Use either the neighborhood oracle above or the locally feasible contracted-query oracle
with curvature \(m_{\rm eff}\) satisfying the weighted threshold. In the latter case replace
\(\widetilde C_n\) by \(K_n\) throughout. Assume a compact product
\(\mathcal S=\prod_n(\mathcal X_n\times[0,P_{\max}])\) contains a surrogate planner KKT equilibrium.
A sufficiently large cap is an
assumption; it is not information that the private valuations automatically reveal to the manager.

Let \(\widetilde G\) be the weighted operator for the smooth surrogate. It is continuous and monotone by the
preceding inequality. On a closed convex compact set its variational inequality has a solution. The existence of
a planner KKT equilibrium in the box, combined with the same monotonicity comparison, shows that all boxed
equilibria have its allocation and common prices. Price optimality then still implies the correct
complementarity: a positive slack has a strictly positive price derivative and forces price zero, while a
binding constraint has zero derivative. Consequently the boxed equilibria retain the economic characterization
above.

For constant \(\gamma>0\), define the resolvent

\[
R(z)=(I+\gamma(\widetilde G+N_{\mathcal S}))^{-1}z.
\]

Equivalently, it solves the VI for

\[
H_z(s)=\widetilde G(s)+\gamma^{-1}(s-z).
\]

This operator is \(\sigma\)-strongly monotone with \(\sigma=\gamma^{-1}\). At inner iteration \(t\), each agent
queries P's local estimator for the allocation component, computes its payment components analytically,
exchanges current aggregate allocations and prices, and makes the product-set projected stochastic-gradient
update for \(H_z\). Thus each agent only needs private loss values and local projection, plus aggregate
messages. No true CVaR gradient is required.

For fresh samples, the oracle is conditionally unbiased for \(H_z\). Compactness, the analytic linear payment
terms, and P's gradient bound give a uniform conditional second-moment bound \(M^2\). Projection
nonexpansiveness, the VI condition at \(y=R(z)\), and strong monotonicity yield

\[
\mathbb E[\|s_{t+1}-y\|^2\mid s_t,z]
\le(1-2\sigma\eta_t)\|s_t-y\|^2+\eta_t^2M^2.
\]

With \(\eta_t=1/[\sigma(t+2)]\), induction gives

\[
\mathbb E[\|s_T-R(z)\|^2\mid z]\le\frac{C}{T+1},
\qquad C=\max\{\operatorname{diam}(\mathcal S)^2,M^2/\sigma^2\}.
\]

At outer iteration \(k\), start an inner solve centered at \(z_k\), run

\[
T_k=\left\lceil(k+1)^{2+\epsilon}\right\rceil,\qquad\epsilon>0,
\]

and set \(z_{k+1}=s_{T_k}\). For \(e_k=z_{k+1}-R(z_k)\), the conditional bound gives

\[
\sum_k\mathbb E\|e_k\|<\infty,
\qquad \sum_k\|e_k\|<\infty\quad\text{almost surely}.
\]

For completeness, monotonicity proves firm nonexpansiveness of \(R\): subtract its two VI conditions, giving

\[
\|R(z)-R(w)\|^2\le\langle R(z)-R(w),z-w\rangle.
\]

For any equilibrium \(z^\star\), this implies

\[
\|R(z_k)-z^\star\|^2
\le\|z_k-z^\star\|^2-\|z_k-R(z_k)\|^2.
\]

The summable perturbations make distances to every equilibrium converge and make the squared residual summable.
Compactness supplies a cluster point, and continuity of the resolvent puts it in the equilibrium set.
Convergence of the distance to that cluster point gives convergence of the whole sequence. Thus \(z_k\)
converges almost surely to a possibly random surrogate equilibrium. Boundedness gives mean-square convergence to
that random limit by dominated convergence. Since all equilibrium allocations coincide, the allocations converge
in mean square to the deterministic surrogate welfare optimum.

This proof permits nonunique prices. It does not give an efficient oracle complexity bound, preserve Q's single
outer PBR update, or establish exact population-CVaR equilibrium convergence with fixed sampling and smoothing.
The inner sample cost is \(b_nT_k\) per agent per outer iteration, and the variance constant deteriorates as the
smoothing radius shrinks.

## Prior work and remaining publication burden

Searches performed:

- `"risk-averse" "zeroth-order" games CVaR Wang 2022`
- `"mechanism design" "budget balance" "CVaR" Nash`
- `"proximal best-response" "monotone" convergence games`

[Wang, Shen, and Zavlanos, ICML 2022](https://proceedings.mlr.press/v162/wang22w.html) already combine empirical
CVaR and one-point zeroth-order estimators in noncooperative games, with regret guarantees. [Cui and
Shanbhag](https://arxiv.org/abs/2104.07860) already study stochastic proximal-point methods for monotone
hierarchical games and smoothing-based approximate equilibria in a different game class. Neither the estimator
nor the general proximal construction is itself a credible novelty claim here. The searches did not settle prior
coverage of the specific corrected mechanism and its economic error bounds.

The supported publication lead is a correction-and-extension result: a structural price-consensus obstruction,
an explicit IR failure and incentive-preserving rebate repair, a nonsmooth weighted implementation theorem, and
P's surrogate interpreted as a statistical perturbation of incentives. Ada's improved objective-level bounds
strengthen that package. A stand-alone algorithm paper would need a sharper and more practical learning rule
than the conservative nested construction above, plus benchmarking against existing CVaR game methods.

Remaining unresolved issues are publication novelty, efficient convergence for Q-style local PBR updates,
sample complexity of the conservative nested method, and a useful exact population-risk limit under vanishing
query contraction and smoothing with increasing sample sizes. Local boundary feasibility is resolved above
when an interior ball is known; aggregate feasibility throughout exploratory play is not established. No claim
of absence of prior work is made.

## Verification

`emmy/check_algebra.py` uses exact rational arithmetic to verify the IR counterexample, the corrected
equilibrium taxes for several network sizes, the weighted-operator completion of squares, and the PBR expansion
identity. These are algebra checks, not simulations of stochastic convergence. The static and convergence
arguments above are analytical derivations with their extra assumptions stated explicitly.
