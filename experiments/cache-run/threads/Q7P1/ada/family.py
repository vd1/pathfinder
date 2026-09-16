"""Symmetric Q payment family satisfying Q P2 and P3 (K=1).

t_n = a/2 [p_n^2 - 2/(N-1) p_n pbar_{-n} + sigma^p_{-n}/(N-1)]
      + p_n[-theta x_n - theta xbar_{-n}]              (B^n_{nl} = -theta, all l)
      + (zeta+theta)/(N-1) pbar_{-n} x_n               (B^n_{mn}, m != n)
      - theta/(N-1) sum_{m!=n} p_m x_m                  (B^n_{mm}, m != n)
      + theta c p_n - zeta c/(N(N-1)) pbar_{-n}         (a^n)
(40) is a=alpha, theta=alpha/(N-1), zeta=alpha.
"""
import numpy as np
from scipy.optimize import minimize

rng = np.random.default_rng(1)


def coeffs(N, a, th, ze, c):
    A = np.zeros((N, N, N)); B = np.zeros((N, N, N)); av = np.zeros((N, N))
    for n in range(N):
        for m in range(N):
            for l in range(N):
                if m == n and l == n: A[n, m, l] = a
                elif (m == n) != (l == n): A[n, m, l] = -a / (N - 1)
                elif m == l: A[n, m, l] = a / (N - 1)
                if m == n: B[n, m, l] = -th
                elif l == n: B[n, m, l] = (ze + th) / (N - 1)
                elif m == l: B[n, m, l] = -th / (N - 1)
            av[n, m] = th * c if m == n else -ze * c / (N * (N - 1))
    return A, B, av


def pay(A, B, av, x, p):
    return np.array([0.5 * p @ A[n] @ p + p @ B[n] @ x + p @ av[n] for n in range(len(x))])


def pay40(al, c, x, p):
    N = len(x); out = []
    for n in range(N):
        pb = p.sum() - p[n]; xb = x.sum() - x[n]
        sp = (p ** 2).sum() - p[n] ** 2; spx = (p * x).sum() - p[n] * x[n]
        out.append(al * (0.5 * p[n] * (p[n] - 2 / (N - 1) * pb) - p[n] * (x[n] + xb - c) / (N - 1)
                         + N / (N - 1) ** 2 * pb * (x[n] - c / N) + sp / (2 * (N - 1))
                         - (spx - pb * c / N) / (N - 1) ** 2))
    return np.array(out)


def jac(N, a, th, ze, H):
    I = np.eye(N); O = np.ones((N, N))
    Jxp = th * I - (ze + th) / (N - 1) * (O - I)
    Jpx = th * O
    Jpp = -a * I + a / (N - 1) * (O - I)
    return np.block([[-np.diag(H), Jxp], [Jpx, Jpp]])


def check_P2P3(N, A, B, av, th, ze, c):
    e = []
    for n in range(N):
        e.append(abs(A[n, n, :].sum()))                                   # P2(i)
        e.append(abs(B[n, :, n].sum() - ze))                              # P2(ii)
        e.append(abs(B[n, n, :] + th).max())                             # P2(iii)
        e.append(abs(av[n, n] - th * c))                                  # P2(iv)
        others = [m for m in range(N) if m != n]
        e.append(abs(sum(A[m, n, n] for m in others) - A[n, n, n]))      # P3(i)
        e.append(abs(sum(B[m, n, n] for m in others) - B[n, n, n]))
        for m in others:
            for l in others:
                if m != l: e.append(abs(A[n, m, l]) + abs(B[n, m, l]))    # P3(ii)
        e.append(abs(sum(av[m, n] for m in others) + sum(B[m, n, m] for m in range(N)) * c / N))  # P3(iii)
    return max(e)


print("== 1. family = (40), P2/P3 hold, Jacobian formula ==")
for N in (2, 3, 5, 10):
    al, c = 0.8, 2.0
    A, B, av = coeffs(N, al, al / (N - 1), al, c)
    x, p = rng.random(N), rng.random(N)
    d40 = abs(pay(A, B, av, x, p) - pay40(al, c, x, p)).max()
    a, th, ze = rng.uniform(0.2, 3, 3)
    A, B, av = coeffs(N, a, th, ze, c)
    H = rng.uniform(0.5, 2, N)
    # numeric pseudo-gradient Jacobian of F = (V' - dt_n/dx_n, -dt_n/dp_n), V_n = -H x^2/2
    def F(s):
        x, p = s[:N], s[N:]; g = np.zeros(2 * N); eps = 1e-6
        for n in range(N):
            ex = np.zeros(N); ex[n] = eps
            g[n] = -H[n] * x[n] - (pay(A, B, av, x + ex, p)[n] - pay(A, B, av, x - ex, p)[n]) / (2 * eps)
            g[N + n] = -(pay(A, B, av, x, p + ex)[n] - pay(A, B, av, x, p - ex)[n]) / (2 * eps)
        return g
    s0 = rng.random(2 * N); Jn = np.zeros((2 * N, 2 * N))
    for k in range(2 * N):
        e = np.zeros(2 * N); e[k] = 1e-4
        Jn[:, k] = (F(s0 + e) - F(s0 - e)) / 2e-4
    print(f"N={N}: |family-(40)|={d40:.1e}  P2P3 residual={check_P2P3(N, A, B, av, th, ze, c):.1e}"
          f"  |J_num-J_formula|={abs(Jn - jac(N, a, th, ze, H)).max():.1e}")

print("\n== 2. W-monotonicity threshold, W=diag(I, w I), w=zeta/(N theta) ==")
for _ in range(8):
    N = int(rng.choice([2, 3, 5, 10, 50])); a, th, ze = rng.uniform(0.1, 5, 3)
    w = ze / (N * th); hstar = th * (N * th + ze) ** 2 / (4 * ze * a * (N - 1))
    W = np.diag(np.r_[np.ones(N), w * np.ones(N)])
    lam = lambda h: np.linalg.eigvalsh(W @ jac(N, a, th, ze, h * np.ones(N)) + jac(N, a, th, ze, h * np.ones(N)).T @ W).max()
    # best w by scan, to confirm cancellation w is the only admissible one
    ws = np.linspace(0.01, 5, 500)
    best = min(ws, key=lambda ww: np.linalg.eigvalsh(np.diag(np.r_[np.ones(N), ww * np.ones(N)]) @ jac(N, a, th, ze, 1.2 * hstar * np.ones(N))
                                                    + jac(N, a, th, ze, 1.2 * hstar * np.ones(N)).T @ np.diag(np.r_[np.ones(N), ww * np.ones(N)])).max())
    print(f"N={N:2d} a={a:.2f} th={th:.2f} ze={ze:.2f} h*={hstar:.4g}: lmax(1.01h*)={lam(1.01 * hstar):+.1e} "
          f"lmax(0.99h*)={lam(0.99 * hstar):+.1e}  scan-best w={best:.3f} vs w={w:.3f}")

print("\n== 3. below threshold: heterogeneous H, linearisation ==")
for N in (3, 10, 50):
    al = 1.0; a, th, ze = al, al / (N - 1), al
    hstar = th * (N * th + ze) ** 2 / (4 * ze * a * (N - 1))
    worst = -np.inf
    for _ in range(300):
        H = hstar * 0.05 * rng.uniform(1, 20, N)
        worst = max(worst, np.linalg.eigvals(jac(N, a, th, ze, H)).real.max())
    print(f"(40) N={N}: h*={hstar:.3g}; H in [0.05h*,h*]: max Re eig J = {worst:+.2e}")
    # h = 0 on the level: rotation
    print(f"   level block at h=0: eig = {np.linalg.eigvals(np.array([[0, -ze], [N * th, 0]]))}")

print("\n== 4. IR of the family at the NE; counterexample for (40) ==")


def solve_NE_check(N, a, th, ze, c, Vgrad, V, xs, lam, box=2.0):
    """xs, lam: candidate optimum of welfare. Check each agent's best response and utilities."""
    A, B, av = coeffs(N, a, th, ze, c)
    pt = lam / ze; p = pt * np.ones(N); U = []; dev = []
    for n in range(N):
        def negU(z):
            x2 = xs.copy(); p2 = p.copy(); x2[n], p2[n] = z
            return -(V[n](z[0]) - pay(A, B, av, x2, p2)[n])
        best = min((minimize(negU, z0, bounds=[(0, box), (0, 50)]) for z0 in
                    ([xs[n], pt], [0.0, 0.0], [box, 10.0], [0.5, pt])), key=lambda r: r.fun)
        U.append(-negU([xs[n], pt])); dev.append(-best.fun - U[-1])
    return np.array(U), np.array(dev), pay(A, B, av, xs, p).sum()


N, c, M, eps = 3, 1.0, 10.0, 0.1
V = [lambda x: M * x - x ** 2 / 2] + [lambda x: eps * x - x ** 2 / 2] * 2
xs = np.array([1.0, 0.0, 0.0]); lam = M - 1.0     # interior x_1=1 (box [0,2]), others at 0 since eps<lam
for name, a, th, ze in (("(40) alpha=1", 1.0, 1 / (N - 1), 1.0), ("theta=zeta/N", 1.0, 1 / N, 1.0),
                        ("theta=zeta/N, a=5", 5.0, 1 / N, 1.0)):
    U, dev, tb = solve_NE_check(N, a, th, ze, c, None, V, xs, lam)
    print(f"{name}: U={np.round(U, 4)}  best-response gain={np.round(dev, 6)}  sum t={tb:.1e}")
kap = N / (N - 1) ** 2
print(f"predicted U_1 for (40): M-1/2-(M-1)(1+kappa)(1-1/N) = {M - 0.5 - (M - 1) * (1 + kap) * (1 - 1 / N):.4f}")
