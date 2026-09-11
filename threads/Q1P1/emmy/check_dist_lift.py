"""Distributed check of the lifted method (emmy F6) on a heterogeneous version of the F1 atomic instance, d = 1.

m = 4 agents on a ring, Metropolis weights 1/3. Agent i has
    J^i(q, A) = (1 - q)/2 * A + (1 + q)/2 * b + kappa_i * q,  A ~ Bernoulli(alpha),  kappa = (+0.3, -0.3, +0.1, -0.1).
CVaR_alpha[J^i](q) = C_base(q) + kappa_i q, so the network objective (1/m) sum_i C^i equals C_base, with argmin at the right
end, while the agents' own minimizers sit at opposite ends (consensus matters). The plug-in surrogate with s = 16 has slope
c/4 + kappa_i, so its network argmin is the LEFT end of X_delta (the F1 floor). All variants use the residual baseline;
only x is mixed, tau_i stays local.
  plugin : P algorithm (sphere query, empirical CVaR from s = 16 fresh samples),
  ball2  : lifted, x-part from a sphere query with one sample, tau-part from a second query at a uniform ball point,
  kernel : lifted, one query at y + delta v, v ~ (1 - v^2)^3, one sample.
"""
import numpy as np
from scipy.stats import binom

alpha, s, m = 0.1, 16, 4
n = np.arange(s + 1)
c = float(np.sum(binom.pmf(n, s, alpha) * np.maximum(0.0, 1 - n / (alpha * s))))
b = 1 - c / 2
kappa = np.array([0.3, -0.3, 0.1, -0.1])
Cb = lambda x: (1 - x) / 2 + (1 + x) / 2 * b
Cstar = Cb(1.0)
J = lambda q, A: (1 - q) / 2 * A + (1 + q) / 2 * b + kappa * q
W = np.array([[1, 1, 0, 1], [1, 1, 1, 0], [0, 1, 1, 1], [1, 0, 1, 1]]) / 3.0
kpow = 3
rng = np.random.default_rng(11)
R, K = 100, 200_000

for kind in ("plugin", "ball2", "kernel"):
    for delta in (0.3, 0.1):
        lo, hi = -(1 - delta), 1 - delta
        x = np.zeros((R, m)); tau = np.full((R, m), 0.5); base = np.zeros((R, m))
        acc = np.zeros(R); wsum = 0.0
        for k in range(K):
            eta = 0.3 / (k + 1) ** 0.6
            y = x @ W.T
            if kind == "plugin":
                u = 2.0 * rng.integers(0, 2, size=(R, m)) - 1.0
                q = y + delta * u
                nA = rng.binomial(s, alpha, size=(R, m))
                val = J(q, 0.0) + (1 - q) / 2 * np.minimum(1.0, nA / (alpha * s))
                gx = (val - base) / delta * u
            elif kind == "ball2":
                u = 2.0 * rng.integers(0, 2, size=(R, m)) - 1.0
                A1 = (rng.random((R, m)) < alpha).astype(float)
                val = tau + np.maximum(J(y + delta * u, A1) - tau, 0.0) / alpha
                gx = (val - base) / delta * u
                nu = rng.uniform(-1.0, 1.0, size=(R, m))
                A2 = (rng.random((R, m)) < alpha).astype(float)
                gt = 1.0 - (J(y + delta * nu, A2) > tau) / alpha
            else:
                v = 2.0 * rng.beta(kpow + 1, kpow + 1, size=(R, m)) - 1.0
                A1 = (rng.random((R, m)) < alpha).astype(float)
                Jq = J(y + delta * v, A1)
                val = tau + np.maximum(Jq - tau, 0.0) / alpha
                gx = -(val - base) / delta * (-2.0 * kpow * v / (1.0 - v * v))
                gt = 1.0 - (Jq > tau) / alpha
            base = val
            x = np.clip(y - eta * gx, lo, hi)
            if kind != "plugin":
                tau = np.clip(tau - eta * gt, -2.0, 2.0)
            if k >= K // 2:
                acc += eta * x.mean(axis=1); wsum += eta
        xh = acc / wsum
        dis = np.abs(x - x.mean(axis=1, keepdims=True)).max(axis=1).mean()
        print(f"{kind:6s} delta={delta}: ergodic xbar={xh.mean():+.3f} (sd {xh.std():.3f}), "
              f"true gap={np.mean(Cb(xh) - Cstar):.4f}, frac xbar>0={np.mean(xh > 0):.2f}, "
              f"edge gap={Cb(hi) - Cstar:.4f}, final max disagreement={dis:.3f}", flush=True)
