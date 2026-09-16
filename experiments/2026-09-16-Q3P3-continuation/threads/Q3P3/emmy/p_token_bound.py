"""What P's LCB token medians imply about AR's first-pass acceptances.

Explanation of P's reported outcomes, not a reproduction. Inputs are the
coordinates of P Fig. 5a (median tokens per task; P says LCB medians are
"estimated from per-method call counts") and the counts fixed by
p_aggregate.py (ZS 81, SR 81, TwoR 79, AR 91 of 105).
"""
from math import comb

g, sr, twor, ar_med = 8000, 22000, 28000, 30000
# ZS = one generation g; SR = g + review r + edit e; TwoR = g + 2r + e
r = twor - sr
e = sr - g - r
print(f"per-call estimates: generation {g}, review r={r}, edit e={e}")
# cheapest AR trajectory that edits: g + r + c + e + r + c (P Sec 4: every
# edit is followed by a new inner review round)
for c in (1000, 2000, 4000, 6000):
    print(f"critic c={c}: cheapest edited AR task {g + 2*r + e + 2*c}, "
          f"cheapest unedited {g + r + c}; AR median {ar_med}")
print("=> if c > 1000, median 30000 < cheapest edited cost, so at least 53 of"
      " 105 AR tasks were accepted at first pass with v0 unedited\n")

N, AR_FAIL = 105, 14


def p_le(k, a, F):
    """P(at most k failing v0 among a tasks accepted uninformatively)."""
    return sum(comb(F, j) * comb(N - F, a - j)
               for j in range(0, min(k, a, F) + 1)) / comb(N, a)


print("P(uninformative first-pass acceptance of a tasks ships <= 14 failing v0)")
print("  a   F=20    F=24    F=28")
for a in range(53, 106, 4):
    print(f"{a:3d}  " + "  ".join(f"{p_le(AR_FAIL, a, F):.4f}" for F in (20, 24, 28)))
for F in (20, 24, 28):
    amax = max(a for a in range(53, 106) if p_le(AR_FAIL, a, F) >= 0.05)
    print(f"F={F}: uninformative acceptance compatible (p>=0.05) only if a <= {amax}")
