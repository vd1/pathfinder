"""Numerical checks of Q's explicit payment (eq40) and of forecast-driven capacity.

Run: uv run --with numpy --with scipy python ada/check_q.py
"""
import numpy as np
from scipy.optimize import minimize

rng = np.random.default_rng(0)


def t_eq40(n, x, p, c, alpha):
    """Payment of agent n, eq40 of Q. x, p: arrays (N, K)."""
    N = x.shape[0]
    idx = [m for m in range(N) if m != n]
    pb = p[idx].sum(0)
    xb = x[idx].sum(0)
    sp = sum(p[m] @ p[m] for m in idx)
    spx = sum(p[m] @ x[m] for m in idx)
    return alpha * (
        0.5 * p[n] @ (p[n] - 2.0 / (N - 1) * pb)
        - 1.0 / (N - 1) * p[n] @ (x[n] + xb - c)
        + N / (N - 1) ** 2 * pb @ (x[n] - c / N)
        + 1.0 / (2 * (N - 1)) * sp
        - 1.0 / (N - 1) ** 2 * (spx - pb @ c / N)
    )


def unpack(z, N, K):
    return z[: N * K].reshape(N, K), z[N * K :].reshape(N, K)


def quad_params(n, N, K, c, alpha):
    """Recover (H, g, const) of t_n(z) = 0.5 z^T H z + g^T z + const, z = col(x, p)."""
    d = 2 * N * K
    f = lambda z: t_eq40(n, *unpack(z, N, K), c, alpha)
    f0 = f(np.zeros(d))
    E = np.eye(d)
    g = np.array([(f(E[i]) - f(-E[i])) / 2 for i in range(d)])
    H = np.zeros((d, d))
    for i in range(d):
        for j in range(d):
            H[i, j] = (f(E[i] + E[j]) - f(E[i]) - f(E[j]) + f0)
    return H, g, f0


def section1():
    print("== 1. LMI conditions for eq40, N=3, K=2, alpha=1 ==")
    N, K, alpha = 3, 2, 1.0
    c = np.array([1.0, 2.0])
    d = 2 * N * K
    # agent-ordered coordinates s_n = col(x_n, p_n)
    perm = []
    for n in range(N):
        perm += [n * K + k for k in range(K)] + [N * K + n * K + k for k in range(K)]
    J = np.zeros((d, d))
    for n in range(N):
        H, g, _ = quad_params(n, N, K, c, alpha)
        H = H[np.ix_(perm, perm)]
        row = slice(2 * K * n, 2 * K * (n + 1))
        # pseudo-gradient of U_n = V_n - t_n with Hess V_n = -alpha I
        J[row, :] = -H[row, :]
        J[2 * K * n : 2 * K * n + K, 2 * K * n : 2 * K * n + K] += -alpha * np.eye(K)
        # sum_m a^n_m (linear coefficients on p) summed over m
        gp = g[N * K :].reshape(N, K)
        print(f"  agent {n}: sum_m a^n_m = {gp.sum(0)}  (P4(ii) needs <= 0; alpha c/(N(N-1)) = {alpha*c/(N*(N-1))})")
    S = J + J.T
    ev = np.linalg.eigvalsh(S)
    print("  eigenvalues of J + J^T (Hess V = -alpha I, the Psi bound):", np.round(ev, 4))
    u = np.array([1.0, 0.5])
    v = np.concatenate([np.concatenate([np.zeros(K), u]) for _ in range(N)])
    print("  v^T (J+J^T) v for v = (0, 1 (x) u):", v @ S @ v)
    eps = 0.25
    v2 = np.concatenate([np.concatenate([eps * u, u]) for _ in range(N)])
    print(f"  v^T (J+J^T) v for w_n = {eps} u, q_n = u:", v2 @ S @ v2,
          " predicted 2 N alpha |u|^2 (-eps^2 + eps/(N-1)) =", 2 * N * alpha * (u @ u) * (-eps**2 + eps / (N - 1)))


def best_response_gap(n, x, p, c, alpha, V, gradV, box, pmax=50.0):
    N, K = x.shape

    def negU(z):
        xx, pp = x.copy(), p.copy()
        xx[n], pp[n] = z[:K], z[K:]
        return -(V[n](xx[n]) - t_eq40(n, xx, pp, c, alpha))

    z0 = np.concatenate([x[n], p[n]])
    bounds = [box[n]] * K + [(0.0, pmax)] * K
    best = np.inf
    for _ in range(8):
        start = np.array([rng.uniform(*b) for b in bounds])
        r = minimize(negU, start, bounds=bounds, method="L-BFGS-B", options={"ftol": 1e-14, "gtol": 1e-10})
        best = min(best, r.fun)
    return negU(z0) - best  # >= 0; ~0 means candidate is a best response


def section2():
    print("== 2. IR counterexample: N=2, K=1, alpha=1, c=1 ==")
    alpha, c = 1.0, np.array([1.0])
    b = [10.0, 0.1]
    V = [lambda z, bb=bb: float(-0.5 * z @ z + bb * z.sum()) for bb in b]
    # social optimum: x1 = 1, x2 = 0, lambda = 9 (x1 interior of [0,2])
    x = np.array([[1.0], [0.0]])
    lam = 9.0
    p = np.full((2, 1), lam / alpha)
    box = [(0.0, 2.0), (0.0, 2.0)]
    for n in range(2):
        gap = best_response_gap(n, x, p, c, alpha, V, None, box)
        U = V[n](x[n]) - t_eq40(n, x, p, c, alpha)
        print(f"  agent {n}: best-response gap {gap:.2e}, payment {t_eq40(n, x, p, c, alpha):.3f}, utility {U:.3f}")
    print("  kappa_2 lambda (x_n - c/N) prediction:", [3 * lam * (x[n, 0] - 0.5) for n in range(2)])
    print("  sum of payments:", sum(t_eq40(n, x, p, c, alpha) for n in range(2)))
    print("== 2b. Degenerate multiplier: same but X_1 = [0,1]; every p in [0.1, 9] is an NE ==")
    box = [(0.0, 1.0), (0.0, 2.0)]
    for pt in [0.1, 3.0, 9.0]:
        p = np.full((2, 1), pt)
        gaps = [best_response_gap(n, x, p, c, alpha, V, None, box) for n in range(2)]
        print(f"  p = {pt}: gaps {np.round(gaps, 8)}, payments {[round(t_eq40(n, x, p, c, alpha), 3) for n in range(2)]}")


def social(b, alpha, c, U):
    """max sum -alpha/2 |x_n|^2 + b_n^T x_n, 0 <= x <= U, sum_n x_n <= c; separable per resource."""
    N, K = b.shape
    x = np.zeros((N, K))
    lam = np.zeros(K)
    for k in range(K):
        f = lambda l: np.clip((b[:, k] - l) / alpha, 0, U).sum()
        if f(0.0) <= c[k]:
            lam[k] = 0.0
        else:
            lo, hi = 0.0, b[:, k].max()
            for _ in range(200):
                mid = 0.5 * (lo + hi)
                lo, hi = (mid, hi) if f(mid) > c[k] else (lo, mid)
            lam[k] = 0.5 * (lo + hi)
        x[:, k] = np.clip((b[:, k] - lam[k]) / alpha, 0, U)
    return x, lam


def section3():
    print("== 3. Forecast capacity c_hat used in the game, realised c used in settlement ==")
    N, K, alpha, U = 5, 3, 1.0, 5.0
    b = rng.uniform(1, 4, size=(N, K))
    c = np.array([3.0, 4.0, 5.0])
    chat = c * (1 + rng.normal(0, 0.1, K))
    x, lam = social(b, alpha, chat, U)
    p = np.tile(lam / alpha, (N, 1))
    V = [lambda z, bb=b[n]: float(-0.5 * alpha * z @ z + bb @ z) for n in range(N)]
    gaps = [best_response_gap(n, x, p, chat, alpha, V, None, [(0, U)] * N, pmax=20) for n in range(N)]
    print("  NE check with c_hat, max gap:", max(gaps))
    print("  sum t with c_hat:", sum(t_eq40(n, x, p, chat, alpha) for n in range(N)))
    s = sum(t_eq40(n, x, p, c, alpha) for n in range(N))
    print("  sum t settled with c:", s, " predicted lambda^T (c - c_hat)/(N-1):", lam @ (c - chat) / (N - 1))
    print("  physical violation sum x - c:", x.sum(0) - c, " c_hat - c:", chat - c, " lambda:", lam)

    print("== 3b. Expected settlement surplus: naive vs calibrated forecast (K=1) ==")
    N, K = 5, 1
    b = rng.uniform(1, 4, size=(N, K))
    m, s_c, s_e = 4.0, 0.6, 0.6
    M = 20000
    cc = m + s_c * rng.normal(size=M)
    y = cc + s_e * rng.normal(size=M)
    shrink = s_c**2 / (s_c**2 + s_e**2)
    for name, fc in [("naive c_hat = y", y), ("calibrated c_hat = E[c|y]", m + shrink * (y - m))]:
        vals = []
        for ci, fi in zip(cc[:4000], fc[:4000]):
            _, lam = social(b, 1.0, np.array([max(fi, 0.0)]), 5.0)
            vals.append(lam[0] * (ci - max(fi, 0.0)) / (N - 1))
        vals = np.array(vals)
        print(f"  {name}: mean imbalance {vals.mean():.4f} +- {vals.std()/np.sqrt(len(vals)):.4f}")


def section4():
    print("== 4. Theorem 4 sample schedule Q_i = C_b / eta^(2(i+1)), eta = 0.96 ==")
    eta = 0.96
    for i in [0, 56, 100, 200, 400]:
        print(f"  i={i}: Q_i/C_b = {eta ** (-2 * (i + 1)):.3e}; ceil(eta^(i+1)) as printed in Q = {int(np.ceil(eta ** (i + 1)))}")
    print("  cumulative samples to i=400 / C_b:", sum(eta ** (-2 * (i + 1)) for i in range(401)))


if __name__ == "__main__":
    section1()
    section2()
    section3()
    section4()


def t_fix(n, x, p, c, alpha):
    """ada's repaired payment: theta = zeta/N instead of zeta/(N-1); NE value (N/(N-1)) lambda^T (x_n - c/N)."""
    N = x.shape[0]
    idx = [m for m in range(N) if m != n]
    pb, X = p[idx].sum(0), x.sum(0)
    sp = sum(p[m] @ p[m] for m in idx)
    spx = sum(p[m] @ x[m] for m in idx)
    return alpha * (
        0.5 * p[n] @ (p[n] - 2.0 / (N - 1) * pb)
        - 1.0 / N * p[n] @ (X - c)
        + (N + 1) / (N * (N - 1)) * pb @ x[n]
        - 1.0 / (N * (N - 1)) * spx
        + 1.0 / (2 * (N - 1)) * sp
        - 1.0 / (N * (N - 1)) * pb @ c
    )


def section5():
    global t_eq40
    orig = t_eq40
    t_eq40 = t_fix  # reuse the helpers with the repaired payment
    print("== 5. Repaired payment t_fix ==")
    alpha, c = 1.0, np.array([1.0])
    x = np.array([[1.0], [0.0]])
    p = np.full((2, 1), 9.0)
    V = [lambda z, bb=bb: float(-0.5 * z @ z + bb * z.sum()) for bb in [10.0, 0.1]]
    for n in range(2):
        gap = best_response_gap(n, x, p, c, alpha, V, None, [(0.0, 2.0)] * 2)
        print(f"  counterexample agent {n}: gap {gap:.2e}, payment {t_fix(n, x, p, c, alpha):.3f}, utility {V[n](x[n]) - t_fix(n, x, p, c, alpha):.3f}")
    worst_U, worst_gap, worst_bb = np.inf, 0.0, 0.0
    for trial in range(40):
        N = int(rng.integers(2, 6)); K = int(rng.integers(1, 3)); U = 3.0
        b = rng.uniform(0, 6, size=(N, K)) * rng.uniform(0.2, 3, size=(N, 1))
        cc = rng.uniform(0.5, 3, size=K)
        xs, lam = social(b, alpha, cc, U)
        ps = np.tile(lam / alpha, (N, 1))
        Vs = [lambda z, bb=b[n]: float(-0.5 * z @ z + bb @ z) for n in range(N)]
        gaps = [best_response_gap(n, xs, ps, cc, alpha, Vs, None, [(0, U)] * N, pmax=40) for n in range(N)]
        Us = [Vs[n](xs[n]) - t_fix(n, xs, ps, cc, alpha) for n in range(N)]
        Uo = [Vs[n](xs[n]) - orig(n, xs, ps, cc, alpha) for n in range(N)]
        worst_U = min(worst_U, min(Us)); worst_gap = max(worst_gap, max(gaps))
        worst_bb = max(worst_bb, abs(sum(t_fix(n, xs, ps, cc, alpha) for n in range(N))))
        if min(Uo) < 0:
            print(f"  trial {trial} (N={N}): eq40 min utility {min(Uo):.3f}, t_fix min utility {min(Us):.3f}")
    print(f"  40 random instances: max NE gap {worst_gap:.2e}, max |sum t| {worst_bb:.2e}, min utility {worst_U:.4f}")
    for N in [2, 3, 5]:
        K = 1; d = 2 * N * K
        J = np.zeros((d, d))
        for n in range(N):
            H, _, _ = quad_params(n, N, K, np.array([1.0]), alpha)
            perm = []
            for m in range(N):
                perm += [m * K + k for k in range(K)] + [N * K + m * K + k for k in range(K)]
            H = H[np.ix_(perm, perm)]
            J[2 * K * n: 2 * K * (n + 1), :] = -H[2 * K * n: 2 * K * (n + 1), :]
            J[2 * K * n, 2 * K * n] += -alpha
        print(f"  N={N}: max eigenvalue of J+J^T, t_fix: {np.linalg.eigvalsh(J + J.T).max():.4f}")
    t_eq40 = orig


section5()
