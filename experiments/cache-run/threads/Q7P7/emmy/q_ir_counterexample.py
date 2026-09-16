"""Individual rationality of Q's eq40 payment: a two-agent counterexample.

V_n(x) = b_n x - (alpha/2) x^2 (alpha-strongly concave, V_n(0) = 0), X_n = [0, 2],
one resource with capacity c. Candidate NE from Q Theorem 1: (x^o, lambda^o/alpha).
We verify it is a NE by numerically computing each agent's best response over a
fine grid of (x_n, p_n) and report utilities.
"""
import numpy as np

ALPHA, C = 1.0, 1.0
b = np.array([10.0, 1.1])
N = 2


def t(n, x, p):
    others = [m for m in range(N) if m != n]
    pbar = sum(p[m] for m in others)
    xbar = sum(x[m] for m in others)
    sig_p = sum(p[m] ** 2 for m in others)
    sig_px = sum(p[m] * x[m] for m in others)
    return ALPHA * (
        0.5 * p[n] * (p[n] - 2.0 / (N - 1) * pbar)
        - 1.0 / (N - 1) * p[n] * (x[n] + xbar - C)
        + N / (N - 1) ** 2 * pbar * (x[n] - C / N)
        + 1.0 / (2 * (N - 1)) * sig_p
        - 1.0 / (N - 1) ** 2 * (sig_px - pbar * C / N)
    )


def V(n, x):
    return b[n] * x - 0.5 * ALPHA * x ** 2


# social optimum: x1 = 1, x2 = 0, lambda = b1 - alpha*1 = 9 (check KKT for agent 2: b2 <= lambda)
xo = np.array([1.0, 0.0])
lam = b[0] - ALPHA * xo[0]
assert b[1] - ALPHA * xo[1] <= lam
ptil = lam / ALPHA
s_x, s_p = xo.copy(), np.array([ptil, ptil])
U = [V(n, s_x[n]) - t(n, s_x, s_p) for n in range(N)]
print("x^o =", xo, " lambda^o =", lam, " utilities at candidate NE:", U)
print("sum of payments:", sum(t(n, s_x, s_p) for n in range(N)))

xs = np.linspace(0, 2, 801)
ps = np.linspace(0, 30, 1201)
for n in range(N):
    best = -np.inf
    arg = None
    for xv in xs:
        xx = s_x.copy(); xx[n] = xv
        for pv in ps[::1]:
            pp = s_p.copy(); pp[n] = pv
            u = V(n, xv) - t(n, xx, pp)
            if u > best:
                best, arg = u, (xv, pv)
    print(f"agent {n}: best response utility {best:.4f} at (x,p)={arg}; NE utility {U[n]:.4f};"
          f" outside option V(0)=0")
