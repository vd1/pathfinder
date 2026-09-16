"""emmy F6 numerics: heterogeneous CVaR batch bias (open item 4 of #22) and the payment family of ada A6.
Same model as F5_sim.py (K=1, N=5, loss l_n(y,xi) = (h_n/2)(y-xt_n)^2 + xi*y - kappa_n, xi ~ U(-b_n,b_n),
upper-tail CVaR at level 1/2, P one-point estimator with fixed batch s_n, queried points inside the box),
but b_n and s_n differ across agents, so the batch bias m_{s_n,n} - m_n = -b_n/(2(s_n+1)) differs and moves
interior quantities, not only the price level.
Payments: the symmetric Q family (a, theta, zeta) of ada A6:
  d t_n / d x_n = -theta p_n + (zeta+theta)/(N-1) sum_{m!=n} p_m
  d t_n / d p_n = a (p_n - sum_{m!=n} p_m/(N-1)) - theta (sum x - c)
(40) is (alpha, alpha/(N-1), alpha); corrected design is theta = zeta/N with a >= zeta^2/(N(N-1)h_min).
Reported per payment and curvature regime: tail-mean distance to the surrogate NE (quantities, price level),
the true-welfare loss of the surrogate NE against the value-route bound 2 sum_n eps_n with
eps_n = sup_box |C~_n - C_n|, the equilibrium utilities under the true CVaR valuations and the budget.
"""
import sys
import numpy as np

N, al, c, xmax = 5, 0.8, 9.0, 5.0
xt = np.array([3.0, 2.0, 2.5, -0.5, 7.5])
bvec = np.array([2.0, 4.0, 1.0, 3.0, 2.0])
svec = np.array([4, 64, 4, 16, 8])
delta = 0.2


XT0 = xt.copy()


def ne(h, lo, hi, m):
    def xs(lam):
        return np.clip(xt - (lam + m) / h, lo, hi)
    if xs(0.0).sum() <= c:
        return xs(0.0), 0.0
    a_, b_ = 0.0, 1e5
    for _ in range(300):
        mid = (a_ + b_) / 2
        a_, b_ = (mid, b_) if xs(mid).sum() > c else (a_, mid)
    lam = (a_ + b_) / 2
    return xs(lam), lam


def welfare_true(h, x):  # sum of true risk-adjusted valuations -C_n (kappa dropped)
    return float(np.sum(-(0.5 * h * (x - xt) ** 2 + (bvec / 2) * x)))


def run(h, pay, T, R=4, eta0=0.5, k0=100, beta=0.6, thin=10, seed=0):
    a, th, ze = pay
    g = np.random.default_rng(seed)
    lo, hi = delta, xmax - delta
    ms = bvec * (svec / 2) / (svec + 1)
    xsur, lsur = ne(h, lo, hi, ms)
    psur = lsur / ze
    kappa = 0.5 * h * (xsur - xt) ** 2 + (bvec / 2) * xsur
    x = g.uniform(lo, hi, (R, N))
    p = g.uniform(0, 5, (R, N))
    Pmax = 200.0
    store = []
    chunk = 2000
    k = 0
    while k < T:
        m = min(chunk, T - k)
        U = g.choice(np.array([-1.0, 1.0]), size=(m, R, N))
        top = np.empty((m, R, N))
        for n in range(N):
            s = svec[n]
            XI = g.uniform(-bvec[n], bvec[n], size=(m, R, s))
            top[:, :, n] = np.partition(XI, s // 2, axis=-1)[..., s // 2:].mean(axis=-1)
        for j in range(m):
            eta = eta0 / (k + k0) ** beta
            u = U[j]
            y = x + delta * u
            Chat = 0.5 * h * (y - xt) ** 2 + y * top[j] - kappa
            gV = -(1.0 / delta) * Chat * u
            pbar = p.sum(axis=1, keepdims=True) - p
            gx = gV - (-th * p + (ze + th) / (N - 1) * pbar)
            gp = -(a * (p - pbar / (N - 1)) - th * (x.sum(axis=1, keepdims=True) - c))
            x = np.clip(x + eta * gx, lo, hi)
            p = np.clip(p + eta * gp, 0.0, Pmax)
            if k % thin == 0:
                store.append(np.concatenate([x, p], axis=1).astype(np.float32))
            k += 1
    S = np.array(store)
    rows = []
    for H in [10**4, 3 * 10**4, 10**5, 3 * 10**5, 10**6]:
        if H > T:
            break
        tail = S[(H // 2) // thin:H // thin].mean(axis=0)
        xm, pm = tail[:, :N], tail[:, N:]
        rows.append((H, np.linalg.norm(xm - xsur, axis=1).mean(), np.abs(pm.mean(axis=1) - psur).mean(),
                     np.linalg.norm(pm - pm.mean(axis=1, keepdims=True), axis=1).mean()))
    return xsur, psur, rows


if __name__ == "__main__":
    T = int(sys.argv[1]) if len(sys.argv) > 1 else 300000
    print(f"N={N}, alpha={al}, xt=XT0+(1.2+b/2)/h, c={c}, box [0,{xmax}], b={bvec}, s={svec}, delta={delta}")
    for label, h, eta0 in [("high curvature", np.array([1.8, 2.236, 2.041, 1.16, 1.28]), 0.5),
                           ("low curvature", np.array([0.012, 0.015, 0.010, 0.012, 0.018]), 2.0)]:
        # preferred points chosen so that the true NE has the same pattern (three interior, one at each bound)
        # in both regimes: xt = XT0 + (1.2 + b/2)/h
        xt[:] = XT0 + (1.2 + bvec / 2) / h
        hmin = h.min()
        pay40 = (al, al / (N - 1), al)
        acorr = max(al, 1.01 * al ** 2 / (N * (N - 1) * hmin))
        paycorr = (acorr, al / N, al)
        for pname, pay in [("(40)", pay40), ("theta=zeta/N", paycorr)]:
            a, th, ze = pay
            hstar = th * (N * th + ze) ** 2 / (4 * ze * a * (N - 1))
            xsur, psur, rows = run(h, pay, T, eta0=eta0)
            xtrue, ltrue = ne(h, 0.0, xmax, bvec / 2)
            lsur = psur * ze
            # value-route bound: eps_n = sup over the box of |C~_n - C_n| = h delta^2/6 + |m_s - m| xmax
            eps = h * delta ** 2 / 6 + np.abs(bvec * (svec / 2) / (svec + 1) - bvec / 2) * xmax
            wloss = welfare_true(h, xtrue) - welfare_true(h, xsur)
            kap = N * th / ((N - 1) * ze)
            t_sur = lsur * (1 + kap) * (xsur - c / N) if xsur.sum() >= c - 1e-9 else np.zeros(N)
            Vtrue = -(0.5 * h * (xsur - xt) ** 2 + (bvec / 2) * xsur) + 0.5 * h * xt ** 2  # V_n(0) = 0
            print(f"\n[{label}] payment {pname}: (a,theta,zeta)=({a:.3f},{th:.3f},{ze:.3f}), h*={hstar:.4f}, min h={hmin:.3f}"
                  f" ({'certified' if hmin > hstar else 'NOT certified'})")
            print(f"  surrogate NE x={np.round(xsur,4)} price={psur:.4f}; true NE x={np.round(xtrue,4)} price={ltrue/ze:.4f}")
            print(f"  ||x_sur-x_true||={np.linalg.norm(xsur-xtrue):.4f}; true welfare loss of x_sur={wloss:.4f} <= 2 sum eps={2*eps.sum():.4f}"
                  f"; sqrt bound 2 sqrt(sum eps/h_min)={2*np.sqrt(eps.sum()/hmin):.3f}")
            print(f"  at surrogate NE: budget sum t={t_sur.sum():.2e}, true utilities U={np.round(Vtrue - t_sur,3)}")
            print("  H        |xbar-x_sur|  |vbar-p_sur|  |Pi pbar|   (tail [H/2,H), mean over 4 seeds)")
            for H, dx, dv, dp in rows:
                print(f"  {H:>8d}  {dx:.4f}       {dv:.4f}       {dp:.4f}")
            sys.stdout.flush()
