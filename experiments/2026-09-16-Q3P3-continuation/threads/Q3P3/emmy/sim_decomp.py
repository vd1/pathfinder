#!/usr/bin/env python3
"""Efficiency-loss decomposition in Q's CDA: omission vs commission.

loss = MAXS - realized = omission + commission, exactly, where
  omission   = sum over intramarginal traders who did not trade of |value - p*|
  commission = sum over extramarginal traders who did trade of |value - p*|
Omission is the market analogue of a missed finding (recall loss in P);
commission is the analogue of an unsupported agreement (precision loss in P).
Adds an 'acceptor' policy: take any individually rational standing quote on
the opposite side (the terminal action is the default, as AGREE is for P's
naive critic); otherwise open with rent r0 or improve by $0.01.
"""
import json, math, random, statistics, sys
sys.path.insert(0, "emmy")
from sim_cda import B_VALS, S_COSTS, PSTAR, MAXS, zi_c, creeper, run_round


def acceptor(side, val, idx, book, rng, p):
    if side == "B":
        if book.ask is not None and book.ask <= val:
            return book.ask
    elif book.bid is not None and book.bid >= val:
        return book.bid
    return creeper(side, val, idx, book, rng, {"d_B": 1, "d_S": 1, "s_B": -1, "s_S": -1, "r0": p.get("r0", (25, 100))})


def decomp(r):
    traded_b = [x[1] for x in r]
    traded_s = [x[2] for x in r]
    om = sum(v - PSTAR for v in B_VALS if v > PSTAR and v not in traded_b) + \
         sum(PSTAR - c for c in S_COSTS if c < PSTAR and c not in traded_s)
    cm = sum(PSTAR - v for v in traded_b if v < PSTAR) + sum(c - PSTAR for c in traded_s if c > PSTAR)
    real = sum(x[1] - x[2] for x in r)
    assert abs((MAXS - real) - (om + cm)) < 1e-9, (MAXS, real, om, cm)
    return om / MAXS, cm / MAXS


def run(name, pol, p, T=300, runs=400, seed=7):
    rng = random.Random(seed)
    rounds = [run_round(pol, p, rng, T, "persist") for _ in range(runs * 5)]
    d = [decomp(r) for r in rounds]
    prices = [x[0] for r in rounds for x in r]
    out = {"name": name, "T": T,
           "trades": round(statistics.mean(len(r) for r in rounds), 2),
           "eff": round(1 - statistics.mean(a + b for a, b in d), 3),
           "omission": round(statistics.mean(a for a, _ in d), 3),
           "commission": round(statistics.mean(b for _, b in d), 3),
           "alpha": round(statistics.mean(100 * math.sqrt(statistics.mean((x[0] - PSTAR) ** 2 for x in r)) / PSTAR for r in rounds if r), 1),
           "price_sd_across_trades": round(statistics.pstdev(prices) / 100, 3)}
    print(json.dumps(out))
    return out


if __name__ == "__main__":
    res = [run("ZI-C", zi_c, {}),
           run("creeper d=1 s=0", creeper, {"d_B": 1, "d_S": 1, "s_B": 0, "s_S": 0}),
           run("creeper d=1 s=0", creeper, {"d_B": 1, "d_S": 1, "s_B": 0, "s_S": 0}, T=3000),
           run("acceptor r0=25-100", acceptor, {"r0": (25, 100)}),
           run("acceptor r0=0-25", acceptor, {"r0": (0, 25)}),
           run("acceptor r0=50-150", acceptor, {"r0": (50, 150)})]
    json.dump(res, open("emmy/sim_decomp.json", "w"), indent=1)
