# Lift the CVaR threshold instead of estimating CVaR in each round

**Prior-art correction:** [Cardoso and Xu (2019)](https://proceedings.mlr.press/v89/cardoso19a/cardoso19a.pdf), Algorithm 1 and Theorem 2, already give the same joint \((x,\tau)\) spherical estimator with one loss observation and an \(O(T^{-1/4})\) rate in a centralized stochastic convex bandit model. The derivation below checks its transfer to P's objective and sketches a possible network extension. Neither the lifted estimator nor the rate is new.

## Problem and construction

P defines \(C^i(x)\) through the Rockafellar--Uryasev minimization over a threshold \(\tau\) in its §CVaR (lines 310-329). It then minimizes over \(\tau\) afresh in each sampled empirical CVaR (lines 404-440). The latter creates the finite-sample term in P's estimator bound (lines 540-568) and its fixed-sample residual gap (lines 778-795). Q's query-cost discussion (lines 1242-1258) says that any gain must count loss samples and predictor calls.

Set \(\tau_i\in[-U_i,U_i]\) and define

\[
H_i(x,\tau_i,\xi)
=\tau_i+\alpha_i^{-1}(J^i(x,\xi)-\tau_i)_+,
\qquad
\Phi(x,\boldsymbol\tau)
=\frac1m\sum_{i=1}^m\mathbb E H_i(x,\tau_i,\xi^i).
\]

Since P assumes that every sampled \(J^i(\cdot,\xi)\) is convex, each \(H_i\) is jointly convex in \((x,\tau_i)\). Bounded losses permit an optimal threshold in \([-U_i,U_i]\). Thus

\[
\min_{x,\boldsymbol\tau}\Phi(x,\boldsymbol\tau)
=\min_x\frac1m\sum_i C^i(x).
\]

This reformulation is standard. The remaining research issue is whether a distributed theorem under P's time-varying graph or a prediction contract adds something beyond Cardoso and Xu's known method.

## One sample gives unbiased joint gradient feedback

An initial proposal used P's sphere identity for an \(x\)-gradient and an indicator for a \(\tau_i\)-subgradient from the same sphere sample. Ada found that these are derivatives of different smoothings: the former smooths over a ball and the latter over a sphere. They cannot simply be combined as a joint gradient.

A direct repair smooths the joint vector \(z_i=(x,\tau_i)\in\mathbb R^{d+1}\). At \((y_k^i,\tau_k^i)\), draw \(u_k^i=(u_{x,k}^i,u_{\tau,k}^i)\) uniformly on the unit sphere in \(\mathbb R^{d+1}\), and query one loss \(J_k^i=J^i(y_k^i+\delta_i u_{x,k}^i,\xi_k^i)\). Then form

\[
g_k^i=\frac{d+1}{\delta_i}
H_i(y_k^i+\delta_i u_{x,k}^i,
\tau_k^i+\delta_i u_{\tau,k}^i,\xi_k^i)u_k^i.
\]

Let \(H_{\delta,i}(z)=\mathbb E_{v,\xi}H_i(z+\delta_i v,\xi)\), where \(v\) is uniform on the unit ball in \(\mathbb R^{d+1}\). P's spherical identity, now applied in the full joint dimension, gives \(\mathbb E[g_k^i\mid\mathcal F_k]=\nabla H_{\delta,i}(y_k^i,\tau_k^i)\). The same sampled loss supplies both gradient coordinates. No empirical CVaR is formed, so P's DKW bias term does not enter.

The stored threshold is projected onto \([-U_i,U_i]\); its temporary perturbation may leave that interval, but \(H_i\) remains defined there. With \(|J^i|\le U_i\), a bound is \(|H_i|\le M_{i,\delta}:=U_i+\delta_i+(2U_i+\delta_i)/\alpha_i\) at every queried point. Thus \(\|g_k^i\|\le(d+1)M_{i,\delta}/\delta_i\) pathwise. The joint sampled loss is Lipschitz with constant at most \(\sqrt{L_i^2+1}/\alpha_i\), so its smoothing error is of order \(\delta_i/\alpha_i\). These facts fit both a projected stochastic gradient proof and P-style graph mixing.

## Centralized proof check

For a common radius \(\delta\), write \(L_H=m^{-1}\sum_i L_i/\alpha_i\), \(L_z=m^{-1}\sum_i\sqrt{L_i^2+1}/\alpha_i\), and \(D_z^2=D_x^2+4\sum_i U_i^2\). The global gradient estimator has an \(x\) component \(m^{-1}\sum_i g_{x,k}^i\) and threshold components \(m^{-1}g_{\tau,k}^i\). Jensen's inequality and the pathwise local bound give the loose squared-norm cap

\[
G_\delta^2
\le\left(1+\frac1m\right)
\frac1m\sum_i\frac{(d+1)^2M_{i,\delta}^2}{\delta^2}.
\]

Projecting onto \(\mathcal X_\delta\times\prod_i[-U_i,U_i]\), using step size \(\eta=D_z/(G_\delta\sqrt T)\), and averaging iterates gives the standard conditional subgradient inequality

\[
\mathbb E[\Phi_{\boldsymbol\delta}(\bar x_T,\bar{\boldsymbol\tau}_T)]
-\min_{x\in\mathcal X_\delta,\boldsymbol\tau}
\Phi_{\boldsymbol\delta}(x,\boldsymbol\tau)
\le\frac{D_zG_\delta}{\sqrt T}.
\]

Let \((x^\star,\boldsymbol\tau^\star)\) minimize the unsmoothed joint problem and let \(z_\delta=(1-\delta/r)x^\star\), as in P. Smoothing and comparator shrinkage each cost at most a constant times \(L_H\delta\); explicitly,

\[
\mathbb E[\mathcal C(\bar x_T)]-\mathcal C(x^\star)
\le\frac{D_zG_\delta}{\sqrt T}
+2L_z\delta+L_H D_x\delta/r.
\]

Choosing \(\delta\) of order \(T^{-1/4}\) gives an expected gap of order \(T^{-1/4}\) with one loss query per agent per round, reproducing the rate of Cardoso and Xu in this notation. This calculation is central only.

For a distributed proof, agent \(i\) would mix \(x_i\) with its neighbors as P does, take a projected stochastic step in \(x_i\), and update its own \(\tau_i\) without consensus. Use the potential \(V_k=\sum_i\|x_k^i-z_\delta\|^2+\sum_i|\tau_k^i-\tau_i^\star|^2\). Convexity of the joint smoothed sample objective gives the one-step descent term \(\sum_i[H_{\delta,i}(y_k^i,\tau_k^i)-H_{\delta,i}(z_\delta,\tau_i^\star)]\). Lipschitzness in \(x\) compares this to the common decision \(\bar x_k\) at a cost proportional to \(\sum_i(L_i/\alpha_i)\|y_k^i-\bar x_k\|\). P's graph mixing lemma then suggests, for a constant step size and common radius,

\[
\mathbb E[\mathcal C(\widehat x_T)]-\mathcal C(x^\star)
\le O\!\left(\frac{V_0}{m\eta T}
+\eta\sum_i\frac{(d+1)^2M_{i,\delta}^2}{m\delta^2}
+\frac{\max_i(L_i/\alpha_i)}{mT}
\sum_{k<T}\mathbb E\sum_i\|y_k^i-\bar x_k\|
+L_z\delta+L_H D_x\delta/r\right).
\]

The graph term should be \(O(1/T+\eta/\delta)\) with graph-dependent constants, yielding the same \(T^{-1/4}\) order for \(\eta\) of order \(\delta/\sqrt T\). This is a proof sketch, not a completed theorem. The exact constants and filtration must be checked, and the threshold coordinates change the potential used in P.

## Where a prediction could matter

A predicted quantile may initialize \(\tau_i\), reducing its initial distance to an optimal threshold; projection to \([-U_i,U_i]\) retains a bound for any hint. More ambitious predictions of \(C^i(y_k^i)\) can center the one point estimate, but a single noisy \(H_i\) retains stochastic variance of order \(1/\delta_i^2\). A better rate or query advantage requires a stronger oracle condition or a new mechanism; accurate initialization alone changes a constant in the standard bound. Predictor inference and training cost must be stated in the objective units before calling this learning augmented.

There is a simple lower-bound example showing why an exact threshold hint alone cannot eliminate loss queries. Take one agent, \(\mathcal X=[-1,1]\), a Bernoulli \(\xi\) with \(\Pr(\xi=1)=\alpha\), and two possible worlds:

\[
J_A(x,\xi)=\xi(x+1)/2,
\qquad
J_B(x,\xi)=\xi(1-x)/2.
\]

Both sampled losses satisfy P's boundedness, convexity, and Lipschitz assumptions. In both worlds, the \((1-\alpha)\)-quantile is exactly zero for every \(x\), so the same perfect threshold predictor \(\widehat\tau(x)=0\) is available. Yet \(C_A(x)=(x+1)/2\) is minimized at \(-1\), while \(C_B(x)=(1-x)/2\) is minimized at \(1\). If all \(n\) fresh queries have \(\xi=0\), an event of probability \((1-\alpha)^n\), every observed loss is zero regardless of the adaptive query points, and the worlds are indistinguishable. On this event the average of the two objective gaps at any output is exactly \(1/2\). Therefore the worst-world expected gap of any \(n\)-query algorithm is at least \((1-\alpha)^n/2\), even with the exact quantile predictor. This is a lower bound for that pair of worlds, not a minimax rate for the full CVaR problem. It shows that a useful prediction contract must reveal something about tail magnitudes or sampling access, in addition to the threshold.

The joint threshold estimator is already in Cardoso and Xu. [Wang, Shen, and Zavlanos](https://arxiv.org/abs/2203.08957) also study CVaR one point feedback in an online game. Search queries were `distributed zeroth order CVaR optimization auxiliary variable tau one sample stochastic gradient`, `bandit CVaR online convex optimization VaR prediction quantile advice zeroth order`, `CVaR zeroth-order threshold stochastic optimization`, `CVaR bandit auxiliary variable one-point`, `distributed risk-averse bandit CVaR time-varying networks joint threshold`, and `decentralized CVaR bandit one-point optimization`. The search did not settle whether the precise time-varying network and local-threshold theorem exists. This is a proof route to check, not a novelty claim.
