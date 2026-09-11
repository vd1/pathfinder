"""Joint (d+1)-dim one-point ZO on (x, tau) for the F1 Bernoulli instance (d = 1, so a 2-D circle)."""
import numpy as np
from scipy.stats import binom

alpha, s = 0.1, 16
n = np.arange(s + 1)
c = float(np.sum(binom.pmf(n, s, alpha) * np.maximum(0.0, 1 - n / (alpha * s))))
b = 1 - c / 2
C = lambda x: (1 - x) / 2 + (1 + x) / 2 * b
Cstar = C(1.0)
rng = np.random.default_rng(2)
R, K = 200, 400_000
for delta in (0.3, 0.1):
    lo, hi = -(1 - delta), 1 - delta
    x = np.zeros(R); tau = np.full(R, 0.5); base = np.zeros(R); acc = np.zeros(R); wsum = 0.0
    for k in range(K):
        eta = 0.3 / (k + 1) ** 0.6
        th = rng.random(R) * 2 * np.pi
        wx, wt = np.cos(th), np.sin(th)
        q = x + delta * wx
        tq = tau + delta * wt
        A = (rng.random(R) < alpha).astype(float)
        J = (1 - q) / 2 * A + (1 + q) / 2 * b
        p = tq + np.maximum(J - tq, 0.0) / alpha
        coef = (2.0 / delta) * (p - base)
        base = p
        x = np.clip(x - eta * coef * wx, lo, hi)
        tau = np.clip(tau - eta * coef * wt, -1.0 + delta, 1.0 - delta)
        if k >= K // 2:
            acc += eta * x; wsum += eta
    xh = acc / wsum
    print(f"joint tau-lift delta={delta}: mean ergodic x={xh.mean():+.3f} (sd {xh.std():.3f}), "
          f"true gap={np.mean(C(xh)-Cstar):.4f}, frac x>0={np.mean(xh>0):.2f}, X_delta-edge gap={C(hi)-Cstar:.4f}")
