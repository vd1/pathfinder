# General-agent transfer audit

Q's proposed payment is Eq. (40), [Q, lines 412–422](../inputs/Q.tex).
The bars there are **sums** over the other agents. This distinction fixes
the coefficient disputed in ledger entry 28.

Let \(S=\sum_m x_m\), \(z=S-c\), and \(d_n=x_n-c/N\). At a common price
\(p_m=p\) for every agent, Q's definitions give
\[
\bar p_{-n}=(N-1)p,\qquad
\bar\sigma^p_{-n}=(N-1)p^\top p,\qquad
\bar\sigma^{px}_{-n}=p^\top(S-x_n).
\]
The first and fourth terms of Eq. (40) cancel. Its second, third, and
fifth terms, after division by \(\alpha\), are respectively
\[
-\frac{p^\top z}{N-1},\qquad
\frac{N}{N-1}p^\top d_n,\qquad
\frac{p^\top d_n-p^\top z}{(N-1)^2}.
\]
Thus the exact common-price identity, before invoking complementarity, is
\[
\frac{t_n}{\alpha}
=\left(\frac{N}{N-1}+\frac{1}{(N-1)^2}\right)p^\top d_n
-\left(\frac{1}{N-1}+\frac{1}{(N-1)^2}\right)p^\top z.
\]
At an equilibrium, Q's price best-response conditions imply \(p\ge0\),
\(z\le0\), and \(p^\top z=0\). Therefore
\[
t_n=\alpha\kappa_Np^\top d_n,\qquad
\kappa_N=\frac{N^2-N+1}{(N-1)^2}=1+\frac{N}{(N-1)^2}.
\]
The verifier's coefficient \((N+1)/(N-1)^2\) omits the factor
\(N/(N-1)\) from Q's third term. For a direct check, take
\(N=3\), \(c=3\), \(x=(2,1,0)\), \(p_m=1\), \(n=1\), and \(\alpha=1\).
The five terms of Eq. (40) are \(-1/2\), \(0\), \(3/2\), \(1/2\), and
\(1/4\). Hence \(t_1=7/4\), whereas the verifier's formula yields
\(1\). These messages have common prices and complementarity; the
calculation of Eq. (40) does not require choosing valuations.
It can also be realized at a Nash equilibrium: set every
\(\mathcal X_n=[0,2]\), and let
\(V_1(x)=3x-x^2/2\), \(V_2(x)=2x-x^2/2\), and
\(V_3(x)=x/2-x^2/2\). At \(x=(2,1,0)\), the allocation payoff
derivatives are \(0\), \(0\), and \(-1/2\), respectively; the last
is at the lower bound. All price derivatives vanish. Each payoff is
jointly concave in its allocation and price because its own Hessian
is \(\left(\begin{smallmatrix}-1&1/2\\1/2&-1\end{smallmatrix}\right)\).
These first-order conditions therefore prove a Nash equilibrium.

The proposed others-only rebate is
\[
g_n(s_{-n})=
\frac{\alpha N}{(N-1)^3}\bar p_{-n}^\top
\left(\bar x_{-n}-\frac{N-1}{N}c\right).
\]
At a common-price complementary equilibrium, its value is
\(g_n=-\alpha Np^\top d_n/(N-1)^2\), so
\(t_n+g_n=\alpha p^\top(x_n-c/N)\). In the \(N=3\) check, the rebate
is \(-3/4\), and the revised payment is \(1\).

Since \(g_n\) uses only other agents' messages, it leaves every best
response unchanged. The revised payments sum to
\(\alpha p^\top(S-c)=0\). If \(0\in\mathcal X_n\),
\(V_n(0)=0\), and equilibrium demand maximizes
\(V_n(x_n)-\alpha p^\top x_n\), then
\[
V_n(x_n)-(t_n+g_n)
=V_n(x_n)-\alpha p^\top x_n+\alpha p^\top c/N
\ge \alpha p^\top c/N\ge0,
\]
where the last inequality also uses \(c\ge0\). Thus the transfer
calculation still supports equilibrium budget balance and individual
rationality. The Q–P finite-sample welfare and regret bounds in
[Ada's pair note](../ada/pair_note.md) remain conditional on the
existence of a surrogate equilibrium and a planner multiplier. The
sampling result in [P, lines 1287–1315](../inputs/P.tex) does not prove
learning convergence for this mechanism.
