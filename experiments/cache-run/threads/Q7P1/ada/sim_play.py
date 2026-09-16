"""Stochastic projected pseudo-gradient play on game (40), K=1, quadratic valuations
V_n = -h/2 (x-xt_n)^2 + h/2 xt_n^2, boxes x in [0,5], p in [0,10].
Preconditioner W^{-1}=diag(I, N/(N-1) I) (A1) versus Euclidean. Noise: additive N(0, sigma^2) plus
bias b_k = 1/sqrt(s_k) (P-style finite-sample bias) on x-gradients."""
import numpy as np

def run(N, h, alpha, pre, iters, c1, beta, sigma, seed, fixed_bias=None):
    rng = np.random.default_rng(seed)
    xt = np.linspace(1.0, 2.0, N)
    c = 0.5 * N
    lam = h * (xt.sum() - c) / N
    xs = xt - lam / h
    ps = lam / alpha
    x = rng.uniform(0, 5, N); p = rng.uniform(0, 10, N)
    wp = N / (N - 1) if pre else 1.0
    out = []
    for k in range(iters):
        P = p.sum(); X = x.sum()
        pbar = P - p
        gx = -h * (x - xt) + alpha * p / (N - 1) - alpha * N / (N - 1) ** 2 * pbar
        gp = -alpha * (p - pbar / (N - 1) - (X - c) / (N - 1))
        bias = fixed_bias if fixed_bias is not None else 0.0
        gx = gx + sigma * rng.standard_normal(N) + bias
        gp = gp + sigma * rng.standard_normal(N)
        eta = c1 / (k + 1) ** beta
        x = np.clip(x + eta * gx, 0, 5)
        p = np.clip(p + eta * wp * gp, 0, 10)
        if k in (iters // 10, iters // 2, iters - 1):
            out.append((k + 1, np.linalg.norm(x - xs) / np.sqrt(N), abs(p.mean() - ps), p.std()))
    return out

for h in [1.0, 0.1, 0.02]:
    for pre in [True, False]:
        for beta in [0.6, 1.0]:
            res = [run(10, h, 1.0, pre, 40000, 0.5, beta, 0.3, s) for s in range(5)]
            last = np.array([[r[-1][1], r[-1][2], r[-1][3]] for r in res])
            mid = np.array([[r[1][1], r[1][2]] for r in res])
            print(f"h={h:<5} pre={pre!s:<5} beta={beta}: mid(k=20000) rms|x-x*|={mid[:,0].mean():.3g} |pbar-p*|={mid[:,1].mean():.3g}; end rms|x-x*|={last[:,0].mean():.3g} |pbar-p*|={last[:,1].mean():.3g} std(p)={last[:,2].mean():.3g}")
# deterministic, constant step: does play cycle when curvature is small?
for h in [1.0, 0.02, 0.0]:
    r = run(10, h if h > 0 else 1e-12, 1.0, True, 40000, 0.05, 0.0, 0.0, 0)
    print(f"constant step 0.05, no noise, h={h}: ", [(k, round(a, 4), round(b, 4)) for k, a, b, _ in r])
