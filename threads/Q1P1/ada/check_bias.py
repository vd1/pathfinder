"""Sanity check of F1 on a 1-D example (illustration, not a test of P's upper bounds).

J(x, xi) = |x - xi|, xi ~ Bernoulli(p), alpha fixed, X = [-1, 2] (contains the radius-1 ball, r = 1).
Cbar_s is computed exactly by summing over K ~ Bin(s, p); Ctilde is its uniform smoothing over [x-delta, x+delta].
We report the true gap C(argmin_{X_delta} Ctilde) - C*, sup bias b_s, the corrected bound on the
finite-sample term, and P's finite-sample term D_x d sqrt(2pi) U/(alpha delta) e_s.
"""
import numpy as np
from math import comb, sqrt, pi

p, alpha = 0.3, 0.5
lo, hi, r = -1.0, 2.0, 1.0
U, L, d, Dx = 2.0, 1.0, 1, 3.0
h = 1e-3
xs = np.arange(lo - 1.0, hi + 1.0 + h / 2, h)


def cvar_two_point(v0, q0, v1, q1, a):
    vmax = np.maximum(v0, v1)
    vmin = np.minimum(v0, v1)
    pmax = np.where(v0 >= v1, q0, q1)
    return np.where(pmax >= a, vmax, (pmax * vmax + (a - pmax) * vmin) / a)


def C(x):
    return cvar_two_point(np.abs(x), 1 - p, np.abs(x - 1), p, alpha)


def Cbar(x, s):
    tot = np.zeros_like(x)
    for k in range(s + 1):
        w = comb(s, k) * p**k * (1 - p) ** (s - k)
        tot += w * cvar_two_point(np.abs(x), (s - k) / s, np.abs(x - 1), k / s, alpha)
    return tot


def smooth(f, delta):
    n = int(round(delta / h))
    ker = np.ones(2 * n + 1) / (2 * n + 1)
    return np.convolve(f, ker, mode="same")


Cx = C(xs)
inX = (xs >= lo) & (xs <= hi)
Cstar = Cx[inX].min()
print(f"C* = {Cstar:.4f} at x = {xs[inX][Cx[inX].argmin()]:.3f}")
print(f"{'s':>4} {'delta':>6} {'gap':>9} {'b_s':>8} {'corr_bd':>8} {'P_term':>9}")
for s in (4, 16, 64):
    Cb = Cbar(xs, s)
    bs = np.max(np.abs(Cb - Cx)[inX])
    assert np.all(Cb[inX] <= Cx[inX] + 1e-12), "expected downward bias"
    es = 1 / sqrt(s)
    for delta in (0.4, 0.2, 0.1, 0.05, 0.02, 0.01):
        Ct = smooth(Cb, delta)
        Xd = (xs >= (1 - delta / r) * lo) & (xs <= (1 - delta / r) * hi)
        xt = xs[Xd][Ct[Xd].argmin()]
        gap = float(C(np.array([xt]))[0] - Cstar)
        corr = sqrt(2 * pi) * U / alpha * es
        pterm = Dx * d * sqrt(2 * pi) * U / (alpha * delta) * es
        print(f"{s:>4} {delta:>6} {gap:>9.5f} {bs:>8.4f} {corr:>8.3f} {pterm:>9.2f}")

# Bernoulli example: bias is Theta(1/sqrt(s))
print("\nBernoulli(alpha) at level alpha: 1 - E Chat_s vs sqrt((1-alpha)/(2 pi alpha s))")
for s in (16, 64, 256, 1024):
    ks = np.arange(s + 1)
    w = np.array([comb(s, int(k)) * alpha**k * (1 - alpha) ** (s - k) for k in ks])
    Ech = float(np.sum(w * np.minimum(1.0, ks / (alpha * s))))
    print(f"s={s:>5}  1-E Chat = {1 - Ech:.4f}  approx = {sqrt((1 - alpha) / (2 * pi * alpha * s)):.4f}")
