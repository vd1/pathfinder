"""What P's reported LCB aggregates can identify (P Table 1; pass/105 rounded to integer %).
Exact counts consistent with the rounding, and exact two-sided McNemar p-values over every
discordance pattern compatible with the two marginal counts (the per-task pairing is unreported)."""
from math import comb

N, H = 105, 57
pct = {"ZS": 77, "SR_selfrefine": 77, "SR": 77, "TwoR": 75, "MARS": 82, "AR": 87}
hard = {"ZS": 35, "SR_selfrefine": 35, "SR": 36, "TwoR": 34, "MARS": 39, "AR": 43}


def counts(p, n):
    return [k for k in range(n + 1) if round(100 * k / n) == p]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def bounds(x, y, n):
    """x, y = pass counts of methods A, B on the same n tasks; b = A-only, c = B-only."""
    d = x - y
    ps = []
    for c in range(0, n + 1):
        b = c + d
        if b < 0 or b > n - y or c > n - x or b + c > n or b > x or c > y:
            continue
        ps.append((mcnemar(b, c), b, c))
    return min(ps), max(ps)


if __name__ == "__main__":
    k = {m: counts(p, N) for m, p in pct.items()}
    print("counts consistent with rounding:", k, "  85% ->", counts(85, N))
    kk = {m: v[0] for m, v in k.items()}
    for m in kk:
        print(f"{m:14s} all {kk[m]:3d}/105  hard {hard[m]}/57  non-hard {kk[m]-hard[m]}/48")
    for a, b in [("AR", "MARS"), ("MARS", "SR"), ("AR", "SR"), ("AR", "ZS"), ("MARS", "ZS")]:
        lo, hi = bounds(kk[a], kk[b], N)
        loh, hih = bounds(hard[a], hard[b], H)
        print(f"{a} vs {b}: all d={kk[a]-kk[b]:+d} p in [{lo[0]:.4f} (b={lo[1]},c={lo[2]}), {hi[0]:.3f} (b={hi[1]},c={hi[2]})];"
              f" hard d={hard[a]-hard[b]:+d} p in [{loh[0]:.4f}, {hih[0]:.3f}]")
