# Q and P: counterfactual carbon signals and strategic dispatch

## Model interface

Q maximizes \(\sum_n V_n(x_n)\) under a componentwise shared capacity, with convex compact local sets and strongly concave valuations [Q, lines 105-140]. Its quadratic payment implements that welfare optimum at a unique Nash equilibrium under the stated conditions [Q, lines 198-323 and 408-428]. The convergence argument additionally assumes compact prices and a nonexpansive proximal best-response map [Q, lines 449-481 and 518-616].

P minimizes a forecast-weighted GDL carbon expression [P, Eq. (26), lines 879-904]. Its NCI calculation includes MESS discharge and inflowing power [P, Eqs. (23)-(24), lines 800-841], so a change in dispatch can change the NCI against which a forecast was trained. P also imposes workload balance and binary MESS itinerary constraints [P, Eqs. (28) and (35)-(42), lines 907-1037]. These prevent direct application of Q's convex, separable theorem to P's full dispatch.

## A narrow guarantee

Let \(F\) be a fixed feasible dispatch set, \(C(x)\) realized carbon, and \(\widehat C(x)\) the forecast surrogate. Suppose \(\widehat x\) is an \(\varepsilon\)-optimal minimizer of the surrogate, so \(\widehat C(\widehat x)\leq\inf_{x\in F}\widehat C(x)+\varepsilon\), and suppose the *counterfactual* error satisfies \(\sup_{x\in F}|C(x)-\widehat C(x)|\leq\delta\). For a realized-carbon minimizer \(x^\star\),

\[
C(\widehat x)-C(x^\star)
\leq [C(\widehat x)-\widehat C(\widehat x)]
+[\widehat C(\widehat x)-\widehat C(x^\star)]
+[\widehat C(x^\star)-C(x^\star)]
\leq 2\delta+\varepsilon.
\]

Thus exact Nash implementation of the surrogate could remove \(\varepsilon\), but it cannot remove \(\delta\). If \(\widehat C(x)=\widehat e^\top x\), \(C(x)=e(x)^\top x\), \(x\geq0\), and \(\|x\|_1\leq M\), a sufficient condition is \(\sup_{x\in F}\|e(x)-\widehat e\|_\infty\leq\delta/M\). P reports historical NCI prediction error [P, Eq. (25), lines 810-841; Table III and discussion, lines 1390-1513], which does not by itself establish this uniform dispatch-conditioned condition.

If NCI is differentiable with dispatch, the correct marginal signal for \(C(x)=e(x)^\top x\) is \(\nabla C(x)=e(x)+J_e(x)^\top x\). Fixed forecast NCI uses only the first term. This is a model distinction, not a claim that P's particular numerical case has harmful feedback.

For fixed \(\widehat e\), an off-equilibrium balanced carbon charge can be written
\(\tau_n^C=\beta\widehat e^\top x_n-\frac{\beta}{N-1}\sum_{m\ne n}\widehat e^\top x_m\).
Its own marginal is \(\beta\widehat e\), and its sum over agents is zero.
This can be combined with Q's payment to implement a forecast-weighted welfare objective
under Q's assumptions, but Q's individual-rationality result then needs a new check.
For nonlinear carbon \(C(x)\), the same rebate does not provide the true marginal signal.
If private utility matters, the implemented objective is
\(\max_x\sum_n u_n(x_n)-\beta\widehat C(x)\), not pure carbon minimization.
The carbon-regret bound above therefore does not automatically apply to that welfare optimizer.
For any dispatch \(\widehat x\), a direct certificate against a baseline \(x^b\) is
\(\widehat C(\widehat x)+\delta<C(x^b)\).
If the baseline is only predicted to the same error tolerance, it is sufficient that
\(\widehat C(\widehat x)+2\delta<\widehat C(x^b)\).

## Illustrative failure

Consider flexible demand split between locations A and B, with \(x_A+x_B=1\). A forecast obtained near \(x_A=0.1\) gives \(\widehat e_A=0.2\) and \(\widehat e_B=0.6\), so its linear surrogate sends all load to A. Suppose the counterfactual intensities are \(e_A(x_A)=0.1+x_A\) and \(e_B(x_B)=0.6\). Then \(C(1,0)=1.1\) whereas \(C(0,1)=0.6\). This is a logical counterexample to a guarantee from pointwise forecast accuracy, not a calibrated model of P's IEEE 33-bus case.

## Scope of a publication test

The research target is a dispatch-conditioned carbon certificate for decentralized, private-cost response. A first test can hold MESS itineraries fixed and compare the forecast-surrogate allocation, a private-cost Nash implementation, and a carbon-flow re-evaluation after each allocation. DDC owners cannot be used as Q's agents without handling P's cross-DDC workload-balance equality. Recasting agents as owners of splittable workload batches gives local allocation simplexes and destination capacities, but changes the market model. A mandatory-workload simplex excludes zero, so Q's individual-rationality proof does not apply without a new outside option. P's binary itineraries, possible nonlinear carbon-flow response, and forecast-update timing remain open. P's reported 33.86% reduction compares its simulated Cases 2 and 3 [P, lines 1288-1293]; it is not a guarantee under private costs or dispatch-conditioned forecast error.

## Prior-work boundary

The carbon-signal critique alone is established territory.
Jiang et al. study average-carbon load shifting in an equilibrium model and show that
the average signal may fail to reduce emissions
(https://arxiv.org/abs/2504.07248).
Chen and Zhao propose a joint electricity-carbon pricing mechanism with budget balance
and incentive properties (https://arxiv.org/abs/2308.08195).
Chen combines carbon emission flow with carbon-aware demand response
(https://arxiv.org/abs/2404.05713).
The possible contribution here must specifically join day-ahead forecast uncertainty,
dispatch-conditioned carbon verification, and strategic MESS/DDC participation.
The simple \(2\delta\) inequality and linear rebate are useful checks but are not,
by themselves, a publication-level result.
