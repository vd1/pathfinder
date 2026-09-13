"""Scatter of scan scores against thread endings for a campaign. Run from the campaign root:
uv run --with matplotlib python plans/figures/score_vs_outcome.py [OUT.png]"""
import json, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

out = sys.argv[1] if len(sys.argv) > 1 else "plans/figures/2026-09-13-score-vs-outcome.png"
rows = [json.loads(l) for l in open("scan.jsonl")]
sl = {p["pair_id"] for p in json.load(open("shortlist.json"))["pairs"]}
LEGACY = {"accepted": "ACCEPTED", "returned": "PAUSE-ON-AMEND"}

def paper(pid):
    f = f"threads/{pid}/paper/paper.json"
    if not os.path.exists(f): return None
    s = json.load(open(f))["status"]; return LEGACY.get(s, s)

def status(pid):
    f = f"threads/{pid}/status.json"; return json.load(open(f))["status"] if os.path.exists(f) else None

pts = []
for r in rows:
    pid = r["pair_id"]; f = r.get("feasibility") or 0; g = r.get("gain") or 0
    if pid not in sl: out_ = "not selected"
    elif paper(pid) == "ACCEPTED": out_ = "paper accepted"
    elif status(pid) == "DRAFT": out_ = "DRAFT, no accepted paper"
    else: out_ = status(pid)
    pts.append((pid, f, g, f * g, out_))
col = {"not selected": "#c8cbd0", "PAUSE": "#6b7280", "PAUSE-ON-ITERATE": "#b7791f", "PAUSE-ON-REVISE": "#b7791f",
       "DRAFT, no accepted paper": "#7aa2ff", "paper accepted": "#1a7f4b"}
mk = {"not selected": ".", "PAUSE": "o", "PAUSE-ON-ITERATE": "s", "PAUSE-ON-REVISE": "D", "DRAFT, no accepted paper": "^", "paper accepted": "*"}
present = [o for o in col if any(p[4] == o for p in pts)]
fig, ax = plt.subplots(1, 2, figsize=(12, 5.2))
for o in present:
    xs = [p[1] for p in pts if p[4] == o]; ys = [p[2] for p in pts if p[4] == o]
    big = o == "paper accepted"; sel = o != "not selected"
    ax[0].scatter(xs, ys, c=col[o], marker=mk[o], s=160 if big else (60 if sel else 30), label=f"{o} ({len(xs)})",
                  edgecolors="k" if sel else "none", linewidths=0.5, zorder=3 if sel else 1)
for p in pts:
    if p[4] != "not selected": ax[0].annotate(p[0], (p[1], p[2]), xytext=(4, 4), textcoords="offset points", fontsize=7)
thr = json.load(open("shortlist.json")).get("min_score")
if thr:
    x = np.linspace(thr / 100, 100, 200); ax[0].plot(x, thr / x, "--", c="#999", lw=0.8)
    ax[0].text(97, thr / 97 + 1, f"score {thr:.0f}", fontsize=7, ha="right", color="#666")
ax[0].set_xlabel("feasibility (0 to 100)"); ax[0].set_ylabel("gain (0 to 100)")
ax[0].set_title(f"scan scores of all {len(pts)} pairs, endings of the {len(sl)} threads")
ax[0].set_xlim(0, 102); ax[0].set_ylim(0, 102); ax[0].legend(fontsize=8, loc="upper left")
order = [o for o in ("PAUSE", "PAUSE-ON-ITERATE", "PAUSE-ON-REVISE", "DRAFT, no accepted paper", "paper accepted") if o in present]
for i, o in enumerate(order):
    sc = [p[3] for p in pts if p[4] == o]
    ax[1].scatter(sc, [i] * len(sc), c=col[o], marker=mk[o], s=160 if o == "paper accepted" else 60, edgecolors="k", linewidths=0.5)
    for p in pts:
        if p[4] == o: ax[1].annotate(p[0], (p[3], i), xytext=(0, 8), textcoords="offset points", fontsize=7, ha="center")
ax[1].set_yticks(range(len(order))); ax[1].set_yticklabels(order); ax[1].set_xlabel("score = feasibility x gain")
ax[1].set_title(f"the {len(sl)} threads: score against ending"); ax[1].set_ylim(-0.6, len(order) - 0.4); ax[1].grid(axis="x", alpha=0.3)
fig.tight_layout(); fig.savefig(out, dpi=130); print(out)
