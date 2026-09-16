"""Check Q's explicit payment (eq40) against Q's LMI conditions P1-P4.

Coefficients A^n, B^n, a^n are extracted from t_n numerically (t_n is a
polynomial of degree 2), independently of any hand derivation. K = 1.
"""
import itertools

import numpy as np

N, ALPHA, C = 4, 0.8, 1.0


def t(n, x, p, alpha=ALPHA, c=C, N=N):
    others = [m for m in range(N) if m != n]
    pbar = sum(p[m] for m in others)
    xbar = sum(x[m] for m in others)
    sig_p = sum(p[m] * p[m] for m in others)
    sig_px = sum(p[m] * x[m] for m in others)
    return alpha * (
        0.5 * p[n] * (p[n] - 2.0 / (N - 1) * pbar)
        - 1.0 / (N - 1) * p[n] * (x[n] + xbar - c)
        + N / (N - 1) ** 2 * pbar * (x[n] - c / N)
        + 1.0 / (2 * (N - 1)) * sig_p
        - 1.0 / (N - 1) ** 2 * (sig_px - pbar * c / N)
    )


def coeffs(n):
    """Return A (NxN), B (NxN), a (N), d (pure-x linear), Q (pure-x quad), const."""
    z = np.zeros(N)
    f0 = t(n, z, z)
    e = np.eye(N)
    a = np.array([t(n, z, e[m]) - f0 for m in range(N)])  # includes 0.5 A_mm
    A = np.zeros((N, N))
    for m, l in itertools.product(range(N), range(N)):
        if m == l:
            A[m, m] = t(n, z, 2 * e[m]) - 2 * t(n, z, e[m]) + f0
        else:
            A[m, l] = t(n, z, e[m] + e[l]) - t(n, z, e[m]) - t(n, z, e[l]) + f0
    a = a - 0.5 * np.diag(A)
    B = np.zeros((N, N))
    for m, l in itertools.product(range(N), range(N)):
        B[m, l] = t(n, e[l], e[m]) - t(n, e[l], z) - t(n, z, e[m]) + f0
    dx = np.array([t(n, e[l], z) - f0 for l in range(N)])
    return A, B, a, dx, f0


As, Bs, as_ = {}, {}, {}
for n in range(N):
    A, B, a, dx, f0 = coeffs(n)
    As[n], Bs[n], as_[n] = A, B, a
    assert np.allclose(dx, 0) and abs(f0) < 1e-12, "unexpected pure-x terms"

print("agent 0: A^0 =\n", As[0], "\nB^0 =\n", Bs[0], "\na^0 =", as_[0])

# P2
for n in range(N):
    assert np.isclose(As[n][n].sum(), 0), "P2(i)"
zeta = [Bs[n][:, n].sum() for n in range(N)]
theta = [-Bs[n][n, 0 if n else 1] for n in range(N)]
print("P2(ii) zeta^n =", zeta, " P2(iii) theta^n =", theta,
      " B^n_{nn} =", [Bs[n][n, n] for n in range(N)])
print("P2(iv) a^n_n =", [as_[n][n] for n in range(N)], " theta*c =", [th * C for th in theta])

# P3
for n in range(N):
    lhsA = sum(As[m][n, n] for m in range(N) if m != n)
    lhsB = sum(Bs[m][n, n] for m in range(N) if m != n)
    lhsa = sum(as_[m][n] for m in range(N) if m != n)
    rhsa = -1.0 / N * sum(Bs[m][n, m] for m in range(N)) * C
    print(f"P3 n={n}: sumA={lhsA:.4f} vs {As[n][n,n]:.4f}; sumB={lhsB:.4f} vs {Bs[n][n,n]:.4f};"
          f" sum a={lhsa:.4f} vs {rhsa:.4f}")

# P4
for n in range(N):
    print(f"P4 n={n}: (i) sum A = {As[n].sum():.4f} <= 0 ; (ii) sum_m a^n_m = {as_[n].sum():.4f} <= 0 ?"
          f" expected alpha c/(N(N-1)) = {ALPHA*C/(N*(N-1)):.4f}")

# P1: build Psi with (x,p) ordering per agent; Psi_nm = -d^2 t_n / ds_n ds_m (+ -alpha on x_n x_n)
Psi = np.zeros((2 * N, 2 * N))
for n in range(N):
    for m in range(N):
        blk = np.zeros((2, 2))
        blk[1, 1] = -As[n][n, m]
        blk[0, 1] = -Bs[n][m, n]  # d/dx_n d/dp_m
        blk[1, 0] = -Bs[n][n, m]  # d/dp_n d/dx_m
        if m == n:
            blk[0, 0] = -ALPHA
        Psi[2 * n:2 * n + 2, 2 * m:2 * m + 2] = blk
S = Psi + Psi.T
ev = np.linalg.eigvalsh(S)
print("P1(i) eig Psi_nn:", np.linalg.eigvalsh(Psi[:2, :2]))
print("P1(ii) eig(Psi+Psi^T):", np.round(ev, 4))
zvec = np.zeros(2 * N)
zvec[1::2] = 1.0
print("z^T (Psi+Psi^T) z for z = (x=0, p=1):", zvec @ S @ zvec)
