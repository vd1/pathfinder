# One query and exact last iterate convergence: a proof route

## Question and prior art

Can P's time-varying-network CVaR problem be solved with one fresh loss per agent per round and almost sure convergence of the actual decisions to an exact optimum? This sharpens the pair question to query and communication cost. Q's §Pricing the Prediction (lines 1235-1258) asks for charged calls; P's §CVaR (lines 327-339) supplies the auxiliary threshold. P's §Distributed risk-averse algorithm (lines 393-440) instead estimates CVaR from a batch, and its fixed-radius last-iterate guarantee (lines 854-978) has a smoothing and finite-sample residual.

The joint \((x,\tau)\) one-point estimator itself is already in [Cardoso and Xu (2019), Algorithm 1 and Theorem 2](https://proceedings.mlr.press/v89/cardoso19a/cardoso19a.pdf). [Li and Assaad (2021)](https://arxiv.org/pdf/2105.12597) analyze one-point distributed zeroth-order optimization on time-varying networks for general convex expected objectives, including an \(O(T^{-1/4})\) averaged error. Their local objectives do not have P's private auxiliary thresholds. I have not established that the last-iterate claim below is absent from other work. The searches were `distributed CVaR bandit zeroth order one point almost sure convergence time varying network auxiliary threshold`, `decentralized risk averse CVaR bandit stochastic convex optimization one sample last iterate convergence`, and `distributed stochastic convex optimization diminishing smoothing radius one point bandit almost sure convergence time varying graphs`.

## Algorithm and conditions

Agent \(i\) keeps \(x_k^i\) and a private threshold \(\tau_k^i\in[-U_i,U_i]\). It mixes only \(x\) with P's doubly stochastic graph matrix, obtaining \(y_k^i\). It draws \(u_k^i\) uniformly on the sphere in \(\mathbb R^{d+1}\), queries one \(J^i(y_k^i+\delta_k u_{x,k}^i,\xi_k^i)\), and forms the joint estimator from emmy/lifted-threshold.md:

\[
g_k^i=\frac{d+1}{\delta_k}\left[\tau_k^i+\delta_k u_{\tau,k}^i+\frac{(J^i(y_k^i+\delta_k u_{x,k}^i,\xi_k^i)-\tau_k^i-\delta_k u_{\tau,k}^i)_+}{\alpha_i}\right]u_k^i.
\]

Project the stored \(x\) onto P's shrunken set \(\mathcal X_{\delta_k}\) and the stored threshold onto \([-U_i,U_i]\) after a step of length \(\eta_k\). A technical set-change detail must be checked: the next iteration starts in \(\mathcal X_{\delta_k}\), which is contained in \(\mathcal X_{\delta_{k+1}}\) for decreasing \(\delta_k\), so its next perturbed query is feasible.

Use \(\delta_k=c_\delta(k+1)^{-p}\) and \(\eta_k=c_\eta(k+1)^{-q}\), with \(0<p<q\le1\), \(q+p>1\), and \(q-p>1/2\). For example, \(p=1/4\), \(q=5/6\) satisfy all three inequalities. These give

\[
\sum_k\eta_k=\infty,\qquad
\sum_k\eta_k\delta_k<\infty,\qquad
\sum_k\eta_k^2/\delta_k^2<\infty.
\]

## Proof obligations

For \(H_i(x,\tau,\xi)=\tau+\alpha_i^{-1}(J^i(x,\xi)-\tau)_+\), the sphere identity makes \(\mathbb E[g_k^i\mid\mathcal F_k]\) the gradient of the same jointly ball-smoothed \(\Phi_{i,\delta_k}\). Bounded losses give \(\|g_k^i\|\le C_i/\delta_k\) pathwise. This is the known Cardoso--Xu device, with a varying radius.

Fix an optimal pair \((x^\star,\boldsymbol\tau^\star)\) for the unsmoothed lifted problem. P's feasible-set shrinkage gives a moving comparator \(z_k=(1-\delta_k/r)x^\star\). Its total motion is finite because \(\sum_k\|z_{k+1}-z_k\|\le D_x\delta_0/r\). Double stochasticity and projection yield a conditional product-state potential inequality of the form

\[
\mathbb E[V_{k+1}\mid\mathcal F_k]
\le V_k-2m\eta_k\bigl(\Phi(\bar x_k,\boldsymbol\tau_k)-\Phi^\star\bigr)
+C\left(\eta_k\delta_k+\eta_k D_k+\eta_k^2/\delta_k^2+\delta_k-\delta_{k+1}\right),
\]

where \(V_k=\sum_i\|x_k^i-z_k\|^2+\sum_i|\tau_k^i-\tau_i^\star|^2\), \(\bar x_k=m^{-1}\sum_i x_k^i\), and \(D_k=\sum_i\|x_k^i-\bar x_k\|\). The \(\eta_k\delta_k\) term includes joint smoothing and comparator shrinkage. The \(\eta_k^2/\delta_k^2\) term includes gradient second moments. This display is a proof sketch: constants, conditioning, and exact index placement remain to be written out.

P's geometric graph mixing with \(\|x_{k+1}^i-y_k^i\|\le C\eta_k/\delta_k\) gives

\[
D_k\le C\rho^kD_0+C\sum_{t<k}\rho^{k-1-t}\eta_t/\delta_t.
\]

Thus \(D_k\to0\), and monotonicity of \(\eta_k\) gives \(\sum_k\eta_kD_k<\infty\) from \(\sum_k\eta_k^2/\delta_k<\infty\), which follows from the stronger square-gradient condition above. All positive error terms in the potential inequality are summable. A Robbins--Siegmund argument would make the potential converge and give \(\sum_k\eta_k(\Phi(\bar x_k,\boldsymbol\tau_k)-\Phi^\star)<\infty\). Because \(\sum_k\eta_k=\infty\), the lifted gap has liminf zero. Compactness supplies an optimal cluster point; convergence of the potential for a countable dense set of optimal comparators then yields convergence of the entire product state to an optimal pair, and graph disagreement tending to zero yields exact consensus. This last step needs a careful measurable dense-set argument in a full proof.

If completed, the result would improve P's fixed-sample, fixed-radius last-iterate residual in the same oracle and graph model using one query per round. It would not be a prediction-dependent gain: Q contributes the cost/accounting question, while the core estimator and network machinery already have separate prior art. A predicted threshold changes initialization constants only. The publication case is uncertain unless the exact distributed last-iterate theorem or a sharper communication-query tradeoff is demonstrably new.
