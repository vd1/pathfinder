# Q and P: a repaired forecast-conditioned allocation mechanism

## Source anchors and scope

Q, Section 2 and Eq. (40), studies continuous resource allocations with convex compact local sets, strongly
concave private valuations, and componentwise aggregate capacity. Its Proposition 2 claims unique Nash
equilibrium, budget balance, and individual rationality. P, Section 3.4, Eq. (26), places day-ahead forecast
nodal carbon intensity into a linear dispatch objective. P's DDC Eqs. (27)–(30) contain a continuous
workload slice; its MESS Eqs. (35)–(42) have binary routing decisions. P Eq. (23) includes mobile storage
discharge in calculated carbon intensity. The construction here applies to an optional, continuous, convex
load slice indexed by bus and hour. It does not directly cover P's full MESS schedule or fixed-workload DDC
program. This deliberately changes the question from implementing P's exact scheduling model to testing
whether its forecast can coordinate a separate voluntary load market. P's Eq. (23) gives calculated average
NCI, so the carbon quantity below is attributed load emissions, not automatically the change in physical
generation emissions.

## A counterexample to Q's individual-rationality claim

Set \(N=2\), \(K=1\), \(\alpha=c=1\), \(\mathcal X_1=\mathcal X_2=[0,1]\), \(V_1(x)=3x-x^2/2\), and
\(V_2(x)=2x-x^2/2\). At \((x_1,x_2,p_1,p_2)=(1,0,2,2)\), Q Eq. (40) gives price best responses equal to
\(2\). Each allocation has marginal tax \(2\), while \(V_1'(1)=V_2'(0)=2\), so the profile is an
equilibrium. Direct substitution gives \(t_1^Q=3\) and \(t_2^Q=-3\). Agent 1 has
\(U_1=V_1(1)-3=-1/2<0=V_1(0)\). Q's displayed payment therefore fails its asserted individual rationality,
despite efficient allocation and budget balance.

Emmy's ledger entries 4 and 6 identify a separate uniqueness defect. Q's strict negative-definiteness
condition P1 is incompatible with its P2 common-price condition, and Eq. (40) can have multiple equilibrium
prices. The theorem below claims a unique allocation, not a unique price.

## Corrected payment and result

Assume \(N\ge2\), \(0\in\mathcal X_n\subset\mathbb R_+^K\), \(c\ge0\), the other convexity and concavity
assumptions of Q, and a planner multiplier. Let P's frozen forecast be \(\hat e\ge0\) and let \(\beta\ge0\).
The desired forecast-conditioned planner solves

\[
\max_{x_n\in\mathcal X_n,\ \sum_n x_n\le c}
F_{\hat e}(x),\qquad
F_{\hat e}(x)=\sum_n V_n(x_n)-\beta\hat e^\top\sum_n x_n.
\]

Write \(t_n^Q\) for Q Eq. (40), \(\bar p_{-n}=\sum_{m\ne n}p_m\), and \(\bar x_{-n}=\sum_{m\ne n}x_m\). Add
an own-action-independent transfer

\[
h_n=\alpha\frac{N}{(N-1)^2}
\left(\frac{\bar p_{-n}}{N-1}\right)^\top
\left(\bar x_{-n}-\frac{N-1}{N}c\right)
\]

and a carbon charge with leave-one-out rebate

\[
b_n=\beta\hat e^\top x_n
-\frac{\beta}{N-1}\sum_{m\ne n}\hat e^\top x_m,\qquad
t_n=t_n^Q+h_n+b_n.
\]

The own-action-independent terms do not change best responses. Thus the game is strategically equivalent to
Q Eq. (40) with valuations \(\widetilde V_n=V_n-\beta\hat e^\top x_n\). These remain strongly concave.

For each coordinate \(k\), define \(S^k=\sum_n x_n^k-c^k\) and \(P^k=\sum_n p_n^k\). Q Eq. (40) gives the
exact price best response

\[
p_n^k=\left[\frac{P^k-p_n^k+S^k}{N-1}\right]_+.
\]

If any price is positive, then \(Np_n^k=P^k+S^k>0\). A zero price for another player would violate its
best-response condition. Hence all positive prices agree and \(S^k=0\). If all prices are zero, \(S^k\le0\).
Every equilibrium therefore has common \(p\ge0\), aggregate feasibility, and \(p^\top(\sum_n x_n-c)=0\). At
a common price, Q Eq. (40) has own-allocation marginal tax \(\alpha p\), so the allocation best responses
satisfy the planner optimality conditions with \(\lambda=\alpha p\). Strong concavity makes the allocation
unique. Conversely, a planner primal-dual pair gives an equilibrium because each player's own payoff is
jointly concave in its allocation and price.

At an equilibrium, substitution and complementarity reduce Q Eq. (40) to

\[
t_n^Q=\alpha\left(1+\frac{N}{(N-1)^2}\right)
p^\top\left(x_n-\frac cN\right).
\]

The added \(h_n\) cancels the extra factor, giving \(t_n^Q+h_n=\alpha p^\top(x_n-c/N)\). These base payments
sum to zero by complementarity. Also \(\sum_n b_n=0\) at every profile, so the total budget balances at
equilibrium.

Since \(x_n=0\) is feasible, allocation optimality gives \(V_n(x_n)-\beta\hat e^\top x_n-\alpha p^\top
x_n\ge0\). Agent \(n\)'s equilibrium utility under the corrected tax is this term plus \(\alpha p^\top
c/N+\beta\hat e^\top\bar x_{-n}/(N-1)\ge0\). The mechanism is individually rational for the optional-load
outside option. P Eq. (28) fixes total DDC workload, so its participation baseline must be reformulated
before applying this conclusion.

## Forecast accuracy and endogenous carbon

Let \(e(x)\) be realized nodal carbon intensity, possibly dependent on dispatch. Suppose a counterfactual
error guarantee holds over the entire feasible set:

\[
\sup_{x\in\mathcal F}\|e(x)-\hat e\|_\infty\le\varepsilon.
\]

Nonnegative allocations and aggregate capacities give
\(|F_{e(x)}(x)-F_{\hat e}(x)|\le\beta\varepsilon\|c\|_1\) for every feasible \(x\).
If \(\hat x\) is the forecast-optimal
equilibrium allocation and \(x^\star\) maximizes realized welfare, then the two-sided comparison yields

\[
F_{e(x^\star)}(x^\star)-F_{e(\hat x)}(\hat x)
\le 2\beta\varepsilon\|c\|_1.
\]

P's reported observational forecast accuracy does not establish this uniform counterfactual premise.
If true \(e\) is an exogenous fixed vector, the sharper bound is
\(\beta\varepsilon\|c\|_1\), since the forecast error multiplies the difference
of two feasible aggregate allocations. The dispatch-dependent result above
requires the factor \(2\) from comparing two different counterfactual errors.

To translate this into a physical system-emissions statement, let \(C(x)\) be actual generation emissions
and \(C_0\) a fixed baseline. An additional uniform accounting-link assumption would be

\[
\sup_{x\in\mathcal F}
\left|C(x)-C_0-e(x)^\top\sum_n x_n\right|\le\delta.
\]

Then the same two-sided comparison bounds regret for physical welfare
\(\sum_n V_n(x_n)-\beta(C(x)-C_0)\) by
\(2\beta(\varepsilon\|c\|_1+\delta)\).
Neither P's Eq. (23) nor its forecast tests establish this accounting link; it remains a separate modeling
and validation task.

For a small failure example, take two identical agents, each with \(x_n=(a_n,b_n)\ge0\), \(a_n+b_n\le1/2\),
\(c=(1,1)\), \(V_n=10(a_n+b_n)-0.05(a_n^2+b_n^2)\), \(\beta=1\), and \(\hat e=(1,2)\). The forecast optimum
sends both full loads to A. Suppose actual intensities are \(e_A(A)=1+3A\), where \(A=a_1+a_2\), and
\(e_B=2\). At the no-response baseline \(A=0\), the forecast is exact. After both respond, carbon at A is
\(4\), while sending both to B emits \(2\) with the same valuation. The forecast-optimal allocation is at
least \(2\) welfare units worse than an available alternative. This response law is a toy assumption, not a
fitted model of P's test grid.

## Remaining work

A publication would need a physical or empirical counterfactual intensity model, an appropriate
participation benchmark for mandatory loads, and a fresh learning analysis. Q's strict LMI uniqueness and
stochastic convergence claims do not transfer automatically. The mixed-integer MESS problem needs a distinct
mechanism or a proved relaxation.

Chen and Zhao's [joint electricity-carbon pricing paper](https://arxiv.org/abs/2308.08195)
already claims budget balance, individual rationality, and carbon-aware
social optimality in a generator-load market. The corrected carbon payment
alone is therefore a weak novelty claim. A substantive paper would need
the counterfactual forecast guarantee or another distinctive result.
