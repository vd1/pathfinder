"""Controlled test of the AR first-pass stopping signal with a free local model.

NOT a reproduction of P. Different model (local gemma4:26b via ollama, no paid
API), different tasks (HumanEvalPack/HumanEvalFix python: 164 problems, each
with a canonical and a buggy solution and hidden tests), review-only.

Question tested: does the critic's first-round verdict carry information about
correctness beyond the reviewer's verdict? In AR (P Sec 3, MARS -> AR) the
outer loop stops only if R approves AND C agrees at once (first-pass rule).
A zero-intelligence critic that disagrees at the matched rate d gives
TPR_R (1-d), FPR_R (1-d): same likelihood ratio as R alone. So C is
informative for stopping iff P(C agree | R approve, correct) differs from
P(C agree | R approve, buggy). A second independent reviewer R2 (unanimity,
no interaction) is the non-interacting control.

Prompts: P App. A "reviewer prompt (LCB)" and "AR: critic prompt (LCB)",
verbatim. frozen_ask = HumanEval prompt (signature + docstring).
"""
import json, os, random, re, subprocess, sys, tempfile, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = "/tmp/hep.jsonl"
OUT = os.path.join(HERE, "stop_signal_calls.jsonl")
MODEL = os.environ.get("MODEL", "gemma4:26b")
TEMP = 0.7
NUM_PREDICT = 1200
# Deviation from P, for local throughput: a system line asking for brevity.
# P prompts themselves are unchanged. The first verbose call is kept in
# stop_signal_calls_verbose_pilot.jsonl and excluded from the analysis.
SYSTEM = "Keep your whole response under 200 words. Always end with the required verdict line."

REVIEWER = """You are a senior software engineer reviewing a code artifact.

## Frozen original ask (verbatim -- do not paraphrase)
{frozen_ask}

## Artifact to review
```python
{artifact_code}
```

## Previous inner-loop exchange (if any)
{prior_exchange}

## Your task
Review the code for correctness. Flag bugs, edge cases, and logic errors ONLY.
Do not comment on style. Be specific -- cite line numbers or code snippets.

## Output format
End your review with a verdict line on its own, one of:

  APPROVE

or

  NEEDS_CHANGES: <one-line summary of top issue>

Any other final line is invalid.
"""

CRITIC = """You are critiquing a fellow engineer's code review.

## Frozen original ask (verbatim)
{frozen_ask}

## Artifact being reviewed
```python
{artifact_code}
```

## Reviewer's latest review
{reviewer_latest}

## Prior inner-loop exchange (if any)
{prior_exchange}

## Your task (TWO dimensions)
1. Is every issue the reviewer flagged actually a real bug? Flag spurious ones.
2. Did the reviewer miss any real bugs? Name them.

## Output format
End your response with a verdict line on its own, one of:

  AGREE

(if you agree with the reviewer and name no additional missed bugs)

or

  DISAGREE: <one-line summary of what you disagree with or what's missed>

Any other final line is invalid.
"""

lock = threading.Lock()


def ollama(prompt, seed):
    body = json.dumps({"model": MODEL, "system": SYSTEM, "prompt": prompt, "stream": False, "think": False,
                       "options": {"temperature": TEMP, "seed": seed, "num_predict": NUM_PREDICT,
                                                   "num_ctx": 16384}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    return d["response"], d.get("eval_count")


def verdict(text, kinds):
    """Kind named on the last non-empty line; markdown marks and a 'Verdict:' prefix are ignored."""
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return "INVALID"
    s = re.sub(r"[*`#>]", "", lines[-1]).strip().upper()
    s = re.sub(r"^(FINAL\s+)?VERDICT\s*:?\s*", "", s)
    for k in kinds:
        if s.startswith(k):
            return k
    return "INVALID"


def passes(code, test, entry):
    src = code + "\n\n" + test + f"\n\ncheck({entry})\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(src)
    try:
        r = subprocess.run([sys.executable, f.name], capture_output=True, timeout=20)
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    finally:
        os.unlink(f.name)


def done_keys():
    """(task_id, version, role) -> logged text, for resuming."""
    keys = {}
    if os.path.exists(OUT):
        for l in open(OUT):
            d = json.loads(l)
            keys[(d["task_id"], d["version"], d["role"])] = d["text"]
    return keys


def log(rec):
    with lock:
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")


def run_artifact(row, version, code, ok, done):
    tid = row["task_id"]
    base = dict(task_id=tid, version=version, correct=ok, model=MODEL)
    ask = row["prompt"].strip()
    sid = int(tid.split("/")[1]) * 10 + (0 if version == "canonical" else 1)
    if (tid, version, "R") in done:
        rtxt = done[(tid, version, "R")]
    else:
        rtxt, n = ollama(REVIEWER.format(frozen_ask=ask, artifact_code=code, prior_exchange="(none)"), seed=sid)
        log(dict(base, role="R", verdict=verdict(rtxt, ["APPROVE", "NEEDS_CHANGES"]), tokens=n, text=rtxt))
    if verdict(rtxt, ["APPROVE", "NEEDS_CHANGES"]) != "APPROVE":
        return
    if (tid, version, "C") not in done:
        ctxt, n = ollama(CRITIC.format(frozen_ask=ask, artifact_code=code, reviewer_latest=rtxt, prior_exchange="(none)"), seed=sid + 100000)
        log(dict(base, role="C", verdict=verdict(ctxt, ["AGREE", "DISAGREE"]), tokens=n, text=ctxt))
    if (tid, version, "R2") not in done:
        r2, n = ollama(REVIEWER.format(frozen_ask=ask, artifact_code=code, prior_exchange="(none)"), seed=sid + 200000)
        log(dict(base, role="R2", verdict=verdict(r2, ["APPROVE", "NEEDS_CHANGES"]), tokens=n, text=r2))


def main():
    rows = [json.loads(l) for l in open(DATA)]
    random.Random(20260916).shuffle(rows)
    rows = rows[:int(os.environ.get("N", "164"))]
    done = done_keys()
    jobs = []
    for row in rows:
        for version, sol in (("canonical", row["canonical_solution"]), ("buggy", row["buggy_solution"])):
            code = row["prompt"] + sol
            ok = passes(code, row["test"], row["entry_point"])
            jobs.append((row, version, code, ok))
    print("ground truth:", sum(j[3] for j in jobs if j[1] == "canonical"), "canonical pass,",
          sum(j[3] for j in jobs if j[1] == "buggy"), "buggy pass", flush=True)
    with ThreadPoolExecutor(int(os.environ.get("PAR", "2"))) as ex:
        list(ex.map(lambda j: run_artifact(*j, done), jobs))


if __name__ == "__main__":
    main()
