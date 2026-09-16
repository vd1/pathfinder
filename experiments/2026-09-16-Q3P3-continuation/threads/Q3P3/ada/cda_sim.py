"""Simulate the Q (Struski et al.) continuous double auction with rule-based traders.

Mechanism as stated in Q Sec 3.2: 11 buyers, 11 sellers, values/costs 0.75..3.25 step 0.25,
5 rounds, T=300 iterations per round, at each iteration one agent is drawn uniformly
from those not yet transacted this round; a crossing quote trades at the standing price,
an improving quote replaces the standing quote, anything else is rejected.
Unspecified in Q: what happens to the non-consumed side after a trade. Variant 'clear'
removes both standing quotes (Smith/Gode-Sunder convention); 'keep' keeps the other
side's standing quote if its owner is still active.
"""
import random, math, sys, statistics as st

VALS = [round(0.75 + 0.25 * k, 2) for k in range(11)]
P0, SMAX = 2.00, 7.50  # equilibrium price, max surplus (5 positive-surplus pairs + 1 zero)

def cents(x):
    return round(x * 100) / 100

def run_round(strategy, rng, T=300, book_rule="clear"):
    buyers = [("B", v) for v in VALS]
    sellers = [("S", c) for c in VALS]
    agents = buyers + sellers
    active = set(range(22))
    bid = None  # (price, agent_idx)
    ask = None
    trades = []  # (price, buyer_val, seller_cost)
    for t in range(T):
        if not active:
            break
        i = rng.choice(sorted(active))
        side, r = agents[i]
        q = strategy(side, r, bid, ask, rng, t)
        if q is None:
            continue
        q = cents(q)
        if side == "B":
            if ask is not None and q >= ask[0]:
                p, j = ask
                trades.append((p, r, agents[j][1]))
                active.discard(i); active.discard(j)
                ask = None
                if book_rule == "clear" or (bid is not None and bid[1] not in active):
                    bid = None
            elif bid is None or q > bid[0]:
                bid = (q, i)
        else:
            if bid is not None and q <= bid[0]:
                p, j = bid
                trades.append((p, agents[j][1], r))
                active.discard(i); active.discard(j)
                bid = None
                if book_rule == "clear" or (ask is not None and ask[1] not in active):
                    ask = None
            elif ask is None or q < ask[0]:
                ask = (q, i)
    return trades

def zi_c(lo=0.0, hi=4.0):
    def s(side, r, bid, ask, rng, t):
        return rng.uniform(lo, r) if side == "B" else rng.uniform(r, hi)
    return s

def zi_u(lo=0.0, hi=4.0):
    def s(side, r, bid, ask, rng, t):
        return rng.uniform(lo, hi)
    return s

def threshold(eps_b, eps_s, delta=0.01, mk=(0.25, 1.25)):
    """Improve standing quote by delta within budget; cross the opposite quote
    only if it is within budget and the spread is <= eps; open at a random markup."""
    def s(side, r, bid, ask, rng, t):
        eps = eps_b if side == "B" else eps_s
        if side == "B":
            if ask is not None and ask[0] <= r and (bid is None or ask[0] - bid[0] <= eps + 1e-9):
                return ask[0]
            if bid is None:
                q = r - rng.uniform(*mk)
                if ask is not None:
                    q = min(q, ask[0] - 0.01)
                return q if q >= 0 else None
            q = bid[0] + delta
            if q <= r and (ask is None or q < ask[0]):
                return q
            return None
        else:
            if bid is not None and bid[0] >= r and (ask is None or ask[0] - bid[0] <= eps + 1e-9):
                return bid[0]
            if ask is None:
                q = r + rng.uniform(*mk)
                if bid is not None:
                    q = max(q, bid[0] + 0.01)
                return q
            q = ask[0] - delta
            if q >= r and (bid is None or q > bid[0]):
                return q
            return None
    return s

def metrics(trades):
    n = len(trades)
    eff = sum(bv - sc for _, bv, sc in trades) / SMAX
    if n:
        mp = sum(p for p, _, _ in trades) / n
        alpha = 100 * math.sqrt(sum((p - P0) ** 2 for p, _, _ in trades) / n) / P0
    else:
        mp, alpha = float("nan"), float("nan")
    return n, mp, alpha, eff

def session(strategy, rng, T, book_rule, rounds=5):
    return [metrics(run_round(strategy, rng, T, book_rule)) for _ in range(rounds)]

def summarize(name, strategy, n_sess=400, T=300, book_rule="clear", seed=1):
    rng = random.Random(seed)
    sess = [session(strategy, rng, T, book_rule) for _ in range(n_sess)]
    out = []
    for r in range(5):
        col = [s[r] for s in sess]
        tr = st.mean(c[0] for c in col)
        pr = st.mean(c[1] for c in col if c[0])
        al = st.mean(c[2] for c in col if c[0])
        ef = st.mean(c[3] for c in col)
        out.append((r + 1, tr, pr, al, ef))
    # per-session (10-run blocks) spread of round-mean efficiency, to compare with Q's 10 seeds
    blocks = [st.mean(s[r][3] for s in sess[k:k + 10] for r in range(5)) for k in range(0, n_sess, 10)]
    print(f"{name:34s} book={book_rule:5s} T={T}")
    for r, tr, pr, al, ef in out:
        print(f"   R{r}: trades={tr:4.2f} price={pr:4.2f} alpha={al:5.1f} eff={ef:4.2f}")
    print(f"   mean eff over rounds={st.mean(o[4] for o in out):.3f}; sd of 10-session block means={st.pstdev(blocks):.3f}")
    return out

if __name__ == "__main__":
    for br in ("clear", "keep"):
        summarize("ZI-C U[0,v] / U[c,4]", zi_c(), book_rule=br)
        summarize("ZI-U U[0,4] (no budget)", zi_u(), book_rule=br)
        summarize("threshold eps=0.01 (GPT Large-like)", threshold(0.01, 0.01), book_rule=br)
        summarize("threshold eps=0.00", threshold(0.0, 0.0), book_rule=br)
        summarize("threshold B0.25/S0.01 (GPT Small-like)", threshold(0.25, 0.01), book_rule=br)
        summarize("threshold eps=0.50 (Gemini-like)", threshold(0.50, 0.50), book_rule=br)
