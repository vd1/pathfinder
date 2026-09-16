# ada notes on Q (LMI mechanism) and P (ex-ante NCI dispatch)

Scripts: `ada/check_q.py` (run with `uv run --with numpy --with scipy python ada/check_q.py`).
Outputs: `ada/check_q.out` (sections 1 to 4), `ada/check_fix.out` (section 5).

## 1. Pseudo-gradient of eq40

With \(U_n=V_n-t_n\), \(\nabla^2V_n=-\alpha I\):

\[\partial_{x_n}U_n=\nabla V_n+\tfrac{\alpha}{N-1}p_n-\tfrac{\alpha N}{(N-1)^2}\bar p_{-n},\qquad
\partial_{p_n}U_n=-\alpha p_n+\tfrac{\alpha}{N-1}\bar p_{-n}+\tfrac{\alpha}{N-1}\Big(\sum_m x_m-c\Big).\]

Direction \(v=(0,\mathbf 1\otimes u)\): the price block has zero row sums (this is P2 (i)), so \(v^\top Jv=0\).
Direction \(w_n=\varepsilon u,\ q_n=u\): \(v^\top Jv=N\alpha\|u\|^2(\varepsilon/(N-1)-\varepsilon^2)\), positive for small \(\varepsilon\). The game is not monotone.

## 2. Payments at a symmetric-price profile

For eq40 with uniform price \(\tilde p\) and payment constant \(c'\):

\[\frac{t_n}{\alpha}=\tilde p^\top x_n\Big(\tfrac{N}{N-1}+\tfrac{1}{(N-1)^2}\Big)-\tilde p^\top X\Big(\tfrac{1}{N-1}+\tfrac{1}{(N-1)^2}\Big)+\frac{\tilde p^\top c'}{N(N-1)},\qquad X=\sum_m x_m,\]

so \(\sum_n t_n=\lambda^\top(c'-X)/(N-1)\) with \(\lambda=\alpha\tilde p\). At the NE, \(\lambda^\top(c-X)=0\) and \(t^*_n=\kappa_N\lambda^\top(x_n-c/N)\), \(\kappa_N=(N^2-N+1)/(N-1)^2\).

IR counterexample: \(N=2\), \(V_n=b_nx-\tfrac12x^2\), \(b=(10,0.1)\), \(c=1\), \(X_n=[0,2]\): \(x^o=(1,0)\), \(\lambda^o=9\), \(t_1=13.5\), \(U_1=-4\).
Non-uniqueness: same with \(X_1=[0,1]\); every \(p\in[0.1,9]\) is an NE.

## 3. Repaired payment

General symmetric structure under P2 and P3: \(t^*_n=\kappa\lambda^{o\top}(x^o_n-c/N)\) with \(\kappa=1+N\theta/((N-1)\zeta)\).
The own term contributes \(1+\theta/\zeta\); budget balance P3 (i) forces \(B^m_{nn}=-\theta/(N-1)\) for \(m\neq n\), which adds \(\theta/((N-1)\zeta)\) once \(\lambda^\top X=\lambda^\top c\) is used.

IR on every instance: \(V_n(x^o_n)\ge\lambda^{o\top}x^o_n\) (concavity, \(0\in X_n\)), so \(U_n\ge(1-\kappa)\lambda^{o\top}x^o_n+\kappa\lambda^{o\top}c/N\ge0\) when \(\kappa\le N/(N-1)\), using \(\lambda^{o\top}x^o_n\le\lambda^{o\top}c\). Equivalently \(\theta\le\zeta/N\).

With \(\theta=\alpha/N\), \(\zeta=\alpha\) the payment in ledger entry by ada (repair) satisfies P2, P3, P4, gives \(\kappa=N/(N-1)\), own-Hessian Schur complement \(\preceq-\alpha(1-1/N^2)\), and \(J+J^\top\preceq0\) numerically (N = 2, 3, 5). Random check: 40 instances, IR holds in all; eq40 fails IR in 13.

## 4. Forecast capacity

Game with \(\hat c\), settlement with \(c\): physical violation \(\hat c-c\) on binding resources; imbalance \(\hat\lambda^\top(c-\hat c)/(N-1)\); zero in expectation under auto-calibration \(E[c\mid\hat c]=\hat c\), positive for \(\hat c=c+e\).

## 5. Open

- Uniqueness under degenerate multipliers (continuum of NE prices) is not repaired by the new payment.
- Whether Assumption 5 (non-expansive proximal best response) holds for the repaired, merely monotone game; a monotone-VI algorithm with proximal regularisation would be the safer route.
- P: no quantitative ex-post vs ex-ante emission comparison exists, so the latency claim cannot be tested from the text.

## 5. Q capacity as a carbon budget: which P output a Q layer needs (ada, call 2)

Assumptions: one marginal source of intensity \(e_g\) (feeder head), lossless, no line limits, renewable output \(R_t\) not curtailed in the range considered, fixed load \(\ell^{fix}_t\). Then physical emissions are \(E_t=e_g(\sum_n x_{n,t}+\ell^{fix}_t-R_t)\).

A carbon cap \(E_t\le E^{cap}_t\) is exactly Q's coupling constraint \(\sum_n x_n\le c\) with
\[ c_t = R_t-\ell^{fix}_t+E^{cap}_t/e_g . \]
So the capacity a Q-type layer consumes is built from the renewable forecast (P Tier 1) and the fixed-load forecast, plus the marginal intensity \(e_g\); the average nodal intensity (P Tier 2) does not enter. NCI is not a sufficient statistic for \(e_g\): a bus fed half by a zero-carbon unit at its limit and half by a marginal unit of 1.6 has NCI 0.8 and LME 1.6; two units of 0.8 give NCI 0.8 and LME 0.8.

Carbon conservation (emmy C1) in this setting: charge every load its marginal rate and return the renewable rent \(e_gR\) with weights fixed ex ante, \(\kappa_n=e_g(x_n-w_nR)\), \(\kappa^{fix}=e_g(\ell^{fix}-w_{fix}R)\), \(\sum_n w_n+w_{fix}=1\). Then \(\sum_n\kappa_n+\kappa^{fix}=E\) (C1) and each GDL faces \(e_g\) on its own load (C2). Emmy toy (\(e_g=0.8\), \(R=1.5\), \(\ell^{fix}=2\), GDL 0.5, \(w_{GDL}=0\)): GDL 0.4, fixed 0.4, \(E=0.8\), unchanged by the no-curtailment move (C3). An earlier draft wrote \(\kappa_n=e_g(x_n-(R-\ell^{fix})/N)\) plus \(e_g\ell^{fix}\) on fixed loads, which counts \(e_g\ell^{fix}\) twice. This has the form of the repaired Q NE payment \(t^*_n=\kappa\lambda^\top(x_n-c/N)\) with \(\kappa=1\); Q's structure with \(\kappa=N/(N-1)\) (the IR boundary of section 3) charges more than the conserving amount. Beyond this single-marginal-source case (curtailment kinks, several marginal units, line limits) \(e_g\) becomes a bus- and regime-dependent LME and the constraint becomes \(\sum_n G_n x_n\le c\); not worked out.
