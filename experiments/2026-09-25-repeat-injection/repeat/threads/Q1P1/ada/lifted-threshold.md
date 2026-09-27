# One-query lifted CVaR on a changing network

## Question and source passages

The sharpened question is whether P's own auxiliary-threshold representation can remove its growing empirical-CVaR batch while retaining a finite-time guarantee on P's time-varying graph. Q motivates charging prediction and sampling calls in §System-Level Implications (lines 968-980) and §Pricing the Prediction (lines 1235-1258); its P5 discussion says no generic coherent-risk guarantee follows from a predicted distribution (lines 599-602). P gives the local Rockafellar--Uryasev representation (§CVaR, lines 327-339) but minimizes the threshold anew inside an empirical CVaR estimate at every perturbed point (lines 404-440). Its gradient then has finite-sample bias (lines 393-400), and its ergodic theorem retains a residual proportional to \(e_s/\delta_{\min}\) (lines 657-721). The proposal below is prediction-free at its core. A predicted threshold can initialize it, but the forecast does not drive the query-rate improvement.

## Lift and one-sample estimator

For each agent \(i\), define

\[
H_i(x,t,\xi)=t+\frac{(J^i(x,\xi)-t)_+}{\alpha_i},
\qquad
\Phi_i(x,t)=\mathbb E_\xi H_i(x,t,\xi).
\]

P's assumptions imply that \(H_i\) is jointly convex in \((x,t)\), is \(L_i/\alpha_i\)-Lipschitz in \(x\), and has a minimizing threshold in \([-U_i,U_i]\). Therefore

\[
\min_{x\in\mathcal X}\frac1m\sum_i C^i(x)
=\min_{x\in\mathcal X,\;t_i\in[-U_i,U_i]}
\frac1m\sum_i\Phi_i(x,t_i).
\]

Agent \(i\) keeps its own threshold \(t_k^i\); only \(x_k^i\) is mixed over P's graph. P's sphere one-point identity cannot pair an x-only perturbation with a threshold indicator for an exact joint smoothed subgradient: its \(x\) update differentiates a ball-smoothed objective while the threshold indicator differentiates a sphere-smoothed one. The clean repair is to perturb the joint variable.

Let \(z=(x,t)\in\mathbb R^{d+1}\), and draw \(u\sim\mathrm{Unif}(\mathbb S^d)\). At the current pair \((y_k^i,t_k^i)\), query one loss \(J_k^i=J^i(y_k^i+\delta_i u_{x,k}^i,\xi_k^i)\), evaluate \(H_i(y_k^i+\delta_i u_{x,k}^i,t_k^i+\delta_i u_{t,k}^i,\xi_k^i)\), and set

\[
g_k^i=\frac{d+1}{\delta_i}
H_i(y_k^i+\delta_i u_{x,k}^i,t_k^i+\delta_i u_{t,k}^i,\xi_k^i)u_k^i.
\]

The usual sphere identity in dimension \(d+1\) makes the conditional mean of this whole vector the gradient of the same jointly ball-smoothed objective. The loss oracle sees only the perturbed \(x\); the perturbed threshold is used in arithmetic. Project the stored pair onto \(\mathcal X_\delta\times[-U_i,U_i]\) after the step. Since \(\|u_x\|\le1\), P's shrinkage argument (lines 480-488) keeps the queried \(x\) feasible. The sampled threshold may lie in \([-U_i-\delta_i,U_i+\delta_i]\), where \(H_i\) remains defined. In fact,

\[
|H_i|\le B_i:=U_i+\delta_i+\frac{2U_i+\delta_i}{\alpha_i},
\qquad
\|g_k^i\|\le\frac{(d+1)B_i}{\delta_i}.
\]

This pathwise cap lets P's geometric mixing argument apply to the shared x coordinates without a new expected-disagreement lemma. The joint objective is \(M_i\)-Lipschitz in \((x,t)\), where \(M_i\le\alpha_i^{-1}\sqrt{L_i^2+1}\), so joint smoothing changes its value by at most \(M_i\delta_i\). A full proof should keep separate the shared x consensus and the local threshold projection; the latter simply telescopes in the product-state Lyapunov function.

### Alternative compact-kernel estimator

The following version perturbs only \(x\) and uses a direct threshold subgradient. It has a finite second moment but no pathwise cap, so the graph proof needs an expected-disagreement bound. It is less convenient as the lead theorem, though it may have lower threshold variance.

Let \(v\) have density \(p(v)=c_d(1-\|v\|^2)^2\) on the open unit ball. Define

\[
\bar\Phi_i(y,t)=\mathbb E_{v,\xi}H_i(y+\delta_i v,t,\xi),
\quad
\psi(v)=-\nabla\log p(v)=\frac{4v}{1-\|v\|^2}.
\]

At each round, mix \(y_k^i=\sum_jw_k^{ij}x_k^j\), sample \(v_k^i\), and make exactly one call to P's noisy loss oracle at \(y_k^i+\delta_i v_k^i\). From the returned value \(J_k^i\), set

\[
g_{x,k}^i
=\frac{(J_k^i-t_k^i)_+}{\alpha_i\delta_i}\psi(v_k^i),
\qquad
g_{t,k}^i
=1-\frac{\mathbf 1\{J_k^i>t_k^i\}}{\alpha_i}.
\]

Update \(x_{k+1}^i=\Pi_{\mathcal X_\delta}(y_k^i-\eta g_{x,k}^i)\) and \(t_{k+1}^i=\Pi_{[-U_i,U_i]}(t_k^i-\eta g_{t,k}^i)\). P's shrinkage argument (lines 480-488) keeps each queried point in \(\mathcal X\). The kernel vanishes at the boundary, so integration by parts gives \(\mathbb E[g_x\mid\mathcal F_k]=\nabla_x\bar\Phi_i(y_k^i,t_k^i)\). The indicator is a valid sample subgradient in \(t\), including at ties, hence its conditional mean is a threshold subgradient of the same \(\bar\Phi_i\). Joint convexity gives the paired subgradient inequality against any \((z,\theta_i)\).

The score has finite second moment despite being unbounded at the boundary:

\[
\mathbb E\|\psi(v)\|^2
=16\frac{\int_0^1r^{d+1}\,dr}
{\int_0^1r^{d-1}(1-r^2)^2\,dr}
=2d(d+4).
\]

Since \((J_k^i-t_k^i)_+\le2U_i\),

\[
\mathbb E[\|g_{x,k}^i\|^2\mid\mathcal F_k]
\le\frac{8d(d+4)U_i^2}{\alpha_i^2\delta_i^2},
\qquad |g_{t,k}^i|\le\alpha_i^{-1}.
\]

This is a moment bound, not a pathwise cap. It requires replacing P's pathwise disagreement estimate (lines 523-538) with an expected one. If \(e_k^i=x_{k+1}^i-y_k^i\), projection nonexpansiveness yields \(\mathbb E\|e_k^i\|\le\eta\sqrt{\mathbb E\|g_{x,k}^i\|^2}\). The same geometric matrix-product estimate P cites then gives steady mean disagreement of order \(\eta/\delta\) for constant \(\eta\), with graph-dependent constants.

## Finite-time consequence and comparison

For the preferred joint-smoothing estimator, use the Lyapunov function \(V_k=\sum_i(\|y_k^i-z\|^2+|t_k^i-\theta_i|^2)\), where \(z\in\mathcal X_\delta\) and \(\theta_i\in[-U_i,U_i]\). Projection, double stochasticity and the joint conditional gradient yield a telescoping bound. Comparing each local \(y_k^i\) with the network average costs at most \((L_i/\alpha_i)\|y_k^i-\bar x_k\|\). Joint smoothing costs at most \(M_i\delta_i\), and P's scaled comparator costs at most \(D_xL_{\max}\delta_{\max}/r\). For uniform \(\delta_i=\delta\) and bounded problem and graph constants, the expected true CVaR gap of the averaged decision has the form

\[
\mathbb E[\mathcal C(\hat x_T)-\mathcal C(x^*)]
\le O\!\left(
\frac{A}{\eta T}
+\frac{B\eta}{\delta^2}
+\frac{M\eta}{\delta}
+\delta
\right),
\]

where \(A\) contains the initial \(x\) and threshold distances, \(B\) contains the second-moment constants above, and \(M\) contains the graph-mixing and Lipschitz constants. The initial graph transient contributes a smaller \(O(1/T)\) term for a fixed graph family. Taking \(\eta\asymp\delta/\sqrt T\) and \(\delta\asymp T^{-1/4}\) yields \(O(T^{-1/4})\) and \(O(m\varepsilon^{-4})\) total noisy loss calls to reach expected gap \(\varepsilon\), up to constants and logarithms. A threshold forecast clipped to \([-U_i,U_i]\) changes \(A\) through its distance from an optimal threshold and cannot invalidate the bound; it should be charged for its inference cost, as Q requests.

For comparison, P's displayed one-point theorem requires a residual \(e_s/\delta\). With \(\delta\asymp\varepsilon\), an equal batch size must scale as \(s\asymp\varepsilon^{-4}\). Horizon-tuned \(\eta\asymp\delta/\sqrt T\) makes its transient order \(1/(\delta\sqrt T)\), giving \(T\asymp\varepsilon^{-4}\) and a displayed upper bound of \(O(m\varepsilon^{-8})\) loss calls. The comparison is between sufficient conditions from these analyses, not a lower bound on P. A two-point common-random-number method may improve further if the oracle exposes the same scenario at two decision points; P only specifies independent sampled noisy evaluations and does not promise this access.

## Status and prior work

The main estimator above is already known. [Cardoso and Xu, *Risk-Averse Stochastic Convex Bandit*](https://proceedings.mlr.press/v89/cardoso19a/cardoso19a.pdf), Algorithm 1 and Theorem 2 on pp. 3-4, use the same joint \((x,t)\) sphere perturbation, one observed loss, and \(O(T^{-1/4})\) rate. Their setting is centralized stochastic bandit optimization. The remaining extension is a complete product-state proof on P's time-varying communication graph, with explicit communication and loss-query costs. P's graph estimates make this plausible, but the extension may be too routine for a publication on its own. The compact-kernel version above is a variant of a standard score estimator, not an established novelty claim. A scalar prediction baseline is also weak because prior residual-feedback CVaR work exists in [Wang, Shen and Zavlanos](https://arxiv.org/abs/2203.08957).

### A limit of threshold-only advice

A stronger version of emmy's two-world example quantifies the need for tail observations. Fix one agent and \(\mathcal X=[-1,1]\). Each oracle call draws independent \(E\sim\mathrm{Bernoulli}(\alpha)\) and \(S\in\{-1,+1\}\), with \(\Pr_\pm(S=+1)=1/2\pm\gamma\), and returns

\[
J(x,E,S)=E\frac{1+Sx}{2}.
\]

Both worlds satisfy P's convexity, boundedness and Lipschitz assumptions. Both have exact lower \((1-\alpha)\)-quantile \(0\) for every \(x\), so even a perfect threshold predictor reveals no world information. Yet \(C_\pm(x)=1/2\pm\gamma x\), with opposite optimal endpoints. A loss observation is a function of the latent \((E,S)\). For every adaptively selected \(x\), data processing bounds its conditional KL divergence by

\[
\alpha D\!\left(\mathrm{Bern}(1/2+\gamma)\,\middle\|\,
\mathrm{Bern}(1/2-\gamma)\right)
\le16\alpha\gamma^2
\quad(0<\gamma\le1/4).
\]

The factor \(\alpha\) follows because the observation is a function of the censored pair \((E,ES)\); when \(E=0\), no information about \(S\) is exposed. The KL chain rule then gives transcript divergence at most \(16n\alpha\gamma^2\) after \(n\) calls. If \(n\le1/(32\alpha\gamma^2)\), Pinsker gives total variation at most \(1/2\). For any output \(\hat x\in[-1,1]\), the average of the expected gaps in the two worlds is \(\gamma[1+(\mathbb E_+\hat x-\mathbb E_-\hat x)/2]\ge\gamma(1-\mathrm{TV})\ge\gamma/2\). Taking \(\gamma=2\varepsilon\) proves a worst-world lower bound of \(\Omega(1/(\alpha\varepsilon^2))\) calls to achieve expected gap below \(\varepsilon\) with exact quantile advice. This does not match the \(\varepsilon^{-4}\) upper bound, and it says nothing about advice that reveals tail magnitudes.

Additional relevant primary literature includes [Wang et al., *A Zeroth-Order Momentum Method for Risk-Averse Online Convex Games*](https://arxiv.org/abs/2209.02838). Search queries included `CVaR zeroth-order Rockafellar one sample`, `CVaR bandit auxiliary convex threshold`, and `distributed CVaR optimization zeroth order auxiliary VaR variable one sample stochastic approximation`. These searches found direct centralized prior work and do not establish novelty for the dynamic-network extension.
