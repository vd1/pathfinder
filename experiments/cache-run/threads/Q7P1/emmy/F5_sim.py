"""emmy F5 numerics (verifier #18): plain projected pseudo-gradient play on game (40), K=1,
with P's one-point CVaR estimator (fixed batch s), perturbed points kept inside the box:
quantities are projected onto the shrunk box [delta, xmax-delta], so y = x + delta*u stays in [0, xmax].
Loss of agent n: l_n(y, xi) = (h_n/2)(y - xt_n)^2 + xi*y - kappa_n, xi ~ U(-b, b), CVaR at upper-tail level 1/2.
kappa_n is a deterministic constant (variance only; surrogate and true objectives unchanged up to constants).
Closed forms for y >= 0:
  true CVaR:      C_n(y)  = (h/2)(y-xt)^2 + m y - kappa,  m = b/2
  empirical CVaR: (h/2)(y-xt)^2 + y * mean(top s/2 of xi) - kappa
  surrogate:      grad C~_n(y) = h(y - xt) + m_s,  m_s = E mean(top s/2 of s U(-b,b)) = b (s/2)/(s+1)
So the surrogate NE solves max sum -(h/2)(x-xt)^2 - m_s x on [delta, xmax-delta]^N, sum x <= c, price = lambda/alpha.
Reported: over tail windows [H/2, H), distance of the tail-mean iterate to the surrogate NE and to the true NE,
separately for quantities ||x||_2, common price level |v| (v = mean of prices) and price disagreement ||Pi p||_2.
"""
import sys
import numpy as np

N, al, b, c, xmax = 5, 0.8, 2.0, 9.0, 5.0
rng0 = np.random.default_rng(7)
h = rng0.uniform(al, 3 * al, N)
xt = np.array([3.0, 2.0, 2.5, -0.5, 7.5])


def ne(lo, hi, m):
    def xs(lam):
        return np.clip(xt - (lam + m) / h, lo, hi)
    if xs(0.0).sum() <= c:
        lam = 0.0
    else:
        a_, b_ = 0.0, 1e4
        for _ in range(200):
            mid = (a_ + b_) / 2
            a_, b_ = (mid, b_) if xs(mid).sum() > c else (a_, mid)
        lam = (a_ + b_) / 2
    return xs(lam), lam / al


def run(s, delta, T, R, eta0=0.5, k0=100, beta=0.6, thin=10, seed=0):
    g = np.random.default_rng(seed)
    lo, hi = delta, xmax - delta
    xsur, psur = ne(lo, hi, b * (s / 2) / (s + 1))
    xtrue, ptrue = ne(0.0, xmax, b / 2)
    kappa = 0.5 * h * (xsur - xt) ** 2 + (b / 2) * xsur
    x = g.uniform(lo, hi, (R, N))
    p = g.uniform(0, 5, (R, N))
    Pmax = 50.0
    store = []
    chunk = 2000
    k = 0
    while k < T:
        m = min(chunk, T - k)
        U = g.choice(np.array([-1.0, 1.0]), size=(m, R, N))
        XI = g.uniform(-b, b, size=(m, R, N, s))
        top = np.partition(XI, s // 2, axis=-1)[..., s // 2:].mean(axis=-1)   # mean of top s/2
        for j in range(m):
            eta = eta0 / (k + k0) ** beta
            u = U[j]
            y = x + delta * u
            Chat = 0.5 * h * (y - xt) ** 2 + y * top[j] - kappa
            gV = -(1.0 / delta) * Chat * u
            pbar = p.sum(axis=1, keepdims=True) - p
            gx = gV - al * (-p / (N - 1) + N * pbar / (N - 1) ** 2)
            gp = -al * (p - pbar / (N - 1) - (x.sum(axis=1, keepdims=True) - c) / (N - 1))
            x = np.clip(x + eta * gx, lo, hi)
            p = np.clip(p + eta * gp, 0.0, Pmax)
            if k % thin == 0:
                store.append(np.concatenate([x, p], axis=1).astype(np.float32))
            k += 1
    S = np.array(store)  # (T/thin, R, 2N)
    out = []
    for H in [10**4, 3 * 10**4, 10**5, 3 * 10**5, 10**6]:
        if H > T:
            break
        tail = S[(H // 2) // thin:H // thin].mean(axis=0)  # (R, 2N)
        xm, pm = tail[:, :N], tail[:, N:]
        vm = pm.mean(axis=1)
        Pi_pm = pm - vm[:, None]
        row = dict(H=H,
                   dx_sur=np.linalg.norm(xm - xsur, axis=1).mean(),
                   dv_sur=np.abs(vm - psur).mean(),
                   dPip=np.linalg.norm(Pi_pm, axis=1).mean(),
                   dx_true=np.linalg.norm(xm - xtrue, axis=1).mean(),
                   dv_true=np.abs(vm - ptrue).mean(),
                   rms_x_last=np.linalg.norm(S[H // thin - 1, :, :N] - xsur, axis=1).mean(),
                   rms_v_last=np.abs(S[H // thin - 1, :, N:].mean(axis=1) - psur).mean())
        out.append(row)
    return xsur, psur, xtrue, ptrue, out


if __name__ == "__main__":
    T = int(sys.argv[1]) if len(sys.argv) > 1 else 300000
    R = 4
    print(f"N={N}, alpha={al}, h={np.round(h,3)}, xt={xt}, c={c}, box [0,{xmax}], b={b}, CVaR level 1/2")
    print(f"A1 threshold c_N^2/(4 alpha) = {(al*(2*N-1)/(N-1)**2)**2/(4*al):.4f}  < min h = {h.min():.3f}")
    for s, delta in [(4, 0.2), (64, 0.2)]:
        xsur, psur, xtrue, ptrue, out = run(s, delta, T, R, seed=s)
        print(f"\ns={s}, delta={delta}: m_s={b*(s/2)/(s+1):.4f} vs m={b/2}")
        print(f"  surrogate NE x={np.round(xsur,4)} p={psur:.4f}   true-CVaR NE x={np.round(xtrue,4)} p={ptrue:.4f}")
        print(f"  ||x_sur-x_true||={np.linalg.norm(xsur-xtrue):.4f}, |p_sur-p_true|={abs(psur-ptrue):.4f}")
        print("  H        |xbar-x_sur|  |vbar-p_sur|  |Pi pbar|   |xbar-x_true|  |vbar-p_true|  last: |x-x_sur| |v-p_sur|   (tail [H/2,H), mean over 4 seeds)")
        for r in out:
            print(f"  {r['H']:>8d}  {r['dx_sur']:.4f}       {r['dv_sur']:.4f}       {r['dPip']:.4f}     {r['dx_true']:.4f}         {r['dv_true']:.4f}          {r['rms_x_last']:.4f}   {r['rms_v_last']:.4f}")
        sys.stdout.flush()
