"""Analyse ada/stop_signal_calls.jsonl (see stop_signal_exp.py).

Stopping rules on a fixed artifact (approve = stop and ship):
  R      : R says APPROVE
  AR     : R says APPROVE and C says AGREE (P first-pass termination)
  ZI-C   : R says APPROVE and a coin with P(disagree) = d, d matched to C
  R&R2   : R and an independent R2 both APPROVE (no interaction)
TPR = P(approve | correct), FPR = P(approve | buggy).
"""
import json, os, sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from stop_signal_exp import verdict  # noqa: E402

recs = [json.loads(l) for l in open(os.path.join(HERE, "stop_signal_calls.jsonl"))]
for r in recs:  # re-parse with the current parser; the logged field may predate a parser fix
    r["verdict"] = verdict(r["text"], ["AGREE", "DISAGREE"] if r["role"] == "C" else ["APPROVE", "NEEDS_CHANGES"])
by = {}
for r in recs:
    by.setdefault((r["task_id"], r["version"]), {})[r["role"]] = r


def fisher_two_sided(a, b, c, d):
    """Fisher exact test for [[a, b], [c, d]]."""
    n1, n2, k, n = a + b, c + d, a + c, a + b + c + d
    p = lambda x: comb(n1, x) * comb(n2, k - x) / comb(n, k)
    obs = p(a)
    lo, hi = max(0, k - n2), min(k, n1)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9)))


def wilson(x, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    ph = x / n
    den = 1 + z * z / n
    mid = (ph + z * z / (2 * n)) / den
    half = z * ((ph * (1 - ph) / n + z * z / (4 * n * n)) ** 0.5) / den
    return (mid - half, mid + half)


# only complete artifacts: R done, and if R approved then C and R2 done
arts = []
for key, roles in by.items():
    if "R" not in roles:
        continue
    if roles["R"]["verdict"] == "APPROVE" and not ("C" in roles and "R2" in roles):
        continue
    arts.append((key, roles))

invalid = sum(1 for r in recs if r["verdict"] == "INVALID")
print(f"records {len(recs)}, complete artifacts {len(arts)}, invalid verdict lines {invalid}")
print("ground truth: canonical passing", sum(1 for k, r in arts if k[1] == "canonical" and r["R"]["correct"]),
      "of", sum(1 for k, r in arts if k[1] == "canonical"),
      "; buggy passing", sum(1 for k, r in arts if k[1] == "buggy" and r["R"]["correct"]),
      "of", sum(1 for k, r in arts if k[1] == "buggy"))

pos = [r for k, r in arts if r["R"]["correct"]]
neg = [r for k, r in arts if not r["R"]["correct"]]
rules = {
    "R": lambda r: r["R"]["verdict"] == "APPROVE",
    "AR": lambda r: r["R"]["verdict"] == "APPROVE" and r["C"]["verdict"] == "AGREE",
    "R&R2": lambda r: r["R"]["verdict"] == "APPROVE" and r["R2"]["verdict"] == "APPROVE",
}
appr = [r for k, r in arts if r["R"]["verdict"] == "APPROVE"]
d = sum(1 for r in appr if r["C"]["verdict"] != "AGREE") / max(1, len(appr))
print(f"\nn correct {len(pos)}, n buggy {len(neg)}; R approvals {len(appr)}; matched C disagree rate d = {d:.3f}")
print(f"{'rule':6} {'TPR':>14} {'FPR':>14} {'shipped-buggy share':>20}")
res = {}
for name, f in rules.items():
    tp, fp = sum(map(f, pos)), sum(map(f, neg))
    res[name] = (tp, fp)
    share = fp / (tp + fp) if tp + fp else float("nan")
    print(f"{name:6} {tp:3}/{len(pos):3}={tp/len(pos):.3f} {fp:3}/{len(neg):3}={fp/len(neg):.3f} {share:20.3f}")
tp, fp = res["R"]
print(f"ZI-C   {tp*(1-d):7.2f}/{len(pos):3}={tp*(1-d)/len(pos):.3f} {fp*(1-d):6.2f}/{len(neg):3}={fp*(1-d)/len(neg):.3f} "
      f"{(fp/(tp+fp) if tp+fp else float('nan')):20.3f}")

# informativeness of C on R-approved artifacts
a = sum(1 for r in appr if r["R"]["correct"] and r["C"]["verdict"] == "AGREE")
b = sum(1 for r in appr if r["R"]["correct"] and r["C"]["verdict"] != "AGREE")
c = sum(1 for r in appr if not r["R"]["correct"] and r["C"]["verdict"] == "AGREE")
e = sum(1 for r in appr if not r["R"]["correct"] and r["C"]["verdict"] != "AGREE")
print(f"\nC on R-approved: correct agree/disagree {a}/{b}; buggy agree/disagree {c}/{e}")
if a + b:
    print(f"  P(C agree | approved, correct) = {a/(a+b):.3f} CI {wilson(a, a+b)}")
if c + e:
    print(f"  P(C agree | approved, buggy)   = {c/(c+e):.3f} CI {wilson(c, c+e)}")
print(f"  Fisher two-sided p = {fisher_two_sided(a, b, c, e):.4g}")
a2 = sum(1 for r in appr if r["R"]["correct"] and r["R2"]["verdict"] == "APPROVE")
b2 = sum(1 for r in appr if r["R"]["correct"] and r["R2"]["verdict"] != "APPROVE")
c2 = sum(1 for r in appr if not r["R"]["correct"] and r["R2"]["verdict"] == "APPROVE")
e2 = sum(1 for r in appr if not r["R"]["correct"] and r["R2"]["verdict"] != "APPROVE")
print(f"R2 on R-approved: correct approve/flag {a2}/{b2}; buggy approve/flag {c2}/{e2}; Fisher p = {fisher_two_sided(a2, b2, c2, e2):.4g}")

# where does C disagree: does it name a missed bug on buggy code that R approved?
print("\nC disagreements on R-approved artifacts (task, version, correct, C summary):")
for k, r in arts:
    if r["R"]["verdict"] == "APPROVE" and r["C"]["verdict"] != "AGREE":
        last = [l for l in r["C"]["text"].strip().splitlines() if l.strip()][-1][:150]
        print(" ", k[0], k[1], r["R"]["correct"], "|", last)
print("\nR flags on correct code (false alarms):", sum(1 for r in pos if r["R"]["verdict"] != "APPROVE"), "of", len(pos))
