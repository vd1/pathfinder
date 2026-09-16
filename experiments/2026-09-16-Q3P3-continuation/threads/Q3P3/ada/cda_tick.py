"""(1) ZI-equivalent horizon: T at which ZI-C matches each Q Table 1 mean efficiency.
(2) Creeper agents on a tick grid: the only admissible non-crossing move is one tick
beyond the standing own-side quote; an agent crosses only when a one-tick improvement
would reach the opposite quote (spread <= tick). Variant 'res2': the first quote posted
on the second side of the book is at the poster's reservation price (Q Sec 4.2, GPT Large).
Question: how do trades/efficiency at T=300 depend on tick size?"""
import random, statistics as st
from cda_sim import VALS, SMAX, metrics

def run_round(policy, rng, T, tick):
    agents = [("B", v) for v in VALS] + [("S", c) for c in VALS]
    active = set(range(22)); bid = ask = None; trades = []
    first_side = None
    for t in range(T):
        if not active: break
        i = rng.choice(sorted(active)); side, r = agents[i]
        q = policy(side, r, bid, ask, rng, tick, first_side)
        if q is None: continue
        q = round(round(q / tick) * tick, 2)
        if first_side is None: first_side = side
        if side == "B":
            if ask is not None and q >= ask[0]:
                p, j = ask; trades.append((p, r, agents[j][1])); active -= {i, j}; bid = ask = None
            elif bid is None or q > bid[0]: bid = (q, i)
        else:
            if bid is not None and q <= bid[0]:
                p, j = bid; trades.append((p, agents[j][1], r)); active -= {i, j}; bid = ask = None
            elif ask is None or q < ask[0]: ask = (q, i)
    return trades

def zi_c(side, r, bid, ask, rng, tick, fs):
    return rng.uniform(0, r) if side == "B" else rng.uniform(r, 4.0)

def creeper(res2):
    def pol(side, r, bid, ask, rng, tick, first_side):
        own, opp = (bid, ask) if side == "B" else (ask, bid)
        sgn = 1 if side == "B" else -1
        if own is None:
            if res2 and first_side is not None and first_side != side:
                q = r  # second side opens at reservation
            else:
                q = r - sgn * rng.uniform(0.25, 1.25)
            if opp is not None and sgn * (q - opp[0]) >= 0:
                # opening would cross: only if within budget (always true here since q vs r)
                return opp[0] if sgn * (r - opp[0]) >= 0 else None
            return q if q >= 0 else None
        q = own[0] + sgn * tick
        if sgn * (q - r) > 1e-9: return None  # budget
        return q  # crosses automatically if q reaches opp
    return pol

def run(policy, T, tick, n=1500, seed=3):
    rng = random.Random(seed); E = []; K = []
    for _ in range(n):
        k, mp, al, ef = metrics(run_round(policy, rng, T, tick)); E.append(ef); K.append(k)
    return st.mean(K), st.mean(E)

print("(1) ZI-C efficiency vs horizon T (cents grid)")
zi = {}
for T in (30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200, 250, 300):
    k, e = run(zi_c, T, 0.01); zi[T] = e; print(f"   T={T:3d}: trades={k:4.2f} eff={e:5.3f}")
Q = {"GPT Large": 0.53, "Gemini Large": 0.698, "GPT Small": 0.868}
for m, target in Q.items():
    Ts = sorted(zi); Teq = None
    for a, b in zip(Ts, Ts[1:]):
        if zi[a] <= target <= zi[b]:
            Teq = a + (target - zi[a]) / (zi[b] - zi[a]) * (b - a); break
    print(f"   ZI-equivalent horizon for {m} (mean eff {target}): T~{Teq:.0f}" if Teq else f"   {m}: out of range")

print("\n(2) creeper agents, T=300, by tick size")
for res2 in (False, True):
    for tick in (0.01, 0.02, 0.05, 0.10, 0.25):
        k, e = run(creeper(res2), 300, tick)
        print(f"   res2={res2!s:5s} tick={tick:4.2f}: trades={k:4.2f} eff={e:5.3f}")
print("\n   ZI-C by tick size, T=300 (control: random traders should be tick-insensitive)")
for tick in (0.01, 0.05, 0.25):
    k, e = run(zi_c, 300, tick); print(f"   tick={tick:4.2f}: trades={k:4.2f} eff={e:5.3f}")
