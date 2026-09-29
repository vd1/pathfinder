# Q and P: a failed equilibrium certificate and a narrower route

## Structural obstruction in Q

Q, Proposition 1, requires \(\Psi+\Psi^\top\preceq-\upsilon I\) with \(\upsilon>0\) for its uniqueness claim.
Q, Theorem 1, condition P2(i), requires \(\sum_m A_{nm}^n=0\) for each agent \(n\). These two requirements are
incompatible.

Take any nonzero resource-price vector \(q\), and let \(v\) have zero allocation components and price
component \(q\) for every agent. By Q's definition of the blocks of \(\Psi\),

\[
v^\top\Psi v=-\sum_n q^\top\left(\sum_m A_{nm}^n\right)q=0.
\]

Consequently \(v^\top(\Psi+\Psi^\top)v=0\), whereas P1(ii) demands a value at most \(-\upsilon\lVert
v\rVert^2<0\). The contradiction holds for every \(N\geq2\) and every nonzero \(q\), independently of the
valuation functions. In particular, Q's Proposition 2 cannot provide a payment satisfying all its stated LMIs.
This does not prove that its game lacks a unique Nash equilibrium; it invalidates this sufficient-condition
route to that conclusion.

The obstruction is operationally relevant. Q's Theorem 4 uses convergence to a fixed point and then invokes
uniqueness of the Nash equilibrium. Its numerical section sets \(Q_i=\lceil\widetilde\eta^{i+1}\rceil\) with
\(\widetilde\eta\in\{0.96,0.97,0.98\}\), which is one sample at every iteration, while Theorem 4 requires
\(Q_i=\lceil C_b/\eta^{2(i+1)}\rceil\), a geometrically increasing count. The runs therefore do not test the
theorem's stated noise regime.

There is a separate mismatch between the explicit payment and the payment used by the learning algorithm.
Q, Eq. (40), contains \(+\alpha p_n^\top p_n/2\), while the Section 4 matrix \(M\) in lines 432-440
gives \(-\alpha p_n^\top p_n/2\) in \(\widehat t_n\). This difference depends on the agent's own
strategy, so it cannot be removed as an opponent-only constant. For a scalar resource, let
\(N=2\), \(x_1=x_2=0\), \(c=0\), \(p_1=1\), \(p_2=0\), and \(\alpha=1\). Equation (40) then gives
\(t_1=1/2\), while the printed reduced formula gives \(\widehat t_1=-1/2\). Therefore the stated
best-response program and Algorithm 1 do not optimize the game induced by Eq. (40). This is independent
of the LMI contradiction above.

## What P can and cannot transfer

P, Proposition 1 and Theorem 1, certify a binary wall gate by calibrating a whole-room Hausdorff error and
applying a deterministic distance margin. The analogous Q target would be a frozen finite-iteration solver
output \(s^I\) compared with a reference efficient equilibrium \(s^\dagger\). On exchangeable, labelled
calibration episodes, one could use the split-conformal order statistic of \(R_j=\lVert
s_j^I-s_j^\dagger\rVert\) to obtain a marginal radius \(r\) satisfying \(\Pr\{\lVert
s_{\mathrm{new}}^I-s_{\mathrm{new}}^\dagger\rVert\leq r\}\geq1-\beta\). The reference equilibrium and its
economic properties would need independent verification; Q's incompatible LMIs cannot supply that
verification.

If the complete payment sum \(B(s)=\sum_n t_n(s)\) is \(L_B\)-Lipschitz on a compact strategy set and
\(B(s^\dagger)=0\), the same event gives \(\lvert B(s^I)\rvert\leq L_Br\). If agent utility is
\(L_{U,n}\)-Lipschitz and \(U_n(s^\dagger)\geq0\), it gives \(U_n(s^I)\geq-L_{U,n}r\) for every agent
simultaneously. These are approximate, marginal statements. They are not exact budget balance or individual
rationality at a finite iterate. Capacity excess is likewise at most \(\sqrt N r\) per resource if the
reference allocation is feasible, though the manager can check the observed aggregate demand directly.

The approach needs exchangeable whole-game episodes, exact or defensible reference equilibria, fixed solver
and iteration index, and usable Lipschitz constants. Neither Q nor P supplies the labelled episodes. Q's
private valuations make reference utilities and some constants especially hard to validate. P itself warns
that a marginal certificate can be vacuous operationally. Here a binding capacity or zero utility margin makes
an exact affirmative certificate fragile even for a small nonzero radius.

## Assessment

The clean result is the P1-P2 incompatibility in Q, which merits a correction or a redesigned proof. P
identifies the kind of finite-sample interface guarantee one might seek after that repair, but its wall-gate
theorem does not itself establish a publishable guarantee for Q's mechanism. A joint paper would need a
corrected equilibrium argument and real labelled episodes showing that a finite-iteration radius is small
enough to make the economic bounds useful.
