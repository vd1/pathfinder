# Payment (40) of Q is monotone in a fixed diagonal metric

Setting: K = 1 (Kronecker with I_K for general K), N agents, payment (40) with scale \(\alpha\), valuation Hessians \(\nabla^2 V_n(x_n) = -h_n(x_n)\). Pseudo-gradient \(F_n = (\partial_{x_n}U_n, \partial_{p_n}U_n)\), Jacobian J (ordering x then p). Π := I − 11ᵀ/N.

Blocks of J (from (40)):
- xx: −diag(h)
- xp: diagonal \(\alpha/(N-1)\), off-diagonal \(-\alpha N/(N-1)^2\)
- px: every entry \(\alpha/(N-1)\), i.e. \(\tfrac{\alpha}{N-1}\mathbf 1\mathbf 1^\top\)
- pp: diagonal \(-\alpha\), off-diagonal \(\alpha/(N-1)\), i.e. \(-\tfrac{\alpha N}{N-1}\Pi\)

Metric \(W = \mathrm{diag}(I, wI)\), \(w = (N-1)/N\). Then \(S := WJ + J^\top W\) has
- xx: \(-2\,\mathrm{diag}(h)\)
- pp: \(2w\cdot(-\tfrac{\alpha N}{N-1})\Pi = -2\alpha\Pi\)
- xp: \(J^{xp} + w (J^{px})^\top = \alpha\big(\tfrac{1}{N-1}+\tfrac{N}{(N-1)^2}\big)I + \alpha\big(\tfrac1N-\tfrac{N}{(N-1)^2}\big)\mathbf 1\mathbf 1^\top = c\,\Pi\), with \(c = \alpha(2N-1)/(N-1)^2\).

So \(S = \begin{pmatrix}-2H & c\Pi\\ c\Pi & -2\alpha\Pi\end{pmatrix}\). With \(q=\Pi p\):
\(z^\top S z = -2x^\top Hx + 2c\,x^\top q - 2\alpha\|q\|^2 \le 0\) for all x, q iff \(H \succeq \tfrac{c^2}{4\alpha} I\) (Schur complement in q).

Claim. If every valuation satisfies \(\nabla^2 V_n \preceq -h_{\min} I\) with
\[ h_{\min} \ge \frac{\alpha(2N-1)^2}{4(N-1)^4}, \]
then \(\langle F(s)-F(s'), W(s-s')\rangle \le 0\) for all s, s' (integrate S along the segment), strictly unless \(x=x'\) and \(p-p'\in\mathrm{span}(\mathbf 1)\) (strict version: replace \(h_{\min}\) by \(h_{\min}+\epsilon\)). With Q's Assumption 2 (\(h_{\min}=\alpha\)) the condition holds iff \(N\ge3\). For large N the required curvature is about \(\alpha/N^2\).

The only flat direction is the common price level. It is not a null direction of J: \(J(0,\mathbf 1v) = (-\alpha\mathbf 1 v, 0)\), so the level is pinned through the quantity equations (\(\nabla V_n = \alpha\tilde p\) at the NE), exactly as a dual variable in a Lagrangian saddle. On span\((\mathbf 1)\) the W-weighted block is exactly skew: \(\begin{pmatrix}-h & -\alpha\\ \alpha & 0\end{pmatrix}\).

Numerical confirmation (check2.py, check2.out): 200 draws of \(h_n\sim U[\alpha,3\alpha]\), N ∈ {3, 10, 50}: \(\lambda_{\max}(WJ+J^\top W)\le 10^{-14}\) while \(\lambda_{\max}(J+J^\top) = 0.106, 0.0043, 0.00013\).

## Assumption 5 of Q fails along the price level for every μ (N ≥ 3)

Interior linearisation \(T = (\mu I - D)^{-1}(\mu I + J - D)\), \(D\) the per-agent 2x2 blocks \(\begin{pmatrix}-h & \theta\\ \theta & -a\end{pmatrix}\), for the family with \(A^n_{nn}=a\), \(B^n_{nl}=-\theta\), \(\zeta=\sum_m B^n_{mn}\), \(\sum_m A^n_{nm}=0\). For \(z=(0,\mathbf 1 v)\): \(Jz=(-\zeta\mathbf 1v,0)\), \(\det=(\mu+h)(\mu+a)-\theta^2\),
\[ \frac{\|Tz\|^2}{\|z\|^2}-1 = \frac{\zeta^2\big((\mu+a)^2+\theta^2\big)-2\zeta\theta\det}{\det^2}. \]
For (40) (\(\zeta=a=h=\alpha\), \(\theta=\alpha/(N-1)\)) the numerator is positive for every \(\mu>0\) when \(N\ge3\); for N = 2 it is positive iff \((\mu+\alpha)^2<3\alpha^2\). Numerics in check2.out agree (ratio > 1 for μ up to 1000, tending to 1). So Q's remark (μ ≥ Nα/(N−1) suffices) is false in the Euclidean norm, analytically.

## Where risk aversion (P) bites

Everything above needs a curvature floor on the valuation actually used by agents. CVaR preserves a sample-wise curvature floor (CVaR is monotone, translation equivariant and convex, so pointwise α-strong convexity of the loss passes to the CVaR). It does not preserve curvature that holds only in mean, which is exactly what Q Remark 1 allows. Example on \(x\in[0,M)\): \(\psi(x;\xi)=-\xi x^2-(1-\xi)Mx\), \(\xi\sim\mathrm{Bernoulli}(1/2)\). Then \(\mathbb E\psi=-x^2/2-Mx/2\) is 1-strongly concave, but the loss \(-\psi\) has worst half equal to \(Mx\), so \(-\mathrm{CVaR}_{1/2}[-\psi] = -Mx\): curvature 0. With curvature 0:
- Q P1(i) with P2(iii) is infeasible: \(\begin{pmatrix}0 & -\theta\\ -\theta & a\end{pmatrix}\succeq0\) forces \(\theta=0\), against \(\theta^n\in\mathbb R^K_+\).
- The W-monotonicity above fails (Schur condition), and on span(1) the block is exactly skew (bilinear saddle).
- The admissible Krasnoselskij step collapses: largest τ with spectral radius < 1 at μ = 1 (check2.out), N = 50, α = 1: 1.96, 0.59, 0.20, 0.058, 0.019 for h = 1, 0.3, 0.1, 0.03, 0.01; for N = 3 no τ works once h ≤ 0.1.

In Q's own EV application the random terms enter linearly and the quadratic preference is deterministic, so CVaR-averse users keep curvature \(\alpha_n\): the benign case.
