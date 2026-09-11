"""Exact tau-lift variants (x-only smoothing, no tau smoothing) on the F1 Bernoulli instance, d = 1.

Tests ada #15: SGD on F(x,tau) = E_nu phi(x + delta nu, tau) has bias <= L delta (no e_s, no 1/alpha).
  ball2 : x-part from a sphere query (u = +-1), tau-part from a second query at a uniform ball point (ada #15 fix ii).
  kernel: ONE query at x + delta v, v ~ p(v) prop. to (1 - v^2)^k on [-1, 1]; x-part = -(1/delta) phi(q) * score(v),
          score = grad log p = -2k v / (1 - v^2); tau-part = d_tau phi(q) at the same point. Both are unbiased for the
          partial derivatives of the single jointly convex F_p(x,tau) = E_v phi(x + delta v, tau).
Both use the residual baseline (previous observed phi value), which is F_k-measurable and keeps them unbiased.
On X_delta the tail of the nu-mixture is exactly the A = 1 group here, so min_tau F(x,.) = C(x) and the
predicted fixed point is the X_delta edge x = 1 - delta (a favourable instance for these constructions; it is
the instance on which joint (x,tau) smoothing stalled, see check_tau_joint.out).
"""
import numpy as np
from scipy.stats import binom

alpha, s = 0.1, 16
n = np.arange(s + 1)
c = float(np.sum(binom.pmf(n, s, alpha) * np.maximum(0.0, 1 - n / (alpha * s))))
b = 1 - c / 2
C = lambda x: (1 - x) / 2 + (1 + x) / 2 * b
Cstar = C(1.0)
J = lambda q, A: (1 - q) / 2 * A + (1 + q) / 2 * b
kpow = 3
rng = np.random.default_rng(3)
R, K = 200, 300_000

for kind in ("ball2", "kernel"):
    for delta in (0.3, 0.1):
        lo, hi = -(1 - delta), 1 - delta
        x = np.zeros(R); tau = np.full(R, 0.5); base = np.zeros(R); acc = np.zeros(R); wsum = 0.0
        for k in range(K):
            eta = 0.3 / (k + 1) ** 0.6
            if kind == "ball2":
                u = rng.choice((-1.0, 1.0), size=R)
                A1 = (rng.random(R) < alpha).astype(float)
                val = tau + np.maximum(J(x + delta * u, A1) - tau, 0.0) / alpha
                gx = (val - base) / delta * u
                nu = rng.uniform(-1.0, 1.0, size=R)
                A2 = (rng.random(R) < alpha).astype(float)
                gt = 1.0 - (J(x + delta * nu, A2) > tau) / alpha
            else:
                v = 2.0 * rng.beta(kpow + 1, kpow + 1, size=R) - 1.0
                A1 = (rng.random(R) < alpha).astype(float)
                Jq = J(x + delta * v, A1)
                val = tau + np.maximum(Jq - tau, 0.0) / alpha
                score = -2.0 * kpow * v / (1.0 - v * v)
                gx = -(val - base) / delta * score
                gt = 1.0 - (Jq > tau) / alpha
            base = val
            x = np.clip(x - eta * gx, lo, hi)
            tau = np.clip(tau - eta * gt, -1.0, 1.0)
            if k >= K // 2:
                acc += eta * x; wsum += eta
        xh = acc / wsum
        print(f"{kind:6s} delta={delta}: mean ergodic x={xh.mean():+.3f} (sd {xh.std():.3f}), "
              f"true gap={np.mean(C(xh)-Cstar):.4f}, frac x>0={np.mean(xh>0):.2f}, edge gap={C(hi)-Cstar:.4f}", flush=True)
