# The symmetric Q family: curvature threshold and IR (ada A6)

Numerics: `ada/family.py`, output `ada/family.out`. K = 1 throughout; for K > 1 with diagonal \(\theta,\zeta\) everything below holds per resource.

## 1. The family

Q restricts \(t_n\) by P2 (Theorem 1) and P3 (Theorem 2). Impose permutation symmetry. P3(ii) kills \(A^n_{ml},B^n_{ml}\) for \(m\neq l\), both \(\neq n\). Then:

- price quadratic: \(A^n_{nn}=a\), \(A^n_{nm}=b\), \(A^n_{mm}=e\) (\(m\neq n\)); P2(i) gives \(b=-a/(N-1)\), P3(i) gives \(e=a/(N-1)\);
- bilinear: P2(iii) gives \(B^n_{nl}=-\theta\) for all \(l\); P2(ii) gives \(B^n_{mn}=(\zeta+\theta)/(N-1)\) for \(m\neq n\); P3(i) gives \(B^n_{mm}=-\theta/(N-1)\);
- linear: P2(iv) gives \(a^n_n=\theta c\); P3(iii) gives \(a^n_m=-\zeta c/(N(N-1))\).

So the symmetric P2 and P3 family is exactly three parameters \((a,\theta,\zeta)\), with \(\theta,\zeta>0\). Payment (40) is \(a=\alpha\), \(\theta=\alpha/(N-1)\), \(\zeta=\alpha\) (checked to \(10^{-16}\) for N = 2, 3, 5, 10). The equilibrium price is \(\tilde p=\lambda^o/\zeta\).

## 2. Pseudo-gradient Jacobian

With \(\Pi=I-\mathbf 1\mathbf 1^\top/N\), \(P_1=\mathbf 1\mathbf 1^\top/N\) and valuation Hessian \(-H\):
\[
J=\begin{pmatrix}-H & \frac{N\theta+\zeta}{N-1}\Pi-\zeta P_1\\ N\theta P_1 & -\frac{aN}{N-1}\Pi\end{pmatrix}
\]
(checked against finite differences of the full payment, error below \(5\cdot10^{-6}\)).

## 3. Metric-monotonicity threshold

For a block-scalar metric \(W=\mathrm{diag}(I,wI)\) (the only metrics for which Euclidean projection on the product box is the \(W\)-projection, emmy F4(1)), the \(P_1\) part of the \(x\)-\(p\) block of \(WJ+J^\top W\) is \((wN\theta-\zeta)P_1\) against a zero \(p\)-\(p\) entry, so negative semidefiniteness forces \(w=\zeta/(N\theta)\). Then
\[
WJ+J^\top W=\begin{pmatrix}-2H & \frac{N\theta+\zeta}{N-1}\Pi\\ \frac{N\theta+\zeta}{N-1}\Pi & -\frac{2\zeta a}{\theta(N-1)}\Pi\end{pmatrix}\preceq0
\iff H\succeq h^\ast I\ \text{(exact for }H=hI\text{)},\qquad
h^\ast=\frac{\theta(N\theta+\zeta)^2}{4\zeta a(N-1)}.
\]
For (40) this is \(\alpha(2N-1)^2/(4(N-1)^4)\), my A1 value and emmy F5 (H1). Checked on 8 random \((N,a,\theta,\zeta)\): \(\lambda_{\max}\le10^{-13}\) at \(1.01h^\ast\), strictly positive at \(0.99h^\ast\).

Consequences.

1. The price weight \(a\) acts only on \(\Pi p\), so \(h^\ast\to0\) as \(a\to\infty\). Any positive curvature floor is certified by choosing \(a\ge\theta(N\theta+\zeta)^2/(4\zeta h(N-1))\). The \(\alpha/N^2\) scale in my A2(b) is an artefact of (40) tying \(a\) to the curvature bound \(\alpha\); I withdraw it as a statement about the mechanism class.
2. At \(h=0\) no choice helps: on the level direction \((u\mathbf 1,v\mathbf 1)\) the block is \(\begin{pmatrix}-h&-\zeta\\N\theta&0\end{pmatrix}\), a pure rotation at \(h=0\) (eigenvalues \(\pm i\sqrt{N\theta\zeta}\)), independent of \(a\). A strictly positive floor is necessary and any positive floor is sufficient.
3. The threshold is a common-Lyapunov (proof) threshold, not a linear instability threshold: for (40) with heterogeneous \(H\in[0.05h^\ast,h^\ast]\) (300 draws, N = 3, 10, 50) the linearisation stays Hurwitz. This matches A4 (plain play converged at every tested curvature). What fails below \(h^\ast\) is the uniform certificate over time-varying Hessians, which is what a nonlinear, sampled valuation needs.

## 4. Individual rationality for every concave valuation

At the symmetric-price NE with active coupling,
\[
t_n=\lambda^o(1+\kappa)\Big(x^o_n-\frac cN\Big),\qquad \kappa=\frac{N\theta}{(N-1)\zeta}.
\]
For (40), \(1+\kappa=k_N\) of emmy F3b and F5(b). Concavity, \(V_n(0)=0\), \(0\in\mathcal X_n\) and the KKT condition give \(V_n(x^o_n)\ge\lambda^o x^o_n+\tfrac h2(x^o_n)^2\). Hence \(U_n\ge0\) whenever \(\kappa x^o_n\le(1+\kappa)c/N\). Since \(x^o_n\le c\), this holds for every share iff \(\kappa(N-1)\le1\), that is
\[
\theta\le\zeta/N .
\]
Sharpness: for \(\theta>\zeta/N\), an agent with \(x^o_n=c\) has \(U_n\ge\lambda^oc[1-(1+\kappa)(N-1)/N]+\tfrac h2c^2\) with a negative bracket, attained by quadratic valuations, so \(U_n<0\) once \(\lambda^o\) is large relative to \(h\). The share bound \((1+\kappa)/(\kappa N)\) reduces for (40) to \((N^2-N+1)/N^2\), emmy F5(b).

Instance (N = 3, c = 1, \(V_1=10x-x^2/2\), \(V_{2,3}=0.1x-x^2/2\), boxes \([0,2]\), so \(x^o=(1,0,0)\), \(\lambda^o=9\)), NE verified by best-response optimisation (gain 0 for every agent), budget exactly 0:

| payment | \(U\) |
|---|---|
| (40), \(\alpha=1\) | \((-1,\ 5.25,\ 5.25)\) |
| \(\theta=\zeta/N\), \(a=1\) | \((0.5,\ 4.5,\ 4.5)\) |
| \(\theta=\zeta/N\), \(a=5\) | \((0.5,\ 4.5,\ 4.5)\) |

At \(\theta=\zeta/N\) the bound is tight: \(U_1=\tfrac h2c^2\).

## 5. The corrected design this gives

At \(\theta=\zeta/N\) the cancellation metric is \(w=1\) (emmy F1 found this variant Euclidean monotone), and \(h^\ast=\zeta^2/(N(N-1)a)\). So for agents whose risk-adjusted valuations keep a per-sample curvature floor \(h>0\) (preserved by CVaR, empirical CVaR, smoothing and batch means, emmy F5(0)):
\[
\theta=\zeta/N,\qquad a\ge\frac{\zeta^2}{N(N-1)h}
\]
gives a payment in Q's class that is Euclidean monotone uniformly over valuations with that floor, budget balanced, IR for every concave valuation with \(V_n(0)=0\), and implements the welfare optimum; Q P1(i) (\(ah\ge\theta^2\)) is implied. Emmy F5 carries over with \(W=I\) and \(\alpha\) replaced by \(\zeta\) in the level drift, since \(p\mapsto p+v\mathbf 1\) shifts \(F_{x_n}\) by \((\theta-(\zeta+\theta))v=-\zeta v\). This replaces Q Proposition 2, which fails on P1 (emmy F1) and on P4 (emmy F5(b)).

Cost, not quantified: a large \(a\) stiffens the price-disagreement mode (rate \(aN/(N-1)\)), which limits early step sizes; the level mode has rate about \(N\theta\zeta/h\) when \(h^2>4N\theta\zeta\), independent of \(a\).

Not done: the same analysis without symmetry (the full LMI in \((A^n,B^n,a^n)\) for fixed \(w\)), and a simulation comparing (40) with the corrected payment below the (40) threshold. Given item 3 of Section 3 I expect little visible difference in linear-quadratic instances.
