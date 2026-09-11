"""Exact fixed point of the lifted surrogate on the check_dist_lift.py instance.

The lifted method is SGD on Phi(x, tau) = (1/m) sum_i F_i(x, tau_i), so its limit is argmin over X_delta of
(1/m) sum_i G_i(x), G_i(x) = min_tau F_i(x, tau), F_i(x, tau) = tau + (1/alpha) E_nu E_A (J^i(x + delta nu, A) - tau)_+.
With the tilts kappa_i the alpha-tail of the nu-mixture is no longer the A = 1 group near the edge (the two groups
overlap), so G_i > C^i there and the fixed point need not be the X_delta edge. This computes it by quadrature.
nu ~ uniform on [-1, 1] (ball2) or nu ~ (1 - v^2)^3 (kernel); the two surrogates differ.
"""
import numpy as np
from scipy.stats import binom, beta as betad

alpha, s, m = 0.1, 16, 4
n = np.arange(s + 1)
c = float(np.sum(binom.pmf(n, s, alpha) * np.maximum(0.0, 1 - n / (alpha * s))))
b = 1 - c / 2
kappa = np.array([0.3, -0.3, 0.1, -0.1])
Cb = lambda x: (1 - x) / 2 + (1 + x) / 2 * b
Cstar = Cb(1.0)

M = 2001
grid = np.linspace(-1, 1, M)
for name in ("ball", "kernel"):
    if name == "ball":
        w = np.ones(M)
    else:
        w = betad.pdf((grid + 1) / 2, 4, 4)
    w = w / w.sum()
    for delta in (0.3, 0.1):
        xs = np.linspace(-(1 - delta), 1 - delta, 281)
        Gbar = np.zeros_like(xs)
        for i, kap in enumerate(kappa):
            for ix, x in enumerate(xs):
                q = x + delta * grid
                vals = []
                for A, pA in ((0.0, 1 - alpha), (1.0, alpha)):
                    Jv = (1 - q) / 2 * A + (1 + q) / 2 * b + kap * q
                    vals.append((Jv, pA * w))
                Jall = np.concatenate([v[0] for v in vals]); pall = np.concatenate([v[1] for v in vals])
                o = np.argsort(-Jall); Js, ps = Jall[o], pall[o]
                cum = np.cumsum(ps); take = np.clip(alpha - (cum - ps), 0.0, ps)
                Gbar[ix] += float(Js @ take) / alpha / m  # CVaR_alpha of the mixture = min_tau F_i(x, tau)
        j = int(np.argmin(Gbar))
        print(f"{name:6s} delta={delta}: argmin of (1/m) sum G_i over X_delta = {xs[j]:+.3f}, "
              f"true gap there = {Cb(xs[j]) - Cstar:.4f}, edge gap = {Cb(1 - delta) - Cstar:.4f}, "
              f"max_x [(1/m) sum G_i - C] = {np.max(Gbar - Cb(xs)):.4f}", flush=True)
