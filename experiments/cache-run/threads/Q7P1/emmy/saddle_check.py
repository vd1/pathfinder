"""emmy: (1) strict monotonicity of payment (40) in a per-agent cross metric P_n=[[1,e],[e,w]] (interior only);
(2) does W-preconditioned projected play (ada A1 metric) converge on the flat price level with active constraints,
    with additive noise and with P's one-point CVaR estimator (fixed batch)?  K=1."""
import numpy as np
rng = np.random.default_rng(3)

def blocks(N, h, al):
    r = N/(N-1); a1 = al*(2*N-1)/(N-1)**2
    Jc = np.array([[-h, -al], [al*r, 0.0]])        # consensus subspace
    Jd = np.array([[-h, a1], [0.0, -al*r]])        # disagreement subspace
    return Jc, Jd

print("(1) best strict modulus  min_e max_w  -lambda_max(P J + J^T P)/lambda_max(P), homogeneous h=alpha=1")
for N in [3, 10, 50, 500]:
    best = (-np.inf, None)
    for e in np.linspace(0.0, 1.0, 101):
        for w in np.linspace(0.05, 2.0, 40):
            P2 = np.array([[1, e], [e, w]])
            if np.linalg.eigvalsh(P2).min() <= 0: continue
            Jc, Jd = blocks(N, 1.0, 1.0)
            lam = max(np.linalg.eigvalsh(P2@Jc+Jc.T@P2).max(), np.linalg.eigvalsh(P2@Jd+Jd.T@P2).max())
            m = -lam/np.linalg.eigvalsh(P2).max()
            if m > best[0]: best = (m, (round(e,2), round(w,2)))
    print(f"  N={N}: modulus {best[0]:.4f} at (e,w)={best[1]};  e=0 (ada W) gives 0")

def grads(x, p, N, al, c, gx_val):
    pbar = p.sum()-p
    gx = gx_val - al*(-p/(N-1) + N*pbar/(N-1)**2)
    gp = -al*(p - pbar/(N-1) - (x.sum()-c)/(N-1))
    return gx, gp

def run(N, h, xt, xmax, c, al, iters, noise, Pmax=50.0, cvar=None, seed=0):
    g = np.random.default_rng(seed)
    x = g.uniform(0, xmax, N); p = g.uniform(0, 5, N)
    traj = []
    for k in range(iters):
        eta = 0.5/(k+10)**0.6
        if cvar is None:
            gv = -h*(x-xt) + noise*g.normal(size=N)
        else:
            delta, s, a_risk, b = cvar
            u = g.choice([-1.0, 1.0], size=N)
            y = x + delta*u
            xi = g.uniform(-b, b, size=(N, s))
            loss = 0.5*h[:, None]*(y[:, None]-xt[:, None])**2 + xi*y[:, None]
            q = np.sort(loss, axis=1)[:, ::-1]; kk = int(np.ceil(a_risk*s))
            C = q[:, :kk].mean(axis=1)                     # empirical CVaR (upper tail, s*alpha integer)
            gv = -(1.0/delta)*C*u                          # gradient estimate of the valuation -CVaR
        gx, gp = grads(x, p, N, al, c, gv)
        x = np.clip(x + eta*gx, 0, xmax)
        p = np.clip(p + eta*(N/(N-1))*gp, 0, Pmax)          # W^{-1} preconditioning
        traj.append(np.concatenate([x, p]))
    return np.array(traj)

def ne(N, h, xt, xmax, c, al, shift=0.0):
    # centralized: max sum -h/2 (x-xt)^2 - shift*x  s.t. sum x<=c, 0<=x<=xmax ; lambda by bisection
    def xs(lam): return np.clip(xt - (lam+shift)/h, 0, xmax)
    if xs(0).sum() <= c: lam = 0.0
    else:
        lo, hi = 0.0, 1e4
        for _ in range(200):
            mid = (lo+hi)/2
            lo, hi = (mid, hi) if xs(mid).sum() > c else (lo, mid)
        lam = (lo+hi)/2
    return xs(lam), lam/al

print("(2) W-preconditioned projected play, N=5, alpha=0.8, some x at bounds")
N, al = 5, 0.8
h = rng.uniform(al, 3*al, N); xt = np.array([6.0, 1.0, 4.0, -1.0, 9.0]); xmax = 5.0
for c in [6.0, 30.0]:
    xo, po = ne(N, h, xt, xmax, c, al)
    for noise in [0.0, 1.0]:
        tr = run(N, h, xt, xmax, c, al, 200000, noise)
        err = [np.linalg.norm(tr[k, :N]-xo) + np.linalg.norm(tr[k, N:]-po) for k in [999, 9999, 99999, 199999]]
        print(f"  c={c} (coupling {'active' if po>0 else 'slack'}, p*={po:.3f}) noise={noise}: ||s_k-s*|| at k=1e3,1e4,1e5,2e5:", [f"{v:.2e}" for v in err])
# CVaR bandit: loss (h/2)(x-xt)^2 + xi x, xi~U(-b,b); CVaR_a[xi x] = x*CVaR_a[xi] = x*b(1-a) for x>=0, upper tail a
a_risk, b, delta, s = 0.5, 2.0, 0.3, 64
c = 6.0
xo, po = ne(N, h, xt, xmax, c, al, shift=b*(1-a_risk))
tr = run(N, h, xt, xmax, c, al, 400000, 0.0, cvar=(delta, s, a_risk, b), seed=1)
avg = tr[-100000:].mean(axis=0)
print(f"  one-point CVaR estimator (delta={delta}, s={s}): true-CVaR NE x*={np.round(xo,3)}, p*={po:.3f}")
print(f"    last 1e5 iterates mean x={np.round(avg[:N],3)}, p={np.round(avg[N:],3)}; ||mean-s*||={np.linalg.norm(avg[:N]-xo)+np.linalg.norm(avg[N:]-po):.3f}")
print(f"    last iterate spread (std over last 1e5): x {tr[-100000:,:N].std(axis=0).max():.3f}, p {tr[-100000:,N:].std(axis=0).max():.3f}")
