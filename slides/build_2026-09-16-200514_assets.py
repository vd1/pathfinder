"""Freeze talk data and render vector heatmaps without external plot dependencies."""
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import statistics

REPO = Path(__file__).resolve().parent.parent
AG = REPO.parent / "agQSL"
OUT = REPO / "slides/assets/2026-09-16-200514"
OUT.mkdir(parents=True, exist_ok=False)
provenance = {}

def records(path):
    data = path.read_bytes()
    provenance[str(path.relative_to(path.parents[len(path.parts)-3])) if False else str(path)] = hashlib.sha256(data).hexdigest()
    return [json.loads(line) for line in data.splitlines() if line.strip()]

def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")

def heatmap(name, matrix):
    """Minimal vector PDF: each cell is a filled rectangle, no text is rasterised."""
    rows, cols = len(matrix), len(matrix[0])
    width, height = 600, 400
    cw, ch = width / cols, height / rows
    commands = []
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            if value is None:
                colour = (0.80, 0.81, 0.82)
            else:
                t = min(1, max(0, value)) ** 0.65
                colour = tuple(1 + t * (v / 255 - 1) for v in (21, 102, 121))
            commands.append(f"{colour[0]:.4f} {colour[1]:.4f} {colour[2]:.4f} rg {j*cw:.3f} {height-(i+1)*ch:.3f} {cw+.01:.3f} {ch+.01:.3f} re f")
    stream = "\n".join(commands).encode()
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << >> /Contents 4 0 R >>".encode(),
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for n, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{n} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    (OUT / name).write_bytes(output)

J = AG / "pathfinder_Julien_edition/phase_a"
release = J / "releases/release:v1:79b313a898717711e523f8f0131b63668275570c37eeb28266a7c636bc63c058"
jq, jp, pairs = records(release / "q.jsonl"), records(release / "p.jsonl"), records(release / "pairs.jsonl")
events = records(J / "verdicts.jsonl")
pairmap = {p["pair_id"]: p for p in pairs}
groups = defaultdict(dict)
for event in events:
    if event["pair_id"] in pairmap:
        groups[event["instrument_id"]][event["pair_id"]] = event
instrument, selected = max(groups.items(), key=lambda item: len(item[1]))
jmatrix = [[None for p in jp] for q in jq]
for pair_id, event in selected.items():
    pair, scores = pairmap[pair_id], event["agent"]["scores"]
    jmatrix[pair["q_admitted_ordinal"]-1][pair["p_admitted_ordinal"]-1] = scores["feasibility"] * scores["prospective_gain"] / 10000
jinfo = {"rows": len(jq), "columns": len(jp), "pairs": len(pairs), "scored": len(selected),
    "instrument": instrument, "models": dict(Counter(e["served_model"] for e in selected.values())),
    "decisions": dict(Counter(e["agent"]["decision"] for e in selected.values())),
    "metric": "feasibility times prospective gain / 10000; latest recorded event per pair for the most-covered instrument",
    "dates": [min(e["accepted_at"] for e in selected.values()), max(e["accepted_at"] for e in selected.values())],
    "q_titles": [q["title"] for q in jq], "p_titles": [p["title"] for p in jp], "matrix": jmatrix}
write("julien-data.json", jinfo)
heatmap("julien-heatmap.pdf", jmatrix)

P = AG / "pathfinder3/ledger"
qslpairs = [p for p in records(P / "pairs.jsonl") if p.get("corpus_snapshot") == "d8deb3c"]
qids = sorted({p["c1"]["item_id"] for p in qslpairs})
pids = sorted({p["c2"]["item_id"] for p in qslpairs})
qindex, pindex = {q: i for i, q in enumerate(qids)}, {p: i for i, p in enumerate(pids)}
qslmap = {p["pair_id"]: p for p in qslpairs}
target = "7f01f7e54dc02bbc59a447ea77c51c9fe8b16291b8d4e52e37ce1ed0b433b046"
qslverdicts = {}
for row in records(P / "verdicts.jsonl"):
    if row.get("instrument_id") == target and row["pair_id"] in qslmap:
        qslverdicts[row["pair_id"]] = row
if not qslverdicts:
    raise RuntimeError("The documented QSL instrument has no local verdicts.")
qmatrix = [[None for p in pids] for q in qids]
for pair_id, row in qslverdicts.items():
    p = qslmap[pair_id]
    qmatrix[qindex[p["c1"]["item_id"]]][pindex[p["c2"]["item_id"]]] = row["corr"] * row["int"]
qinfo = {"rows": len(qids), "columns": len(pids), "pairs": len(qslmap), "scored": len(qslverdicts),
    "instrument": target, "model": "claude-opus-5", "freeze": "d8deb3c",
    "metric": "technical hook times interest; latest local verdict per frozen pair and documented instrument",
    "q_ids": qids, "p_ids": pids, "matrix": qmatrix}
write("qsl-data.json", qinfo)
heatmap("qsl-heatmap.pdf", qmatrix)

receipts = records(REPO / "receipts.jsonl")
categories = {"scan": "Scan", "peers": "Research", "consolidate": "Research", "verify": "Research",
    "author": "Manuscript", "review": "Manuscript", "edit": "Readable account", "probe": "Probe"}
costs = defaultdict(lambda: {"calls": 0, "input": 0, "output": 0, "seconds": 0, "scenario_usd": 0})
for row in receipts:
    bucket = costs[categories.get(row["stage"], row["stage"]) ]
    bucket["calls"] += 1
    bucket["input"] += row.get("input_tokens") or 0
    bucket["output"] += row.get("output_tokens") or 0
    bucket["seconds"] += row.get("seconds") or 0
    bucket["scenario_usd"] += ((row.get("input_tokens") or 0)*10 + (row.get("output_tokens") or 0)*50)/1e6
times = [datetime.fromisoformat(r["at"].replace("Z", "+00:00")) for r in receipts]
economics = {"stages": dict(costs), "calls": len(receipts), "recorded_input": sum(c["input"] for c in costs.values()),
    "recorded_output": sum(c["output"] for c in costs.values()), "scenario_usd": sum(c["scenario_usd"] for c in costs.values()),
    "campaign_span_hours": (max(times)-min(times)).total_seconds()/3600,
    "agent_hours": sum(c["seconds"] for c in costs.values())/3600,
    "cache_fields_present": sum("cache_read" in r for r in receipts),
    "interpretation": "Illustrative flat short-context GPT-6 Standard tariff applied to recorded input/output only. All recorded input treated as uncached. Missing Claude cache usage, unknown cached share of Codex input, request-level long-context adjustments and separately billed tools prevent an exact campaign repricing. Not an observed medium-effort run or a bill.",
    "pricing_source": "https://developers.openai.com/api/docs/models/gpt-6-astra", "pricing_date": "2026-09-16"}
write("economics.json", economics)
write("provenance.json", {"frozen_at": datetime.now().astimezone().isoformat(),
    "source_sha256": {str(Path(k).relative_to(REPO.parent)): v for k,v in provenance.items()},
    "notes": "No source records were modified. Grey heatmap cells mean no matching recorded verdict, not zero."})
macros = {"JulienRows": len(jq), "JulienColumns": len(jp), "JulienPairs": f"{len(pairs):,}",
    "JulienScored": f"{len(selected):,}", "JulienMissing": f"{len(pairs)-len(selected):,}",
    "QSLRows": len(qids), "QSLColumns": len(pids), "QSLPairs": f"{len(qslmap):,}",
    "QSLScored": f"{len(qslverdicts):,}", "ScenarioTotal": f"{economics['scenario_usd']:.0f}",
    "RecordedInput": f"{economics['recorded_input']/1e6:.1f}", "RecordedOutput": f"{economics['recorded_output']/1e6:.2f}",
    "CampaignSpan": f"{economics['campaign_span_hours']:.1f}", "AgentHours": f"{economics['agent_hours']:.1f}"}
for stage, macro in [("Scan", "ScanCost"), ("Research", "ResearchCost"), ("Manuscript", "ManuscriptCost"), ("Readable account", "AccountCost")]:
    macros[macro] = f"{costs[stage]['scenario_usd']:.2f}"
(OUT / "numbers.tex").write_text("\n".join("\\newcommand{\\" + k + "}{" + str(v) + "}" for k,v in macros.items()) + "\n")
print(json.dumps({"julien": {k:v for k,v in jinfo.items() if k not in ("matrix", "q_titles", "p_titles")},
    "qsl": {k:v for k,v in qinfo.items() if k not in ("matrix", "q_ids", "p_ids")}, "economics": economics}, indent=2))
