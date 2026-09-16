"""Repair of Q's IR failure inside Q's own LMI family.

General quadratic payment t_n = 1/2 p'A^n p + p'B^n x + p'a^n (K = 1) with
  A^n_nn = alpha, A^n_nm = A^n_mn = -alpha/(N-1), A^n_mm = alpha/(N-1)  (m != n)
  B^n_nm = -theta (all m),  B^n_mn = beta (m != n),  B^n_mm = -theta/(N-1) (m != n)
  a^n_n = theta c,  a^n_m = -zeta c/(N(N-1)),  zeta = -theta + (N-1) beta.
This satisfies P2, P3, P4(i),(iii) and P1(i) if theta <= alpha; P4(ii) iff theta <= zeta/N.
eq40 is theta = alpha/(N-1), beta = alpha N/(N-1)^2 (zeta = alpha), which fails P4(ii).
Rerun the N=2 counterexample of q_ir_counterexample.py with eq40 and with a repaired choice.
"""
import numpy as np

ALPHA, C, N = 1.0, 1.0, 2
b = np.array([10.0, 1.1])


def build(theta, beta):
    zeta = -theta + (N - 1) * beta
    A, B, a = [], [], []
    for n in range(N):
        An = np.zeros((N, N)); Bn = np.zeros((N, N)); an = np.zeros(N)
        for m in range(N):
            if m == n:
                An[n, n] = ALPHA
                an[n] = theta * C
            else:
                An[n, m] = An[m, n] = -ALPHA / (N - 1)
                An[m, m] = ALPHA / (N - 1)
                Bn[m, n] = beta
                Bn[m, m] = -theta / (N - 1)
                an[m] = -zeta * C / (N * (N - 1))
            Bn[n, m] = -theta
        A.append(An); B.append(Bn); a.append(an)
    return A, B, a, zeta


def t(n, x, p, A, B, a):
    return 0.5 * p @ A[n] @ p + p @ B[n] @ x + p @ a[n]


def V(n, x):
    return b[n] * x - 0.5 * ALPHA * x ** 2


xo = np.array([1.0, 0.0]); lam = b[0] - ALPHA * xo[0]
xs = np.linspace(0, 2, 401); ps = np.linspace(0, 30, 601)
for label, theta, beta in [("eq40", ALPHA / (N - 1), ALPHA * N / (N - 1) ** 2),
                           ("repaired", 0.5, 2.0)]:
    A, B, a, zeta = build(theta, beta)
    ptil = lam / zeta
    p = np.array([ptil, ptil])
    U = [V(n, xo[n]) - t(n, xo, p, A, B, a) for n in range(N)]
    print(f"[{label}] theta={theta} beta={beta} zeta={zeta} P4(ii) sum a^n = {a[0].sum():.3f}"
          f" p~={ptil:.3f} U={np.round(U,3)} sum t={sum(t(n, xo, p, A, B, a) for n in range(N)):.2e}")
    for n in range(N):
        best, arg = -np.inf, None
        for xv in xs:
            xx = xo.copy(); xx[n] = xv
            for pv in ps:
                pp = p.copy(); pp[n] = pv
                u = V(n, xv) - t(n, xx, pp, A, B, a)
                if u > best:
                    best, arg = u, (round(xv, 3), round(pv, 3))
        print(f"   agent {n}: best reply utility {best:.4f} at {arg}; NE utility {U[n]:.4f}")
