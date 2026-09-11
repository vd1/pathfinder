"""P's distributed sensor problem (P Sec. 6) with a baseline b subtracted in the one-point estimator.

g = (d/delta) (Chat(yhat) - b) u. Variants of b (all F_k-measurable):
  none   : b = 0 (P's algorithm)
  resid  : b = Chat from the agent's previous query (residual feedback)
  oracle : b = C^i(y) computed with a fixed 512-sample reference noise set
  noisy  : b = oracle + N(0, sigma^2)
  adv    : b = clip(10*oracle + 100, 0, U_i) (an arbitrary wrong prediction, clipped)
  ftl    : per agent, follow-the-leader over {none, resid, adv} on the cumulative realized (Chat - b)^2
Loss offset c0 is added to every loss (CVaR is translation equivariant, so the optimizer is unchanged).
Reports final ||xbar - x*||^2 and the mean realized (d/delta)^2 (Chat - b)^2 along the run.
"""
import sys
import numpy as np

m, d, alpha, lam = 16, 10, 0.5, 1e-4
box, r = 10.0, 10.0


def er_connected(rng, p=0.4):
    while True:
        a = np.triu((rng.random((m, m)) < p).astype(int), 1)
        a = a + a.T
        seen, stack = {0}, [0]
        while stack:
            i = stack.pop()
            for j in np.nonzero(a[i])[0]:
                if j not in seen:
                    seen.add(j)
                    stack.append(j)
        if len(seen) == m:
            return a


def metropolis(a):
    deg = a.sum(1)
    W = np.zeros((m, m))
    for i in range(m):
        for j in range(m):
            if i != j and a[i, j]:
                W[i, j] = 1.0 / (max(deg[i], deg[j]) + 1)
        W[i, i] = 1.0 - W[i].sum()
    return W


def emp_cvar(losses):
    s = losses.shape[-1]
    srt = -np.sort(-losses, axis=-1)
    kf = int(np.floor(alpha * s))
    fr = alpha * s - kf
    top = srt[..., :kf].sum(-1)
    if kf < s:
        top = top + fr * srt[..., kf]
    return top / (alpha * s)


def run(variant, c0, c1, K, s, delta, seed, sigma=0.0):
    rng = np.random.default_rng(seed)
    A = rng.standard_normal((m, d, d))
    xt = np.clip(rng.standard_normal(d), -box, box)
    W = metropolis(er_connected(rng))
    wref = np.clip(0.01 * np.random.default_rng(10_000 + seed).standard_normal((512, d)), -10, 10)
    sig = np.linalg.norm(A, ord=2, axis=(1, 2))
    U = 0.5 * (sig * 2 * box * np.sqrt(d) + 10 * np.sqrt(d)) ** 2 + lam / 2 * d * box**2 + abs(c0)
    shrink = 1 - delta / r
    lo, hi = -box * shrink, box * shrink
    x = np.zeros((m, d))
    prev = np.zeros(m)
    cum = np.zeros((m, 3))

    def oracle(y):
        e = np.einsum("mij,mj->mi", A, xt[None, :] - y)
        J = 0.5 * ((e[:, None, :] + wref[None]) ** 2).sum(-1) + lam / 2 * (y**2).sum(-1)[:, None] + c0
        return emp_cvar(J)

    sq = 0.0
    for k in range(K):
        y = W @ x
        u = rng.standard_normal((m, d))
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        yh = y + delta * u
        w = np.clip(0.01 * rng.standard_normal((m, s, d)), -10, 10)
        e = np.einsum("mij,mj->mi", A, xt[None, :] - yh)
        J = 0.5 * ((e[:, None, :] + w) ** 2).sum(-1) + lam / 2 * (yh**2).sum(-1)[:, None] + c0
        Ch = emp_cvar(J)
        if variant == "none":
            b = np.zeros(m)
        elif variant == "resid":
            b = prev.copy()
        else:
            orc = oracle(y)
            if variant == "oracle":
                b = orc
            elif variant == "noisy":
                b = orc + sigma * rng.standard_normal(m)
            elif variant == "adv":
                b = np.clip(10 * orc + 100, 0, U)
            elif variant == "ftl":
                cands = np.stack([np.zeros(m), prev, np.clip(10 * orc + 100, 0, U)], 1)
                b = cands[np.arange(m), cum.argmin(1)]
                cum += (Ch[:, None] - cands) ** 2
        prev = Ch
        g = (d / delta) * (Ch - b)[:, None] * u
        sq += float(np.mean((d / delta) ** 2 * (Ch - b) ** 2))
        eta = c1 / (k + 1) ** 0.55
        x = np.clip(y - eta * g, lo, hi)
    xbar = x.mean(0)
    return float(((xbar - xt) ** 2).sum()), sq / K


if __name__ == "__main__":
    K = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    trials = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    s, delta = 64, 0.4
    print(f"K={K} trials={trials} s={s} delta={delta}; x* approximated by x_true (lam=1e-4, noise sd 0.01)")
    for c0 in (0.0, 100.0):
        for c1 in (0.004, 0.02):
            print(f"\n offset c0={c0}  step c1={c1}")
            for v, sg in (("none", 0), ("resid", 0), ("oracle", 0), ("noisy", 1.0), ("noisy", 10.0), ("adv", 0), ("ftl", 0)):
                res = [run(v, c0, c1, K, s, delta, seed, sg) for seed in range(trials)]
                err = np.mean([a for a, _ in res])
                var = np.mean([b for _, b in res])
                name = v if v != "noisy" else f"noisy{sg:g}"
                print(f"  {name:>8}: final ||xbar-x*||^2 = {err:10.4f}   mean (d/delta)^2 (Chat-b)^2 = {var:12.1f}")
