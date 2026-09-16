"""Analysis of emmy/ar_ablation_runs.jsonl (written before any result was seen).

Decomposition of AR over Single-reviewer on paired tasks:
  AR - SR = (RO - SR)      iterate-to-clean stopping rule, no critic
          + (ARZ - RO)     content-free critic at matched DISAGREE rate (extra deliberation and edits)
          + (AR - ARZ)     information in the critic's messages
Stop-signal split (Q's omission / commission read on the first artifact v0):
  accept-clean given v0 correct   (right stop; its complement is an unnecessary edit)
  accept-clean given v0 wrong     (false consensus: a wrong artifact is shipped)
"""
import json, os, sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "ar_ablation_runs.jsonl"))]
ARMS = ["ZS", "SR", "RO", "AR", "ARZ"]


def ok(r, a):
    v = r[a]
    return bool(v["pass"]) if isinstance(v, dict) else bool(v)


def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


n = len(rows)
print(f"tasks {n}  (hard {sum(r['difficulty']=='hard' for r in rows)}, medium {sum(r['difficulty']=='medium' for r in rows)})")
for a in ARMS:
    s = sum(ok(r, a) for r in rows)
    calls = sum(r["stats"]["base"]["calls"] + (r["stats"][a]["calls"] if a in r["stats"] else 0)
                for r in rows) if a != "ZS" else sum(1 for r in rows)
    print(f"{a:4s} pass {s:3d}/{n}  calls/task {calls / n:5.1f}")

print("\npaired contrasts (b = first arm only, c = second arm only)")
for a, b in [("SR", "ZS"), ("RO", "SR"), ("ARZ", "RO"), ("AR", "ARZ"), ("AR", "RO"), ("AR", "SR")]:
    bb = sum(ok(r, a) and not ok(r, b) for r in rows)
    cc = sum(ok(r, b) and not ok(r, a) for r in rows)
    print(f"{a:4s} - {b:4s}: {bb - cc:+d}  (b={bb}, c={cc}, exact McNemar p={mcnemar(bb, cc):.3f})")

print("\nstop signal on v0 (accepted without any edit)")
for a in ["RO", "AR", "ARZ"]:
    acc_ok = sum(r[a]["edits"] == 0 and r["ZS"] for r in rows)
    acc_bad = sum(r[a]["edits"] == 0 and not r["ZS"] for r in rows)
    n_ok = sum(bool(r["ZS"]) for r in rows)
    broke = sum(r["ZS"] and not ok(r, a) for r in rows)
    fixed = sum((not r["ZS"]) and ok(r, a) for r in rows)
    print(f"{a:4s} accept|v0 correct {acc_ok}/{n_ok}  accept|v0 wrong {acc_bad}/{n - n_ok}"
          f"  broke {broke}  fixed {fixed}  mean edits {sum(r[a]['edits'] for r in rows) / n:.2f}")

for a in ["AR", "ARZ"]:
    cv = [x for r in rows for x in r[a]["c_verdicts"]]
    d1 = [not x[2] for x in cv if x[1] == 1]
    d2 = [not x[2] for x in cv if x[1] > 1]
    print(f"{a} critic DISAGREE rate: round 1 {sum(d1)}/{len(d1)}, later rounds {sum(d2)}/{len(d2)}")
    if a == "AR":
        # does the LLM critic's first verdict carry information about v0 correctness when R approved?
        t = [(r["ZS"], r[a]["c_verdicts"][0][2]) for r in rows if r["r1_approve"] is True and r[a]["c_verdicts"]]
        for z in (True, False):
            sub = [g for zz, g in t if zz == z]
            print(f"   R approved v0, v0 {'correct' if z else 'wrong'}: C agrees {sum(sub)}/{len(sub)}")
q = [r["ARZ"]["q_used"] for r in rows]
if q:
    print("ARZ q used (round 1, later):", sorted(set((round(a, 2), round(b, 2)) for a, b, _, _ in q)))
