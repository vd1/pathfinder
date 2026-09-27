# Forecast conditioned carbon scheduling and equilibrium prices

## Source anchors and scope

Q's manager problem in `inputs/Q.tex`, Problem Formulation, maximizes
\(\sum_n V_n(x_n)\) over convex local sets under \(\sum_n x_n\leq c\).
Its valuation assumption requires strong concavity. The payment in Q Eq. (40)
is claimed in Proposition 2 to satisfy the strict uniqueness LMI in Proposition 1
and the implementation condition in Theorem P2. P's `inputs/P.txt`, Section
3.4, Eq. (26), minimizes a forecast-NCI-weighted flexible-load objective.
P's DDC Eqs. (27)–(30) contain continuous workload regulation, while its
MESS Eqs. (35)–(42) contain binary location and travel decisions. P's calculated
NCI in Eq. (23) depends on generation, flow, and MESS discharge.

The result below concerns a convex, optional flexible-load slice whose actions
are nonnegative bus-time quantities and whose local feasible sets contain zero.
It does not implement P's full mixed-integer dispatch. P's fixed workload
balance in Eq. (28) also needs a different participation benchmark if zero
service is infeasible.

## Incompatible conditions in Q

Q Proposition 1 asks for
\(\Psi+\Psi^\top\preceq-\upsilon I\) with \(\upsilon>0\). Q Theorem P2(i)
requires \(\sum_m A_{nm}^n=0\) for every \(n\). Take a nonzero vector
\(q\in\mathbb R^K\) and a direction \(v\) whose allocation blocks are zero
and whose price blocks all equal \(q\). From Q's definition of \(\Psi\),
\[
v^\top\Psi v
=-\sum_n q^\top\Bigl(\sum_m A_{nm}^n\Bigr)q=0.
\]
Hence \(v^\top(\Psi+\Psi^\top)v=0\), contradicting the strict LMI.
No payment parameters satisfy both stated conditions. This invalidates the
claimed LMI feasibility of Q Proposition 2, though it does not establish
failure of efficient allocation.

There is also a concrete failure of full equilibrium uniqueness for Eq. (40).
Let \(N=2\), \(K=1\), \(\alpha=1\), \(c=2\),
\(\mathcal X_1=\mathcal X_2=[0,1]\), and
\(V_n(x)=3x-x^2/2\). At the profile \(x_1=x_2=1\) and
\(p_1=p_2=p\), agent \(n\)'s unilateral deviation can be written as
\(x_n=1-\delta\), \(p_n=p+u\), with \(\delta\in[0,1]\) and
\(u\geq-p\). Substitution in Q Eq. (40) gives the utility change
\[
U_n(1-\delta,p+u;1,p)-U_n(1,p;1,p)
=-(2-p)\delta-\tfrac12(\delta+u)^2\leq0
\]
for every \(p\in[0,2]\). Thus there is a continuum of equilibria, even
though the efficient allocation is unique. The aggregate capacity is redundant
with the two local upper bounds, so the planner's capacity multiplier is not
unique either.

Q Eq. (40) also fails the claimed individual rationality. Ada's independent
counterexample in ledger entry 10 takes \(N=2\), \(K=1\), \(\alpha=1\),
\(c=1\), \(\mathcal X_n=[0,1]\),
\(V_1(x)=3x-x^2/2\), and \(V_2(x)=2x-x^2/2\).
The profile \((x_1,x_2,p_1,p_2)=(1,0,2,2)\) is an equilibrium by the
price best responses below and joint concavity of each player's payoff.
At this profile Q Eq. (40) gives \((t_1,t_2)=(3,-3)\). Thus
\(U_1=V_1(1)-3=-1/2<0=V_1(0)\).

## Allocation-level repair for Q Eq. (40)

Assume \(N\geq2\), the stated compact convex local sets and strongly concave
valuations, and existence of a planner primal-dual KKT pair. At any Nash
equilibrium, write \(S^k=\sum_n x_n^k-c^k\) and
\(P^k=\sum_n p_n^k\). Direct minimization of Q Eq. (40) in the price of
agent \(n\) yields
\[
p_n^k=\left[\frac{P^k-p_n^k+S^k}{N-1}\right]_+.
\]
If any price in coordinate \(k\) is positive, then
\(Np_n^k=P^k+S^k>0\). A zero price for another agent would require
\(P^k+S^k\leq0\), a contradiction. All prices are therefore positive and
equal, and summing \(Np_n^k=P^k+S^k\) gives \(S^k=0\).
If none is positive, all are zero and \(S^k\leq0\). Thus equilibrium prices
are common, aggregate capacities are feasible, and
\(p^k S^k=0\).

At common prices, direct differentiation of Q Eq. (40) gives
\(\nabla_{x_n}t_n=\alpha p\). The allocation best responses consequently
give the planner's stationarity conditions with multiplier
\(\lambda=\alpha p\). Every Nash equilibrium has the unique social optimum
as its allocation. Conversely, every planner primal-dual KKT pair, with
\(p_n=\lambda/\alpha\) for all \(n\), is a Nash equilibrium: each agent's
payoff is jointly concave in its own allocation and price, because its
quadratic Hessian is bounded above by
\[
\alpha\begin{pmatrix}
-I&I/(N-1)\\
I/(N-1)&-I
\end{pmatrix}\preceq0.
\]
This proves existence under the KKT assumption and allocation uniqueness.
Price uniqueness requires an additional condition ensuring a unique relevant
capacity multiplier.

## Correcting individual rationality and adding a carbon charge

Ada's transfer in ledger entry 11 repairs Q's equilibrium tax without
changing any best response. Define
\[
h_n=\alpha\frac{N}{(N-1)^2}
\left(\frac{1}{N-1}\sum_{m\ne n}p_m\right)^\top
\left(\sum_{m\ne n}x_m-\frac{N-1}{N}c\right).
\]
It uses only other agents' actions. At any equilibrium, direct substitution
into Q Eq. (40), together with common prices and complementarity, gives
\[
t_n^Q=\alpha\left(1+\frac{N}{(N-1)^2}\right)
p^\top(x_n-c/N),\qquad
t_n^Q+h_n=\alpha p^\top(x_n-c/N).
\]
The corrected payments sum to zero because \(p^\top(\sum_n x_n-c)=0\).
Since \(x_n=0\) is feasible, allocation optimality gives
\(V_n(x_n)-\alpha p^\top x_n\geq V_n(0)=0\). The corrected
equilibrium utility is therefore at least \(\alpha p^\top c/N\geq0\).
This is equilibrium budget balance and individual rationality, not an
off-equilibrium balance claim for \(h_n\).

For a nonnegative day-ahead bus-time forecast \(\hat e\), let the optional
flexible-load planner maximize
\(\sum_n V_n(x_n)-\beta\hat e^\top\sum_n x_n\) under Q's constraints.
Add to the corrected payment the transfer
\[
r_n(x)=\beta\hat e^\top x_n
-\frac{\beta}{N-1}\sum_{m\ne n}\hat e^\top x_m.
\]
The second term is independent of agent \(n\)'s own action, and
\(\sum_n r_n(x)=0\) at every profile. Therefore best responses are those
of Q with valuation \(V_n(x_n)-\beta\hat e^\top x_n\), which remains
strongly concave. The allocation-level repair above gives the unique
forecast-optimal allocation at every equilibrium, subject to its KKT
assumption. Equilibrium budget balance persists. If zero is a feasible
outside option and \(\hat e\geq0\), the corrected equilibrium utility is
\[
\bigl[V_n(x_n)-\beta\hat e^\top x_n-\alpha p^\top x_n\bigr]
+\alpha p^\top c/N
+\frac{\beta}{N-1}\sum_{m\ne n}\hat e^\top x_m\geq0.
\]
The inequality follows from the allocation best response against zero.
These claims do not establish unique prices or stochastic learning
convergence.

If physical marginal carbon coefficients are a fixed vector \(e\) and
\(\lVert e-\hat e\rVert_\infty\leq\varepsilon\), let \(x_e\) and
\(x_{\hat e}\) maximize the corresponding true and forecast objectives.
Since every feasible aggregate quantity satisfies \(0\leq X\leq c\),
optimality under the forecast gives
\[
0\leq F_e(x_e)-F_e(x_{\hat e})
\leq\beta\varepsilon\lVert X_e-X_{\hat e}\rVert_1
\leq\beta\varepsilon\lVert c\rVert_1.
\]
This is a welfare bound for fixed coefficients, not a claim about P's
endogenous NCI. For an action-dependent NCI \(e(x)\), the same comparison
needs a uniform counterfactual bound on
\(\lVert e(x)-\hat e\rVert_\infty\) over all feasible dispatches. A held-out
forecast MAE at observed dispatches does not provide that bound. P Eq. (23)
shows why dispatch can change the calculated NCI used to evaluate the
forecast, while Eq. (26) treats it as fixed during optimization.

Under the stronger uniform premise
\(\sup_{x\in\mathcal F}\lVert e(x)-\hat e\rVert_\infty\leq\varepsilon\),
let \(x^\star\) maximize
\(F(x)=\sum_n V_n(x_n)-\beta e(x)^\top X(x)\). At every feasible \(x\),
\(\lvert F(x)-F_{\hat e}(x)\rvert\leq\beta\varepsilon\lVert c\rVert_1\).
Comparing \(x^\star\) with the forecast-optimal \(x_{\hat e}\) on both sides
of its forecast-optimality inequality gives
\[
0\leq F(x^\star)-F(x_{\hat e})
\leq 2\beta\varepsilon\lVert c\rVert_1.
\]
This concerns the NCI-weighted accounting objective. Interpreting it as a
bound on changes in physical system emissions requires an additional
identity connecting \(e(x)^\top X(x)\) to actual generation emissions or a
separate marginal-emissions model. P Eq. (23) defines calculated average
intensity, while Eq. (26) weights flexible-load actions by its forecast;
neither equation supplies that identity for an intervention.

A two-bus thought experiment separates attributed intensity from physical
incremental emissions. At bus A, one unit of baseline load exhausts
zero-carbon generation, and backup generation emits one unit per added MWh.
At bus B, generation emits one-half unit per added MWh. The baseline average
intensities are \(e_A=0\) and \(e_B=1/2\), so the frozen-intensity objective
sends one movable MWh to A. The added physical emissions are one unit at A
and one-half unit at B. This is a constructed case, not a simulation result
from P. It motivates a dispatch-aware marginal carbon signal if the objective
is physical emission reduction.

The simple balanced carbon charge is not by itself a novelty claim. A prior
joint electricity-carbon pricing paper already claims social optimality,
budget balance, individual rationality, and incentive properties:
https://arxiv.org/abs/2308.08195 . The distinctive research task here would
require a verified allocation-level mechanism under forecast feedback and a
counterfactual carbon guarantee, followed by tests on P's dispatch setting.
