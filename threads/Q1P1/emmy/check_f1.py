"""Numerical check of F1 on P's assumptions (1-D, bounded, convex, Lipschitz loss).

Instance: X=[-1,1], r=1, J(x,xi)=((1-x)/2)*A + ((1+x)/2)*b, A~Bernoulli(alpha), b=1-c_s/2.
Empirical CVaR is positively homogeneous and translation equivariant, so
hatC(x) = ((1-x)/2)*min(1, N/(alpha s)) + ((1+x)/2)*b, N~Bin(s,alpha).
"""
import numpy as np
from scipy.stats import binom

def c_s(s, alpha):
    n = np.arange(s + 1)
    return float(np.sum(binom.pmf(n, s, alpha) * np.maximum(0.0, 1 - n / (alpha * s))))

print("bias of empirical CVaR of Bernoulli(alpha) loss (true CVaR = 1)")
for alpha in (0.5, 0.1):
    for s in (16, 64, 256, 1024, 4096):
        c = c_s(s, alpha)
        print(f"alpha={alpha:4} s={s:5d} c_s={c:.5f} c_s*sqrt(s)={c*np.sqrt(s):.4f} "
              f"DKW bound sqrt(2pi)/(alpha sqrt s)={np.sqrt(2*np.pi)/(alpha*np.sqrt(s)):.4f}")

alpha, s = 0.5, 16
c = c_s(s, alpha); b = 1 - c / 2; U, L, D, d, r = 1.0, 0.5, 2.0, 1, 1.0
C = lambda x: (1 - x) / 2 + (1 + x) / 2 * b
Cstar = C(1.0)
print(f"\ninstance alpha={alpha} s={s} c_s={c:.4f} b={b:.4f} C*={Cstar:.4f}")
# surrogate C^s is linear with slope +c/4, so argmin over X_delta = [-(1-delta), 1-delta] is -(1-delta)
rng = np.random.default_rng(0)
R, K = 400, 200_000
for delta in (0.05, 0.1, 0.2, 0.4):
    x = np.zeros(R); acc = np.zeros(R); wsum = 0.0
    lo, hi = -(1 - delta / r), (1 - delta / r)
    for k in range(K):
        eta = 0.5 / (k + 1) ** 0.6
        u = rng.choice((-1.0, 1.0), size=R)
        q = x + delta * u
        N = rng.binomial(s, alpha, size=R)
        chat = (1 - q) / 2 * np.minimum(1.0, N / (alpha * s)) + (1 + q) / 2 * b
        g = (d / delta) * chat * u
        x = np.clip(x - eta * g, lo, hi)
        if k >= K // 2:
            acc += eta * x; wsum += eta
    xhat = acc / wsum
    gap = C(xhat) - Cstar
    p_term = np.sqrt(2 * np.pi) * d * D * U / (alpha * delta) * (1 / np.sqrt(s))
    f1_term = 2 * np.sqrt(2 * np.pi) * U / alpha * (1 / np.sqrt(s))
    print(f"delta={delta:4}: mean xhat={xhat.mean():+.3f} (surrogate argmin {lo:+.3f}), "
          f"true gap={gap.mean():.4f} (theory c_s/2 - delta c_s/4 = {c/2 - delta*c/4:.4f}); "
          f"P sampling term={p_term:.3f}, F1 sampling term={f1_term:.3f}")
