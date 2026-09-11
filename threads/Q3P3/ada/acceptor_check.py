"""Cross-check of emmy #4 'acceptor' agents in Q's mechanism: cross any individually
rational opposite quote; otherwise open with rent U[0.25,1.25] or improve own side by 1c."""
import random, statistics as st
from cda_sim import VALS, SMAX, run_round, metrics

def acceptor(side, r, bid, ask, rng, t):
    if side == "B":
        if ask is not None and ask[0] <= r:
            return ask[0]
        if bid is None:
            q = r - rng.uniform(0.25, 1.25)
            return q if q >= 0 else None
        q = bid[0] + 0.01
        return q if q <= r else None
    else:
        if bid is not None and bid[0] >= r:
            return bid[0]
        if ask is None:
            return r + rng.uniform(0.25, 1.25)
        q = ask[0] - 0.01
        return q if q >= r else None

for br in ("keep", "clear"):
    rng = random.Random(5); K, E, A, C = [], [], [], []
    for _ in range(3000):
        tr = run_round(acceptor, rng, 300, br)
        k, mp, al, ef = metrics(tr); K.append(k); E.append(ef)
        if k: A.append(al)
        # commission: surplus lost to extramarginal traders, weighted by distance from p*=2
        com = sum(max(0, 2.0 - bv) + max(0, sc - 2.0) for _, bv, sc in tr) / SMAX
        C.append(com)
    print(f"acceptor book={br}: trades={st.mean(K):.2f} eff={st.mean(E):.3f} alpha={st.mean(A):.1f} commission={st.mean(C):.3f}")
