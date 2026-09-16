"""Isolated, subscription-authenticated repeat scan and paired-score comparison."""
import datetime
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
sys.path.insert(0, str(REPO))
from pathfinder.scan import parse_json

MODEL = "claude-sonnet-5"
OUT = ROOT / "doc/logs/claude_outputs"
OUT.mkdir(parents=True, exist_ok=True)
LOG = ROOT / "doc/logs/claude_call_log.md"
LOG.write_text("# Repeat scan calls\n\n| Call | Owner | Creativity | Purpose | Status |\n| --- | --- | --- | --- | --- |\n")
ENV = {k: v for k, v in os.environ.items() if not any(s in k for s in ("API_KEY", "OPENAI_", "ANTHROPIC_API", "ELM_"))}
schedule, results, receipts = [], [], []
started = time.monotonic()
child = None
cancelled = False

def save(name, obj):
    temporary = ROOT / (name + ".tmp")
    temporary.write_text(json.dumps(obj, indent=2) + "\n")
    temporary.replace(ROOT / name)

def append(name, obj):
    with (ROOT / name).open("a") as stream:
        stream.write(json.dumps(obj) + "\n")

def rows(name):
    return [json.loads(line) for line in (ROOT / name).read_text().splitlines() if line.strip()]

def stop(signum, frame):
    global cancelled
    cancelled = True
    if child is not None and child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

def progress(status):
    save("status.json", {"status": status, "pid": os.getpid(), "model": MODEL,
         "completed_pairs": len(results), "total_pairs": len(qs) * len(ps),
         "valid_pairs": sum(r["error"] is None for r in results),
         "calls": len(receipts), "api_equivalent_usd_reported": sum(r["cost"] or 0 for r in receipts),
         "elapsed_seconds": round(time.monotonic() - started, 2),
         "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})

qs, ps = rows("Q.jsonl"), rows("P.jsonl")
header = json.loads((ROOT / "prompt-header.json").read_text())
progress("running")
for qi, q in enumerate(qs, 1):
    for pi, p in enumerate(ps, 1):
        if cancelled or (ROOT / "STOP").exists():
            cancelled = True
            break
        pair = f"Q{qi}P{pi}"
        prompt = header + f"## Q\n\nTitle: {q['title']}\n\n{q['abstract']}\n\n## P\n\nTitle: {p['title']}\n\n{p['abstract']}\n"
        append("prompts.jsonl", {"pair_id": pair, "prompt": prompt})
        value, error = None, None
        pair_seconds, pair_cost = 0.0, 0.0
        for attempt in (1, 2):
            call_id = f"claude-{pair}-{attempt:02d}"
            entry = {"call_id": call_id, "owner": "scan judge", "creativity": "CLI default",
                     "purpose": f"Repeat abstract scan for {pair}", "status": "running"}
            schedule.append(entry)
            save("schedule.json", schedule)
            call_started = time.monotonic()
            reply, stdout, stderr, error = {}, "", "", None
            try:
                child = subprocess.Popen(["claude", "-p", "--model", MODEL, "--output-format", "json",
                    "--tools", "", "--strict-mcp-config", "--no-session-persistence", "--max-turns", "1"],
                    cwd=ROOT, env=ENV, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True, start_new_session=True)
                try:
                    stdout, stderr = child.communicate(prompt if attempt == 1 else "Return only the requested JSON object.\n\n" + prompt, timeout=180)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGTERM)
                    try:
                        stdout, stderr = child.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        stdout, stderr = child.communicate()
                    raise ValueError("timeout")
                if stdout.strip():
                    reply = json.loads(stdout)
                if cancelled:
                    raise ValueError("cancelled")
                if child.returncode:
                    raise ValueError(stderr[-1200:] or f"exit {child.returncode}")
                if reply.get("is_error"):
                    raise ValueError(reply.get("result") or reply.get("subtype") or "model error")
                value = parse_json(reply.get("result", ""))
                if any(type(value.get(k)) is not int or not 0 <= value[k] <= 100 for k in ("feasibility", "gain")):
                    raise ValueError("invalid scores")
                if any(not isinstance(value.get(k), str) or not value[k].strip() for k in ("connexion", "rationale")):
                    raise ValueError("missing connexion or rationale")
            except (ValueError, TypeError, KeyError, OSError) as exc:
                value, error = None, str(exc)
            finally:
                child = None
            seconds = round(time.monotonic() - call_started, 2)
            (OUT / f"{call_id}.txt").write_text(stdout)
            if stderr:
                (OUT / f"{call_id}.stderr.log").write_text(stderr)
            usage = reply.get("usage") or {}
            receipt = {"call_id": call_id, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "thread": pair, "stage": "scan", "actor": "judge", "backend": "claude", "model": MODEL,
                "seconds": seconds, "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"), "cache_write": usage.get("cache_creation_input_tokens"),
                "cache_read": usage.get("cache_read_input_tokens"), "cost": reply.get("total_cost_usd"),
                "session": reply.get("session_id"), "error": error}
            receipts.append(receipt)
            append("receipts.jsonl", receipt)
            pair_seconds += seconds
            pair_cost += receipt["cost"] or 0
            entry["status"] = "completed" if value else ("cancelled" if cancelled else "failed")
            with LOG.open("a") as stream:
                stream.write(f"| {call_id} | scan judge | CLI default | Repeat {pair} | {entry['status']} |\n")
            save("schedule.json", schedule)
            progress("running")
            if value or cancelled:
                break
        result = {"pair_id": pair, "q": q["id"], "p": p["id"], "feasibility": None,
            "gain": None, "connexion": None, "rationale": None, **(value or {}), "model": MODEL,
            "seconds": round(pair_seconds, 2), "cost": pair_cost, "error": error}
        result["score"] = result["feasibility"] * result["gain"] if value else None
        results.append(result)
        append("scan.jsonl", result)
        progress("running")
        print(f"{pair}: feasibility={result['feasibility']} gain={result['gain']} error={error}", flush=True)
    if cancelled:
        break

baseline = {r["pair_id"]: r for r in rows("baseline-scan.jsonl")}
def valid(row):
    return all(type(row.get(k)) is int for k in ("feasibility", "gain"))

matched = [(baseline[r["pair_id"]], r) for r in results if r["pair_id"] in baseline and valid(r) and valid(baseline[r["pair_id"]])]
comparison = {"matched_original_pairs": len(matched), "excluded_original_unparseable": [k for k, r in baseline.items() if not valid(r)],
    "interpretation": "Two-run within-pair variance is squared difference / 2. Its mean pools pair-specific estimates; it is not precise per-pair variance. Model version and time effects cannot be separated from sampling variability.",
    "axes": {}}
for axis in ("feasibility", "gain", "score"):
    def score(r):
        return r["feasibility"] * r["gain"] if axis == "score" else r[axis]
    differences = [score(new) - score(old) for old, new in matched]
    if differences:
        pooled = statistics.mean(d * d / 2 for d in differences)
        comparison["axes"][axis] = {"mean_change": statistics.mean(differences),
            "mean_absolute_change": statistics.mean(abs(d) for d in differences),
            "root_mean_squared_change": math.sqrt(statistics.mean(d*d for d in differences)),
            "mean_within_pair_sample_variance": pooled, "pooled_within_pair_sd": math.sqrt(pooled),
            "unchanged_pairs": sum(d == 0 for d in differences),
            "per_pair": [{"pair_id": new["pair_id"], "original": score(old), "repeat": score(new),
                "change": score(new)-score(old), "two_run_sample_variance": (score(new)-score(old))**2/2} for old,new in matched]}
comparison["threshold_1500_crossings"] = [{"pair_id": new["pair_id"],
    "original": old["feasibility"]*old["gain"], "repeat": new["feasibility"]*new["gain"]}
    for old,new in matched if (old["feasibility"]*old["gain"] >= 1500) != (new["feasibility"]*new["gain"] >= 1500)]
comparison["repeat_zero_scores"] = sum(valid(r) and r["score"] == 0 for r in results)
q1p7_old = rows("baseline-Q1P7-rescan.jsonl")[0]
comparison["Q1P7_separate_rescan_comparison"] = {"earlier_rescan": q1p7_old,
    "repeat": next((r for r in results if r["pair_id"] == "Q1P7"), None)}
save("comparison.json", comparison)
with (ROOT / "style-gates.log").open("w") as output:
    paths = [str(LOG)] + [str(p) for p in OUT.glob("*.txt")]
    gate = subprocess.run(["/Users/v/.local/bin/style-ban-artifacts", *paths], stdout=output, stderr=subprocess.STDOUT)
    pdf_gate = subprocess.run([sys.executable, "/Users/v/.codex/skills/style-gates/scripts/style_gate.py", str(LOG)], stdout=output, stderr=subprocess.STDOUT)
save("artifact-gates.json", {"style_ban_exit_code": gate.returncode, "style_gate_exit_code": pdf_gate.returncode})
progress("cancelled" if cancelled else "completed")
print("Repeat scan finished; comparison.json contains the paired-score analysis.", flush=True)
