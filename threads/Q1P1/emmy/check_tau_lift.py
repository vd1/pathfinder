"""Plug-in (P) vs tau-lifted one-point ZO on the Bernoulli instance of F1.

X=[-1,1], J(x,xi)=((1-x)/2)*A + ((1+x)/2)*b, A~Bern(alpha), b = 1 - c_s/2 (s = plug-in batch size).
True optimum x=1. Plug-in surrogate optimum x=-1 (F1 step 5a). Both estimators use the
F_k-measurable residual baseline (previous observed value), which keeps them unbiased.
tau-lift: phi(x,tau) = tau + (1/alpha)(J - tau)_+, one sample per query, one-point ZO in x,
exact stochastic subgradient in tau: 1 - (1/alpha) 1{J > tau}.
"""
import numpy as np
from scipy.stats import binom

alpha, s = 0.1, 16
n = np.arange(s + 1)
c = float(np.sum(binom.pmf(n, s, alpha) * np.maximum(0.0, 1 - n / (alpha * s))))
b = 1 - c / 2
C = lambda x: (1 - x) / 2 + (1 + x) / 2 * b
Cstar = C(1.0)
print(f"alpha={alpha} s={s} c_s={c:.4f} b={b:.4f}; true argmin x=+1, plug-in surrogate argmin x=-1")

rng = np.random.default_rng(1)
R, K, delta = 200, 300_000, 0.3
lo, hi = -(1 - delta), 1 - delta

def run(kind):
    x = np.zeros(R); tau = np.full(R, 0.5); base = np.zeros(R)
    acc = np.zeros(R); w = 0.0
    for k in range(K):
        eta = 0.3 / (k + 1) ** 0.6
        u = rng.choice((-1.0, 1.0), size=R)
        q = x + delta * u
        if kind == "plugin":
            N = rng.binomial(s, alpha, size=R)
            val = (1 - q) / 2 * np.minimum(1.0, N / (alpha * s)) + (1 + q) / 2 * b
        else:
            A = (rng.random(R) < alpha).astype(float)
            J = (1 - q) / 2 * A + (1 + q) / 2 * b
            val = tau + np.maximum(J - tau, 0.0) / alpha
            gtau = 1.0 - (J > tau) / alpha
            tau = np.clip(tau - eta * gtau, -1.0, 1.0)
        g = (val - base) / delta * u
        base = val
        x = np.clip(x - eta * g, lo, hi)
        if k >= K // 2:
            acc += eta * x; w += eta
    xh = acc / w
    return xh, C(xh) - Cstar

for kind in ("plugin", "taulift"):
    xh, gap = run(kind)
    print(f"{kind:8s}: mean ergodic x = {xh.mean():+.3f} (sd {xh.std():.3f}), "
          f"mean true gap = {gap.mean():.4f}, fraction x>0 = {(xh > 0).mean():.2f}")
print(f"F1 prediction for plug-in gap at x=-(1-delta): {C(lo)-Cstar:.4f}; tau-lift fixed point x={hi:+.2f}, gap {C(hi)-Cstar:.4f}")
