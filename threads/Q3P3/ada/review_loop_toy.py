"""Toy model: can 'iterate until the reviewer approves' alone produce AR-sized LCB gains,
under parameters consistent with P's finding Single-reviewer = Zero-shot = 77%?
State of the program: correct / wrong. Per cycle: reviewer approves a correct program w.p. a1,
a wrong one w.p. a0; approval stops the loop. If flagged, the author edits: wrong -> correct
w.p. f, correct -> wrong w.p. b. After K edits the loop stops without a further review
(as MARS 'after Round 2 revision, STOP'). K=1 is P's Single-reviewer. b is solved from
pass(K=1) = p0 so that one review-edit cycle has zero net effect, as P observed."""
p0 = 0.77

def pass_rate(K, a1, a0, f, b, d=0.0):
    # d: extra probability that a critic blocks approval (random disagreement), applied to both states
    A1, A0 = a1 * (1 - d), a0 * (1 - d)
    c, w, S = p0, 1 - p0, 0.0
    for _ in range(K):
        S += c * A1
        c_fl, w_fl = c * (1 - A1), w * (1 - A0)
        c, w = c_fl * (1 - b) + w_fl * f, c_fl * b + w_fl * (1 - f)
    return S + c

rows = []
for a1 in (0.7, 0.8, 0.9):
    for a0 in (0.2, 0.4, 0.6):
        for f in (0.2, 0.4, 0.6):
            # solve p0*(1-a1)*b = (1-p0)*(1-a0)*f
            b = (1 - p0) * (1 - a0) * f / (p0 * (1 - a1))
            if not (0 <= b <= 1):
                continue
            r = [pass_rate(K, a1, a0, f, b) for K in (1, 2, 3, 5)]
            rz = [pass_rate(K, a1, a0, f, b, d=0.3) for K in (2, 3, 5)]
            rows.append((a1, a0, f, b, r, rz))
print("a1   a0   f    b(solved) | K=1   K=2   K=3   K=5  | with random critic d=0.3: K=2  K=3  K=5")
for a1, a0, f, b, r, rz in rows:
    print(f"{a1:.1f}  {a0:.1f}  {f:.1f}  {b:5.3f}     | " + "  ".join(f"{x:.3f}" for x in r)
          + "  |   " + "  ".join(f"{x:.3f}" for x in rz))
gains = [r[2] - r[0] for *_, r, _ in rows]
print(f"\nadmissible parameter sets: {len(rows)}; gain K=3 over K=1: min {min(gains)*100:.1f}pp, "
      f"median {sorted(gains)[len(gains)//2]*100:.1f}pp, max {max(gains)*100:.1f}pp")
