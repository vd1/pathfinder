# F3: function-value route removes the \( e_s/\delta_{\min} \) factor in P, and transfers to Q

Notation of P. For agent \(i\) with sample size \(s\) (fixed or \(s_k^i\) at iteration \(k\)) define the surrogate
\[ \widetilde C^i_s(x) := \mathbb E_{\nu\sim\mathrm{Unif}(\mathbb B)}\,\mathbb E_{\xi^{1:s}}\big[\widehat C^i(x+\delta_i\nu)\big]. \]
P already uses this object (proof of Theorem 3, eq. surrogate-unbiased-gradient): \(\mathbb E[\hat g_k^i\mid\mathcal F_k]=\nabla\widetilde C^i_{s_k^i}(y_k^i)\), and \(\widetilde C^i_s\) is convex and \(L_i\)-Lipschitz.

**Uniform value error.** For every \(x\in\mathcal X_\delta\),
\[ |\widetilde C^i_s(x)-C^i(x)| \le |\widetilde C^i_s(x)-C^i_\delta(x)| + |C^i_\delta(x)-C^i(x)| \le \tfrac{2U_i}{\alpha_i}\sqrt{\tfrac{\pi}{2s}} + L_i\delta_i =: \varepsilon_i(s), \]
using P's Lemma (Wang 2022, Lemma 3) plus DKW exactly as in P's proof of Lemma 4, but applied to values, pointwise in \(x+\delta_i\nu\), before multiplying by \(d/\delta_i\). Averaging with (sampling requirement) gives
\[ \sup_x |\widetilde{\mathcal C}_k(x)-\mathcal C(x)| \le L_{\max}\delta_{\max} + \sqrt{2\pi}\,\max_i\tfrac{U_i}{\alpha_i}\,e_s =: \varepsilon. \]
No factor \(d\), no \(1/\delta_{\min}\).

**Ergodic recursion.** In P's step (Exp <g,y-z>) replace the split \(\hat g=g+e\) by the conditional mean directly:
\[ \mathbb E[\langle\hat g_k^i,y_k^i-z\rangle\mid\mathcal F_k] = \langle\nabla\widetilde C^i_{s_k^i}(y_k^i),y_k^i-z\rangle \ge \widetilde C^i(y_k^i)-\widetilde C^i(z) \ge C^i(y_k^i)-C^i(z)-2\varepsilon_i. \]
Everything else in P's Theorem 1 is unchanged, so \(D_1\) can be replaced by \(2\varepsilon\) (up to the averaging over agents), and \(D_2\) by \(2\varepsilon + D_xL_{\max}\delta_{\max}/r = O(\delta_{\max}+e_s)\). The transient term \(G_{\max}^2\sum\eta_k^2/\sum\eta_k\) still carries \(1/\delta_{\min}^2\); that is where the smoothing/variance trade-off lives.

**Last iterate (fixed \(s^i\)).** \(\bar x_\infty\) minimises \(\widetilde{\mathcal C}\) over \(\mathcal X_\delta\) and \(z_\delta\in\mathcal X_\delta\), so
\[ \mathcal C(\bar x_\infty)-\mathcal C^\ast \le [\mathcal C-\widetilde{\mathcal C}](\bar x_\infty) + \underbrace{\widetilde{\mathcal C}(\bar x_\infty)-\widetilde{\mathcal C}(z_\delta)}_{\le 0} + [\widetilde{\mathcal C}-\mathcal C](z_\delta) + \mathcal C(z_\delta)-\mathcal C^\ast \le 2\varepsilon + \tfrac{D_xL_{\max}\delta_{\max}}{r}. \]
P's route through the gradient mismatch (surrogate-gradient-error) is not needed; it is also the step whose right-hand side is \(d\sqrt{2\pi}\max_i U_i/(\alpha_i\delta_i)\,e_s\), which blows up as \(\delta\to0\). Consequence for P's Remark 4 and Fig. 3 discussion: the limiting neighbourhood is increasing in \(\delta\) only; small \(\delta\) costs transient variance, not asymptotic accuracy.

Caveat to check: P's gradient-mismatch bound (surrogate-gradient-error) is itself stated for the true gradients \(\nabla\widetilde{\mathcal C}\) and \(\nabla\mathcal C_\delta\), which exist because both are smoothed; the value route does not need it at all.

**Transfer to Q.** Q's P2 (Theorem 1 proof, eqs. 10 to 16) and P3 use valuations only through KKT and concavity; the budget-balance computation at a symmetric-price NE of (40) gives, for \(K=1\) and scale \(\alpha\),
\[ t_n(s^\ast) = \alpha\,k_N\,\tilde p\,(x_n^o - c/N),\quad k_N = \tfrac{N}{N-1}+\tfrac{1}{(N-1)^2},\qquad \sum_n t_n(s^\ast) = \alpha k_N\tilde p\,(\textstyle\sum_n x_n^o - c)=0 \]
by complementary slackness, for any valuations. If agents in Q learn with P's one-point estimator on CVaR losses (known quadratic payment, bandit valuation), the learning target is the NE implementing the surrogate welfare \(\sum_n \widetilde V_n\), with \(\widetilde V_n = -\widetilde C^n\) (plus any known regulariser). Then: budget balance exact; welfare loss \(\le 2\sum_n\varepsilon_n\); IR violated by at most \(2\varepsilon_n\) (one \(\varepsilon_n\) from \(|\widetilde V_n-V_n|\) at \(x_n\), one from \(\widetilde V_n(0)\neq0\)). The oracle satisfies Q's Assumption 3(ii) in second-moment form with \(\kappa^n\le dU_n/\delta_n\).

What does not transfer: convergence of the learning dynamics. Q's game induced by (40) is not monotone (F1) and its proximal best response is not nonexpansive in the Euclidean norm (F2), so neither P's descent argument nor Q's Theorem 4 applies as written.
