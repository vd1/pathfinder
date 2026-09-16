# F4: learning in the game of payment (40): what ada's metric buys, and what is left

Setting as in ada/weighted_monotone.md: K = 1, payment (40) of Q with scale \(\alpha\), valuation Hessians \(-\mathrm{diag}(h)\), \(h_n\ge h_{\min}\), strategy sets \(\mathcal S_n=\mathcal X_n\times[0,P_{\max}]\), pseudo-gradient \(F\), \(W=\mathrm{diag}(I_x,wI_p)\), \(w=(N-1)/N\), \(\Pi=I-\mathbf 1\mathbf 1^\top/N\), \(c_N=\alpha(2N-1)/(N-1)^2\). ada A1: if \(h_{\min}>c_N^2/(4\alpha)\) there is \(\varepsilon>0\) with
\[\langle F(s)-F(s'),W(s-s')\rangle\le-\varepsilon\big(\|x-x'\|^2+\|\Pi(p-p')\|^2\big).\]

## 1. No preconditioning is needed (correction of the remark in ada #7)

Iteration \(s^{k+1}=\Pi_{\mathcal S}[s^k+\eta_kMG^k]\) with \(M\) positive and scalar on each x block and each p block, Lyapunov \(\|\cdot\|_Q^2\) with \(Q\) of the same form. Because \(\mathcal S\) is a product of the per-agent x sets and p sets and \(Q\) is scalar on each factor, the Euclidean projection equals the \(Q\)-projection, and \(s^\ast=\Pi^Q_{\mathcal S}[s^\ast+\eta MF(s^\ast)]\) iff \(\langle QMF(s^\ast),s-s^\ast\rangle\le0\) for all \(s\), which for block-scalar \(QM\) is the same as the NE variational inequality. Nonexpansiveness of \(\Pi^Q\) gives
\[\|s^{k+1}-s^\ast\|_Q^2\le\|\Delta_k\|_Q^2+2\eta_k\,\Delta_k^\top QM\,(G^k-F(s^\ast))+\eta_k^2\|M(G^k-F(s^\ast))\|_Q^2 .\]
The cross term is the W-monotone quantity whenever \(QM=W\). So plain projected play (\(M=I\), \(Q=W\)), price steps scaled by \((N-1)/N\) (\(M=W\), \(Q=I\)) and ada's \(N/(N-1)\) scaling (\(M=W^{-1}\), \(Q=W^2\)) are all covered. This explains ada A4: preconditioning made no visible difference.

## 2. Robbins–Siegmund step with P's estimator

With a fixed batch size, P gives \(\mathbb E[\hat g^n_k\mid\mathcal F_k]=\nabla\widetilde V_n(x^n_k)\) with \(\widetilde V_n=-\widetilde C^n\) (the expected smoothed empirical CVaR) and \(\|\hat g^n_k\|\le dU_n/\delta_n\). The payment part of \(F\) is computed exactly from announced aggregates. So for the surrogate game (valuations \(\widetilde V_n\)) the noise is a martingale difference with bounded second moment, and
\[\mathbb E\big[\|\Delta_{k+1}\|_W^2\mid\mathcal F_k\big]\le\|\Delta_k\|_W^2-2\eta_k\varepsilon\big(\|x_k-x^\ast\|^2+\|\Pi(p_k-p^\ast)\|^2\big)+\eta_k^2C .\]
Needed: \(\widetilde V_n\) keeps the curvature floor. Smoothing over the ball and the expectation over batches preserve a sample-wise floor; a floor only in mean is lost (ada A2 counterexample). Robbins–Siegmund with \(\sum\eta_k=\infty\), \(\sum\eta_k^2<\infty\): \(\|\Delta_k\|_W\) converges a.s. and \(\sum_k\eta_k(\|x_k-x^\ast\|^2+\|\Pi(p_k-p^\ast)\|^2)<\infty\) a.s.

## 3. The common price level (the part a proof still has to supply)

Write \(p=\Pi p+v\mathbf 1\). The monotonicity is flat in \(v\). Two facts close the gap in the interior case, and I have not written the full stochastic argument.

(a) Uniqueness of the NE, which Q's Proposition 1 does not deliver because its LMI is infeasible (F1). If \(s^\ast,s'\) are both NE, the VI and A1 give \(x'=x^\ast\) and \(p'=p^\ast+v\mathbf 1\). For (40), \(F_x(s')-F_x(s^\ast)=J^{xp}\mathbf 1v=-\alpha v\mathbf 1\). If at least one agent has \(x^\ast_n\) in the interior of \(\mathcal X_n\), both x residuals of that agent vanish, so \(v=0\). Condition used: one interior quantity (a Slater-type condition). Without it (all quantities at bounds) the price level can be non-unique, and that is a real degeneracy, not a proof artefact.

(b) Convergence. The ODE method for projected stochastic approximation (Kushner–Yin) sends the iterates to invariant sets of the projected flow \(\dot s=\Pi_{T_{\mathcal S}(s)}F(s)\). Along the flow \(\tfrac{d}{dt}\tfrac12\|s-s^\ast\|_W^2\le-\varepsilon(\|x-x^\ast\|^2+\|\Pi(p-p^\ast)\|^2)\). By LaSalle, the invariant set lies in \(\{x=x^\ast,\Pi p=\Pi p^\ast\}\). On this set the x drift of an interior agent is \(-\alpha v\), which is nonzero unless \(v=v^\ast\). So the only invariant point is \(s^\ast\). This is the standard primal–dual (Arrow–Hurwicz) picture: the price level plays the role of the multiplier and is pinned only through the quantity equations. It gives a.s. convergence but no rate from monotonicity alone.

## 4. A strict metric exists, but only in the interior

Take the per-agent metric \(P_n=\begin{pmatrix}1&e\\ e&w\end{pmatrix}\), the same for every agent. For homogeneous \(h\) the matrix \(J\) splits into a consensus \(2\times2\) block \(\begin{pmatrix}-h&-\alpha\\ \alpha r&0\end{pmatrix}\), \(r=N/(N-1)\), and \(N-1\) disagreement blocks \(\begin{pmatrix}-h&c_N\\0&-\alpha r\end{pmatrix}\). On the price level \(z=(0,\mathbf 1v)\) one gets \(z^\top(PJ+J^\top P)z=-2eN\alpha v^2<0\) for \(e>0\). A grid search (emmy/saddle_check.py, \(h=\alpha=1\)) gives a strong-monotonicity modulus of about 0.55 for N = 3, 10, 50, 500, at \(e\approx0.4\) to \(0.5\), with \(w\) between 0.9 and 1.5. The modulus does not depend on N. This is the Qu–Li cross-term Lyapunov construction for primal–dual dynamics, and it is an LMI in \((e,w)\) for a fixed payment, in the spirit of Q. Caveat: \(P_n\) couples \(x_n\) with \(p_n\), so the \(P\)-projection no longer reproduces the NE VI when a quantity or price bound is active. The linear rate therefore holds only for interior equilibria (locally, or for unconstrained play). Under active bounds, section 3 is all we have.

## 5. Numerics (emmy/saddle_check.out)

Setup: N = 5, \(\alpha=0.8\), \(h_n\sim U[\alpha,3\alpha]\), \(x\in[0,5]\), with two agents at the lower bound and one near the upper. Price steps scaled by \(N/(N-1)\), \(\eta_k=0.5/(k+10)^{0.6}\).

- Noise-free play with the coupling constraint active (\(p^\ast=6.25\)): \(\|s_k-s^\ast\|\) is \(9\cdot10^{-4}\), \(3\cdot10^{-10}\) and \(2\cdot10^{-12}\) at \(k=10^3,10^4,10^5\). With the coupling slack (\(p^\ast=0\)): \(3\cdot10^{-9}\) at \(10^3\).
- Additive noise with \(\sigma=1\): the distance falls to \(10^{-2}\) (active) and \(6\cdot10^{-4}\) (slack) by \(2\cdot10^5\).
- P's one-point CVaR estimator (\(\delta=0.3\), \(s=64\), loss \(\tfrac h2(x-\tilde x)^2+\xi x\), \(\xi\sim U(-2,2)\), CVaR level 1/2): after \(4\cdot10^5\) steps the mean of the last \(10^5\) iterates is 0.42 from the true-CVaR NE, and prices agree across agents. The spread is still large (std 0.53 in x), so this run does not separate the \(O(\delta+1/\sqrt s)\) bias from unfinished variance decay. Inconclusive on the bias size.
