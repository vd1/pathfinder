# Strategic carbon dispatch: viable theorem and boundary

## Model slice

Let \(z=(z_n)_{n\in\mathcal N}\) denote a convex GDL dispatch, such as divisible
DDC workload across bus-time slots, or MESS charge and discharge power after a
route has been fixed. Let \(X\) be the resulting compact convex feasible set.
The forecasted and realized NCI vectors are \(\widehat e\) and \(e\). Owners
have private concave benefits \(v_n(z_n)\). The forecast-stage social problem is

\[
\widehat z\in\arg\max_{z\in X}
\left\{\sum_n v_n(z_n)-\beta\widehat e^\top z\right\}.
\]

If each transformed valuation
\(V_n(z_n)=v_n(z_n)-\beta\widehat e^\top z_n\) is twice differentiable and
strongly concave, and the remaining coupling constraints can be written in
the resource form required by Q, Q's mechanism implements \(\widehat z\) at
its unique Nash equilibrium. The linear NCI term does not change the Hessian,
so it preserves strong concavity. This claim does not cover binary route and
parking choices.

Q cannot be cited directly as internalizing the public carbon term because
owners do not intrinsically value it. There is, however, a balanced transfer
augmentation. Write \(c_n(z_n)=\beta\widehat e^\top g_n(z_n)\), let \(t_n^Q\)
be Q's transfer for transformed valuation \(V_n=v_n-c_n\), and define the
actual transfer

\[
T_n=t_n^Q+c_n-\frac{1}{N-1}\sum_{m\ne n}c_m.
\]

The rebate is independent of \(z_n\), so it does not change owner \(n\)'s
best response. Its sum exactly cancels the carbon charges:

\[
\sum_n(T_n-t_n^Q)=0.
\]

Hence the augmentation preserves Q's equilibrium incentives and its
equilibrium budget balance. For nonnegative DDC carbon contributions, the
rebate is nonnegative and does not weaken Q's individual-rationality bound.
Signed storage credits require a baseline or a new individual-rationality
argument.

## Forecast-to-operation guarantee

Define realized welfare

\[
W_e(z)=\sum_n v_n(z_n)-\beta e^\top z,
\]

and let \(z^\star\in\arg\max_{z\in X}W_e(z)\). Optimality of \(\widehat z\)
under \(\widehat e\) gives

\[
\sum_n v_n(z_n^\star)-\beta\widehat e^\top z^\star
\leq
\sum_n v_n(\widehat z_n)-\beta\widehat e^\top\widehat z.
\]

Rearranging yields the realized welfare regret bound

\[
W_e(z^\star)-W_e(\widehat z)
\leq
\beta(e-\widehat e)^\top(\widehat z-z^\star)
\leq
\beta\lVert e-\widehat e\rVert_\infty
\operatorname{diam}_1(X).
\]

Thus P's forecast validation can be converted into an operational guarantee,
while Q removes strategic inefficiency only for the implementable convex
slice. If equilibrium is computed only approximately, with forecast-objective
gap \(\delta\), the right side gains \(\delta\).

## Decisive boundary

### Exact lift of P's DDC balance into Q's coupling template

At each time (t), define P's normalized workload regulation

\[
w_{i,t}=\frac{\iota^{\mathrm{GLB}}_{i,t}}{\phi_{1i}}.
\]

Equations (28)--(30) give

\[
\sum_i w_{i,t}=0,\qquad
L_{i,t}\leq w_{i,t}\leq U_{i,t},
\]

where (U_{i,t}=B_i) and
(L_{i,t}=-\phi_{2i}\Gamma_{1i,t}/\phi_{1i}). Introduce two nonnegative
local allocation coordinates

\[
a_{i,t}=w_{i,t}-L_{i,t},\qquad
b_{i,t}=U_{i,t}-w_{i,t},
\]

and put (a_{i,t}+b_{i,t}=U_{i,t}-L_{i,t}) inside DDC (i)'s local convex
set. Define

\[
C_t=-\sum_iL_{i,t},\qquad
D_t=\sum_iU_{i,t}.
\]

Then P's balance equality is equivalent to Q-form aggregate caps

\[
\sum_i a_{i,t}\leq C_t,\qquad
\sum_i b_{i,t}\leq D_t.
\]

Indeed, the first cap implies \(\sum_iw_{i,t}\leq0\), the second implies
\(\sum_iw_{i,t}\geq0\), and both therefore force equality. Conversely,
every P-feasible regulation satisfies both caps at equality. This is an
affine bijection, so compactness and convexity are preserved. It also makes
all message allocation coordinates nonnegative, as Q requires. The predicted
DDC carbon term remains affine because
\(D^{\mathrm{ddc}}_{i,t}=\iota^{\mathrm{base}}_{i,t}+\phi_{1i}w_{i,t}\).

This establishes a P-faithful Q-compatible feasible slice for equations
(27)--(30), subject to three qualifications. DDCs must be the strategic
agents, or each owner's bus-time coordinates must be grouped in its local
set. The transformed private valuation must satisfy Q's smooth strong
concavity assumption. Individual rationality still needs a baseline-relative
participation proof because P's mandatory service makes zero gross allocation
an inappropriate outside option. P's displayed DDC formulation introduces no
additional shared grid polytope in this section; any such constraint added in
an implementation must separately be lifted into aggregate caps or covered by
a general-polytope extension.

P's MESS decisions include binary parking, travel, arrival, and departure
variables. Their feasible set is nonconvex, best responses can be set-valued,
and KKT conditions are not sufficient for global optimality. Consequently,
Q's LMI conditions, uniqueness argument, and nonexpansive proximal response
cannot be transferred to the full P problem. A defensible paper should either
focus on divisible DDC dispatch, use a fixed-route or convexified MESS layer,
or develop genuinely new mixed-integer implementation theory. Calling the
full construction a direct application of Q would be false.

## Suggested experiment

Use P's IEEE 33-bus forecast and dispatch data. Compare centralized truthful,
unpriced strategic, Q-implemented convex, and rounded mixed-integer schedules
under the same realized NCI. Report realized emissions, owner utility,
participation, budget residual, convergence, and the empirical ratio of regret
to
\(\beta\lVert e-\widehat e\rVert_\infty\operatorname{diam}_1(X)\).
