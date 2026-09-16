"""Robustness of the ZI-C benchmark in Q's institution: quote ranges, pass probability,
iteration cap, time to completion, and decomposition of efficiency loss."""
import random, statistics as st
from cda_sim import VALS, SMAX, run_round, metrics

def zi_c(lo, hi, pass_p=0.0):
    def s(side, r, bid, ask, rng, t):
        if rng.random() < pass_p:
            return None
        return rng.uniform(lo, r) if side == "B" else rng.uniform(r, hi)
    return s

def run(strategy, T=300, book_rule="clear", n=2000, seed=7):
    rng = random.Random(seed)
    effs, trs, alphas = [], [], []
    for _ in range(n):
        tr = run_round(strategy, rng, T, book_rule)
        k, mp, al, ef = metrics(tr)
        effs.append(ef); trs.append(k)
        if k: alphas.append(al)
    return st.mean(trs), st.mean(alphas), st.mean(effs)

print("ZI-C sensitivity (per-round means over 2000 rounds; book=clear)")
print(f"{'lo':>4} {'hi':>5} {'pass':>5} {'T':>4} | trades alpha  eff")
for lo, hi in [(0.0, 4.0), (0.0, 3.25), (0.0, 6.0), (0.5, 3.5), (0.75, 3.25)]:
    for pass_p in (0.0, 0.5, 0.8):
        for T in (50, 100, 300):
            tr, al, ef = run(zi_c(lo, hi, pass_p), T=T)
            print(f"{lo:4.2f} {hi:5.2f} {pass_p:5.1f} {T:4d} | {tr:5.2f} {al:5.1f} {ef:5.3f}")

# decomposition for the baseline ZI-C (0,4), T=300: how is efficiency lost?
rng = random.Random(11)
intra_missed, extra_trades, n = 0, 0, 3000
last_trade_iter = []
for _ in range(n):
    tr = run_round(zi_c(0.0, 4.0), rng, 300, "clear")
    bvals = sorted(b for _, b, _ in tr); svals = sorted(s for _, _, s in tr)
    intra_b = [v for v in VALS if v > 2.0]  # 5 buyers with positive surplus at p*
    intra_missed += sum(1 for v in intra_b if v not in bvals)
    extra_trades += sum(1 for v in bvals if v < 2.0) + sum(1 for c in svals if c > 2.0)
print(f"\nZI-C(0,4) T=300: missed positive-surplus buyers per round={intra_missed/n:.2f}, "
      f"extramarginal participants per round={extra_trades/n:.2f}")

# upper bound on efficiency given k trades in Q's schedules
ub = []
for k in range(0, 12):
    b = sorted(VALS, reverse=True)[:k]; s = sorted(VALS)[:k]
    ub.append(max(0.0, sum(b) - sum(s)) / SMAX)
print("max efficiency with k trades:", {k: round(u, 3) for k, u in enumerate(ub) if k <= 6})
