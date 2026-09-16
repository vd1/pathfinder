#!/usr/bin/env python3
"""Rule-based agents in the CDA of Q (Struski et al., Sec 3.1-3.2).

Stated in Q: 11 buyers / 11 sellers, values and costs 0.75..3.25 step 0.25,
p*=2.00, q*=6, 5 rounds, T=300 iterations, one agent drawn uniformly from
those not yet transacted, one unit each, crossing trades at the resting quote,
improving quotes replace the standing quote, others rejected.

Not stated in Q, so parametrised here:
  book='persist': after a trade only the consumed resting quote (and any quote
                  owned by the crossing agent) leaves the book.
  book='clear'  : both standing quotes are cleared after each trade.
All prices in integer cents.
"""
import math, random, statistics, sys, json

B_VALS = [75 + 25 * i for i in range(11)]
S_COSTS = [75 + 25 * i for i in range(11)]
PSTAR = 200
MAXS = sum(v - PSTAR for v in B_VALS if v >= PSTAR) + sum(PSTAR - c for c in S_COSTS if c <= PSTAR)  # 750
LO, HI = 0, 400


class Book:
    __slots__ = ("bid", "bid_owner", "ask", "ask_owner")

    def __init__(self):
        self.bid = self.ask = self.bid_owner = self.ask_owner = None


def draw(x, rng):
    if isinstance(x, list):
        return rng.choices([v for v, _ in x], [w for _, w in x])[0]
    return x


def zi_c(side, val, idx, book, rng, p):
    return rng.randint(LO, val) if side == "B" else rng.randint(val, HI)


def creeper(side, val, idx, book, rng, p):
    """Improve own-side quote by d; cross when the gap to the opposite quote is <= s."""
    d, s = draw(p["d_" + side], rng), p["s_" + side]
    r_lo, r_hi = p.get("r0", (25, 100))
    if side == "B":
        own, owner, other = book.bid, book.bid_owner, book.ask
        if owner == idx:
            return None
        if own is None:
            open_ = val if (other is not None and p.get("second_at_res")) else max(LO, val - rng.randint(r_lo, r_hi))
            ref = open_
        else:
            ref = own
        if other is not None and other <= val and other - ref <= s:
            return other
        if own is None:
            return open_
        new = own + d
        if other is not None and new >= other:
            return other if other <= val else None
        return new if new <= val else None
    own, owner, other = book.ask, book.ask_owner, book.bid
    if owner == idx:
        return None
    if own is None:
        open_ = val if (other is not None and p.get("second_at_res")) else min(HI, val + rng.randint(r_lo, r_hi))
        ref = open_
    else:
        ref = own
    if other is not None and other >= val and ref - other <= s:
        return other
    if own is None:
        return open_
    new = own - d
    if other is not None and new <= other:
        return other if other >= val else None
    return new if new >= val else None


def submit(side, idx, price, book, mode):
    if side == "B":
        if book.ask is not None and price >= book.ask:
            tp, cp = book.ask, book.ask_owner
            book.ask = book.ask_owner = None
            if mode == "clear" or book.bid_owner == idx:
                book.bid = book.bid_owner = None
            return tp, idx, cp
        if book.bid is None or price > book.bid:
            book.bid, book.bid_owner = price, idx
        return None
    if book.bid is not None and price <= book.bid:
        tp, cp = book.bid, book.bid_owner
        book.bid = book.bid_owner = None
        if mode == "clear" or book.ask_owner == idx:
            book.ask = book.ask_owner = None
        return tp, cp, idx
    if book.ask is None or price < book.ask:
        book.ask, book.ask_owner = price, idx
    return None


def run_round(policy, p, rng, T, mode):
    book = Book()
    active = [("B", i) for i in range(11)] + [("S", j) for j in range(11)]
    trades = []
    for t in range(T):
        if not active:
            break
        side, i = rng.choice(active)
        val = B_VALS[i] if side == "B" else S_COSTS[i]
        price = policy(side, val, i, book, rng, p)
        if price is None:
            continue
        res = submit(side, i, price, book, mode)
        if res:
            tp, b, s = res
            trades.append((tp, B_VALS[b], S_COSTS[s], t))
            active.remove(("B", b))
            active.remove(("S", s))
    return trades


def summarise(rounds):
    n = [len(r) for r in rounds]
    prices = [statistics.mean(x[0] for x in r) / 100 for r in rounds if r]
    alpha = [100 * math.sqrt(statistics.mean((x[0] - PSTAR) ** 2 for x in r)) / PSTAR for r in rounds if r]
    eff = [sum(x[1] - x[2] for x in r) / MAXS for r in rounds]
    extra = [sum(1 for x in r if x[1] < PSTAR or x[2] > PSTAR) for r in rounds]
    return {
        "trades": round(statistics.mean(n), 2),
        "price": round(statistics.mean(prices), 3) if prices else None,
        "alpha": round(statistics.mean(alpha), 1) if alpha else None,
        "eff": round(statistics.mean(eff), 3),
        "eff_sd": round(statistics.pstdev(eff), 3),
        "extramarginal_trades": round(statistics.mean(extra), 2),
        "zero_trade_rounds": round(sum(1 for k in n if k == 0) / len(n), 3),
    }


def experiment(name, policy, p, T=300, mode="persist", runs=400, seed=1):
    rng = random.Random(seed)
    rounds = [run_round(policy, p, rng, T, mode) for _ in range(runs * 5)]
    out = {"name": name, "T": T, "book": mode, **summarise(rounds)}
    print(json.dumps(out))
    return out


if __name__ == "__main__":
    res = []
    for mode in ("persist", "clear"):
        res.append(experiment("ZI-C", zi_c, {}, mode=mode))
        for s in (0, 5, 10, 25, 50, 100):
            res.append(experiment(f"creeper d=1 s={s}", creeper, {"d_B": 1, "d_S": 1, "s_B": s, "s_S": s}, mode=mode))
        res.append(experiment("GPT-Large-like d=1 s=0 second_at_res", creeper,
                              {"d_B": 1, "d_S": 1, "s_B": 0, "s_S": 0, "second_at_res": True}, mode=mode))
        res.append(experiment("Gemini-like d=1 s=50", creeper, {"d_B": 1, "d_S": 1, "s_B": 50, "s_S": 50}, mode=mode))
        res.append(experiment("GPT-Small-like B:s=25 d=1|30(.4) S:s=0 d=1", creeper,
                              {"d_B": [(1, 0.6), (30, 0.4)], "d_S": 1, "s_B": 25, "s_S": 0}, mode=mode))
        for T in (1000, 3000):
            res.append(experiment("creeper d=1 s=0", creeper, {"d_B": 1, "d_S": 1, "s_B": 0, "s_S": 0}, T=T, mode=mode))
            res.append(experiment("ZI-C", zi_c, {}, T=T, mode=mode))
    json.dump(res, open(sys.argv[1] if len(sys.argv) > 1 else "emmy/sim_results.json", "w"), indent=1)
