# F5: almost-sure convergence of bandit CVaR play on payment (40), including the common price level

Answers the action in verifier #18. Numerics: emmy/F5_sim.py, emmy/F5_sim.out. IR check: emmy/F5_ir_check.py, .out.

## Setting and hypotheses

\(K=1\). Agent \(n\) has quantity set \(\mathcal X_n=[a_n,b_n]\) and loss \(J^n(x,\xi)\) (Q's satisfaction is \(-J^n\)). The risk-adjusted valuation is \(V_n=-C^n\), \(C^n(x)=\mathrm{CVaR}_{\alpha_n}[J^n(x,\xi)]\). Agents use P's one-point estimator with a fixed batch \(s_n\) and radius \(\delta_n\), and play on the shrunk interval \(\mathcal X_{n,\delta}=[a_n+\delta_n,b_n-\delta_n]\), so every queried point \(x+\delta_nu\) lies in \(\mathcal X_n\). Prices live in \([0,P_{\max}]\) (Q Assumption 3). The payment (40) is known and its gradient is computed exactly from the announced aggregates.

Surrogate valuation: \(\widetilde V_n(x):=-\mathbb E_{\nu}\mathbb E_{\xi^{1:s_n}}\widehat C^n(x+\delta_n\nu)\). P (proof of Theorem 3, eq. surrogate-unbiased-gradient) gives \(\mathbb E[\hat g^n_k\mid\mathcal F_k]=-\nabla\widetilde V_n(x^n_k)\), and \(|\hat g^n_k|\le U_n/\delta_n\) almost surely (P eq. gradient bound with \(d=1\)).

- (H1) Per-sample curvature floor: for every \(\xi\), \(x\mapsto J^n(x,\xi)-\tfrac{h}{2}x^2\) is convex on \(\mathcal X_n\), with \(h>c_N^2/(4\alpha)\), \(c_N=\alpha(2N-1)/(N-1)^2\) (the threshold of ada A1).
- (H2) Every \(J^n(\cdot,\xi)\) is \(L_n\)-Lipschitz and \(|J^n|\le U_n\) (P Assumption 3).
- (H3) At the surrogate equilibrium \(s^\ast\) at least one agent \(n_0\) has \(x^\ast_{n_0}\) in the interior of \(\mathcal X_{n_0,\delta}\), and \(P_{\max}\) exceeds every equilibrium price.
- (H4) \(\eta_k>0\), \(\sum_k\eta_k=\infty\), \(\sum_k\eta_k^2<\infty\).

Iteration (plain projected pseudo-gradient play, simultaneous):
\[ s^{k+1}=\Pi_{\mathcal S_\delta}\big[s^k+\eta_k(F(s^k)+\zeta^k)\big],\qquad \mathcal S_\delta=\textstyle\prod_n\mathcal X_{n,\delta}\times[0,P_{\max}]^N, \]
where \(F\) is the pseudo-gradient of the surrogate game (valuations \(\widetilde V_n\), payment (40)) and \(\zeta^k\) has zero x-block conditional mean given \(\mathcal F_k\), zero p-block, and \(\|\zeta^k\|\le B_\zeta\) almost surely.

## Step 0: the surrogate inherits the floor

By translation equivariance, \(\mathrm{CVaR}[J(x,\xi)]-\tfrac h2x^2=\mathrm{CVaR}[J(x,\xi)-\tfrac h2x^2]\), and CVaR of a per-sample convex family is convex (monotone and convex risk measure). The same holds for the empirical distribution of any batch. Averaging over the batch and over \(\nu\) keeps \(h\)-strong convexity. So \(-\widetilde V_n\) is \(h\)-strongly convex and \(C^1\) (smoothing of a Lipschitz function). A floor that holds only in mean is not inherited (ada A2 counterexample), which is why (H1) is per sample.

## Step 1: weighted monotonicity and uniqueness

With \(W=\mathrm{diag}(I_x,wI_p)\), \(w=(N-1)/N\), \(\Pi=I-\mathbf 1\mathbf 1^\top/N\), the payment part of \(F\) is affine and (ada A1, rechecked: the xp block of \(WJ+J^\top W\) is \(c_N\Pi\), the pp block is \(-2\alpha\Pi\)) for all \(s,s'\in\mathcal S_\delta\), \(\Delta=s-s'\),
\[ \langle F(s)-F(s'),W\Delta\rangle\le-h\|\Delta x\|^2+c_N\,\Delta x^\top\Pi\Delta p-\alpha\|\Pi\Delta p\|^2\le-\varepsilon\big(\|\Delta x\|^2+\|\Pi\Delta p\|^2\big), \]
\(\varepsilon=\tfrac12\big(h+\alpha-\sqrt{(h-\alpha)^2+c_N^2}\big)>0\) by (H1). Only the valuation part of \(F\) is nonlinear, and it enters through \(\langle\nabla\widetilde V(x)-\nabla\widetilde V(x'),\Delta x\rangle\le-h\|\Delta x\|^2\), so no Hessian is needed.

Existence: \(F\) is continuous on the compact convex \(\mathcal S_\delta\), so the variational inequality has a solution, and each agent's utility is concave in its own strategy (\(J_{nn}=\begin{pmatrix}-h&\alpha/(N-1)\\ \alpha/(N-1)&-\alpha\end{pmatrix}\preceq0\) since \(h\alpha\ge\alpha^2/(N-1)^2\) follows from (H1)), so VI solutions are Nash equilibria. Uniqueness: two equilibria satisfy \(\langle F(s')-F(s^\ast),W(s'-s^\ast)\rangle\ge0\) (the blockwise VI is invariant under block-scalar \(W\)), hence \(x'=x^\ast\) and \(p'=p^\ast+v\mathbf 1\). For (40), \(F_{x,n}(s')-F_{x,n}(s^\ast)=-\alpha v\), and for the interior agent \(n_0\) both residuals vanish, so \(v=0\). This replaces Q Proposition 1, whose LMI is infeasible (emmy F1).

## Step 2: Robbins–Siegmund in the W-norm

\(\mathcal S_\delta\) is a product of intervals and \(W\) is scalar on each coordinate, so the Euclidean projection onto \(\mathcal S_\delta\) is the \(W\)-projection and is \(W\)-nonexpansive; the equilibrium satisfies \(s^\ast=\Pi_{\mathcal S_\delta}[s^\ast+\eta F(s^\ast)]\). With \(\Delta_k=s^k-s^\ast\),
\[ \|\Delta_{k+1}\|_W^2\le\|\Delta_k\|_W^2+2\eta_k\langle F(s^k)-F(s^\ast),W\Delta_k\rangle+2\eta_k\langle\zeta^k,W\Delta_k\rangle+\eta_k^2\|F(s^k)-F(s^\ast)+\zeta^k\|_W^2 . \]
Taking \(\mathbb E[\cdot\mid\mathcal F_k]\) and using Step 1 and the a.s. bound \(\|F(s^k)+\zeta^k\|\le B\) on the compact set:
\[ \mathbb E\big[\|\Delta_{k+1}\|_W^2\mid\mathcal F_k\big]\le\|\Delta_k\|_W^2-2\eta_k\varepsilon\,\phi(s^k)+4\eta_k^2B^2,\qquad \phi(s):=\|x-x^\ast\|^2+\|\Pi(p-p^\ast)\|^2 . \]
Robbins–Siegmund and (H4): \(\|\Delta_k\|_W\to R\) a.s. for a finite random \(R\), and \(\sum_k\eta_k\phi(s^k)<\infty\) a.s.

## Step 3: \(\phi(s^k)\to0\) almost surely

\(\phi\) is Lipschitz on \(\mathcal S_\delta\) with some constant \(L_\phi\), and \(\|s^{k+1}-s^k\|\le\eta_kB\), so \(|\phi(s^{k+1})-\phi(s^k)|\le L_\phi B\eta_k\). Fix a sample path with \(\sum\eta_k\phi_k<\infty\). Then \(\liminf\phi_k=0\), since \(\sum\eta_k=\infty\). If \(\limsup\phi_k>2\epsilon\), there are infinitely many disjoint index intervals \([k_1,k_2]\) with \(\phi_{k_1}<\epsilon\), \(\phi_{k_2}>2\epsilon\), \(\phi_k\ge\epsilon\) on \((k_1,k_2]\). On each, \(\epsilon<\phi_{k_2}-\phi_{k_1}\le L_\phi B\sum_{k=k_1}^{k_2-1}\eta_k\), so \(\sum_{k=k_1+1}^{k_2}\eta_k\phi_k\ge\epsilon\big(\epsilon/(L_\phi B)-\eta_{k_1}\big)\), which is at least \(\epsilon^2/(2L_\phi B)\) once \(\eta_{k_1}\) is small. Summing over infinitely many intervals contradicts \(\sum\eta_k\phi_k<\infty\). Hence \(x^k\to x^\ast\) and \(\Pi p^k\to\Pi p^\ast\) a.s. The a.s. boundedness of the step is where P's estimator helps: its bound \(U_n/\delta_n\) holds pathwise, not only in mean square.

## Step 4: the common price level

Write \(v_k=\mathbf 1^\top p^k/N\). Since \(\|\Delta_k\|_W^2=\|x^k-x^\ast\|^2+w\|\Pi(p^k-p^\ast)\|^2+wN(v_k-v^\ast)^2\) and the first two terms vanish, \(|v_k-v^\ast|\to\rho:=R/\sqrt{wN}\) a.s. Suppose \(\rho>0\) on some path. Because \(|v_{k+1}-v_k|\le B\eta_k\to0\), the sign of \(v_k-v^\ast\) is eventually constant, say \(v_k\to v^\ast+\sigma\rho\) with \(\sigma\in\{\pm1\}\). Then \(s^k\to s^\ast+\sigma\rho\,(0,\mathbf 1)\), and by continuity and the affine price dependence of (40),
\[ F_{x,n_0}(s^k)\to F_{x,n_0}(s^\ast)-\alpha\sigma\rho=-\alpha\sigma\rho\neq0 . \]
Since \(x^k_{n_0}\to x^\ast_{n_0}\) in the interior of \(\mathcal X_{n_0,\delta}\) and steps are \(O(\eta_k)\), the projection is inactive for the agent \(n_0\) quantity from some \(K\) on, so
\[ x^{k+1}_{n_0}-x^K_{n_0}=\sum_{j=K}^{k}\eta_jF_{x,n_0}(s^j)+\sum_{j=K}^{k}\eta_j\zeta^j_{x,n_0} . \]
The left side is bounded. The martingale \(\sum_j\eta_j\zeta^j_{x,n_0}\) has square-summable bounded increments and converges a.s. The first sum diverges because its summands tend to \(-\alpha\sigma\rho\neq0\) and \(\sum\eta_j=\infty\). Contradiction on a probability-one set of paths, so \(\rho=0\) and \(s^k\to s^\ast\) almost surely.

**Theorem (F5).** Under (H1)–(H4), plain projected pseudo-gradient play on the game of payment (40), with valuations accessed only through P's fixed-batch one-point CVaR estimator on the shrunk box, converges almost surely to the unique Nash equilibrium of the surrogate game, including the common price level. That equilibrium implements \(\max\sum_n\widetilde V_n\) under the coupling constraint (Q Theorem 1 applied to the surrogate), and its allocation satisfies \(\|\tilde x-x^o_\delta\|\le2\sqrt{\sum_n\varepsilon_n/h}\) relative to the true-CVaR optimum on the shrunk box (ada A5(4)), \(\varepsilon_n=L_n\delta_n+\tfrac{2U_n}{\alpha_n}\sqrt{\pi/(2s_n)}\).

What the proof does not give: a rate (the price level is pinned only through the interior agent quantity equation, the Arrow–Hurwicz situation), and anything when every agent sits at a bound at the equilibrium (then the level can be non-unique, Step 1). The per-agent cross metric of F4 section 4 gives a linear rate for the noise-free interior problem only.

## Numerical check (emmy/F5_sim.out)

Instance: \(N=5\), \(\alpha=0.8\), \(h_n\in[1.16,2.24]\) (threshold 0.063), \(\mathcal X_n=[0,5]\), \(c=9\), loss \(\tfrac{h_n}{2}(y-\tilde x_n)^2+\xi y-\kappa_n\), \(\xi\sim U(-2,2)\), CVaR at upper-tail level 1/2, \(\delta=0.2\), quantities projected onto \([0.2,4.8]\). At the surrogate equilibrium agents 1 to 3 are interior, agent 4 is at the lower bound, agent 5 is at the upper bound, and the coupling is active. The surrogate is available in closed form: \(\nabla\widetilde C^n(y)=h_n(y-\tilde x_n)+m_s\), \(m_s=\mathbb E[\text{mean of the top }s/2\text{ of }s\text{ draws}]=2\cdot\tfrac{s/2}{s+1}\), against \(m=1\) for the true CVaR. The constants \(\kappa_n\) only reduce the variance of the one-point estimator; they do not change either equilibrium. Plain projected play, \(\eta_k=0.5/(k+100)^{0.6}\), four seeds, tail window \([H/2,H)\); the table reports the distance of the tail-mean iterate, quantities and common price level separately.

| batch | H | \(\|\bar x-x_{\rm sur}\|\) | \(\lvert\bar v-p_{\rm sur}\rvert\) | \(\|\bar x-x_{\rm true}\|\) | \(\lvert\bar v-p_{\rm true}\rvert\) |
|---|---|---|---|---|---|
| s=4 | 1e4 | 0.194 | 0.119 | 0.428 | 0.131 |
| s=4 | 1e5 | 0.061 | 0.042 | 0.323 | 0.209 |
| s=4 | 1e6 | 0.019 | 0.015 | 0.295 | 0.235 |
| s=64 | 1e4 | 0.016 | 0.008 | 0.291 | 0.011 |
| s=64 | 1e5 | 0.004 | 0.002 | 0.285 | 0.019 |
| s=64 | 1e6 | 0.003 | 0.001 | 0.285 | 0.018 |

Surrogate versus true gaps: 0.283 in quantities (the box shrink, both batches) and 0.250 (s=4) or 0.019 (s=64) in price. The iterates approach the surrogate equilibrium, including the price level, and the distance to the true-CVaR equilibrium settles at the surrogate gap. Price disagreement \(\|\Pi\bar p\|\) is zero to four digits because the price block carries no noise. In this instance the finite-sample CVaR bias is the same additive shift \(m-m_s\) in every agent's marginal value, so the mechanism puts all of it into the price level, \((m-m_s)/\alpha\), and interior quantities are unbiased. Quantity bias needs heterogeneous estimator bias across agents.

## Corrections to earlier emmy numbers and claims

1. The 0.42 in emmy/saddle_check.out is not a Euclidean distance. Line 83 of saddle_check.py prints \(\|\bar x-x^\ast\|+\|\bar p-p^\ast\|\), a sum of the two norms. From the printed means, the quantity part is 0.119 and the price part is \(\sqrt5\cdot0.136=0.304\), so the linear split 0.12 plus 0.30 is right for that number, and the Euclidean distance is \(\sqrt{0.119^2+0.304^2}=0.326\). The verifier's quadrature split (quantity part about 0.29) assumed the number was Euclidean. That run also let queried points \(x\pm\delta\) leave \([0,5]\) for the two agents at the lower bound, where \(\xi y\) flips sign, so its target was not P's surrogate. It is superseded by F5_sim.out.

2. IR does not transfer, because (40) is not IR. For (40), \(a^n_n=\alpha c/(N-1)\) and \(a^n_m=-\alpha c/(N(N-1))\), so \(\sum_ma^n_m=\alpha c/(N(N-1))>0\), violating Q P4(ii); Proposition 2 of Q is false on P4 as well as on P1. At the symmetric-price equilibrium \(t_n=k_N\lambda^o(x^o_n-c/N)\) with \(k_N=N/(N-1)+1/(N-1)^2\) (checked against the full formula in F5_ir_check.out), and concavity gives \(V_n(x^o_n)\ge\lambda^ox^o_n\), so
\[ U_n(s^\ast)\ge\lambda^o\big[k_Nc/N-(k_N-1)x^o_n\big]\ge0\quad\text{whenever}\quad x^o_n\le c\,\frac{N^2-N+1}{N^2}. \]
The condition is also close to necessary for near-linear valuations: with \(h=\alpha=0.05\), \(c=1\), \(\lambda^o=1\) and one agent taking 0.92 of the capacity, \(U_1=-0.319,-0.086,-0.004\) for \(N=2,3,5\), and a grid search finds no profitable deviation for that agent, so the point is a Nash equilibrium with negative utility. So a share of at most \((N^2-N+1)/N^2\) for every agent is sufficient for IR of (40), and IR fails in examples above it; this is not a characterisation. F3b's "IR violated by at most \(2\varepsilon_n\)" must be restated as: the surrogate equilibrium utility is within \(2\varepsilon_n\) (plus the allocation shift) of the true one, and the share condition above transfers with slack \(2\varepsilon_n/\lambda^o\).
