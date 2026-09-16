"""Matched ablation of P's Adversarial Review (AR) on public LiveCodeBench stdin tasks.

NEW controlled experiment, not a reproduction of P: local gemma4:26b (no thinking)
instead of Sonnet 4.5, LCB release v6 stdin tasks instead of P's unlisted 105,
P App. A LCB prompts adapted from "function with entry point" to "stdin program".

Arms per task, sharing prefixes so comparisons are paired:
  ZS    zero-shot v0
  SR    Single-reviewer: R reviews v0, M edits once (always)
  RO    R-only iterate-to-clean: accept on APPROVE, else edit and re-review, cap E edits
  AR    R<->C inner loop (cap 5), first-pass termination, else edit, cap E edits
  ARZ   AR with content-free random critic, DISAGREE rate matched to realized AR rate
The first review of v0 is shared by SR, RO, AR, ARZ.
"""
import base64, json, os, pickle, random, re, subprocess, sys, tempfile, threading, time, zlib
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "lcb", "test6.jsonl")
OUT = os.path.join(HERE, "ar_ablation_runs.jsonl")
MODEL = os.environ.get("AR_MODEL", "gemma4:26b")
E_CAP, INNER_CAP = 3, 5
N_TASKS = int(os.environ.get("AR_NTASKS", "40"))
WORKERS = int(os.environ.get("AR_WORKERS", "2"))
LOCK = threading.Lock()

WRITE = """You are writing a Python program to satisfy a specification.

## Specification
{specification}

## Input/output (MANDATORY)
Your program MUST read all input from standard input and write the answer to standard
output. The hidden test harness runs the file as a script -- if you define a function
and never call it, every test fails regardless of semantic correctness.

## Previous consistent review (if outer iteration > 1)
{previous_review}

## Your task
Write the complete Python code. Emit ONLY the code -- no explanation, no prose,
no markdown fences (do NOT wrap in ```python ... ``` or ``` ... ```). The code
will be run verbatim against hidden tests.

Include all necessary imports at the top. If the specification references
helper utilities without defining them, implement them inline.
"""

EDIT = """You are revising a Python program based on a code review.

## Specification
{specification}

## Input/output (MANDATORY)
Your program MUST read from standard input and write to standard output.

## Previous version of your code
```python
{previous_artifact}
```

## Code review (consistent review from reviewer-critic loop)
{consistent_review}

## Your task
Rewrite the COMPLETE updated Python code addressing the review. Emit ONLY the
code -- no explanation, no prose, no markdown fences.
"""

REVIEW = """You are a senior software engineer reviewing a code artifact.

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

# Content-free critic message for the zero-intelligence arm: same verdict token, no information.
ZI_DISAGREE = ("I am not convinced this review is complete and correct. Re-check the code "
               "against the specification and revise the review.\n\nDISAGREE: review may be incomplete or wrong")
ZI_AGREE = "AGREE"


def llm(prompt, seed, stats):
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "think": False,
                       "options": {"temperature": 0.7, "seed": seed, "num_ctx": 16384,
                                   "num_predict": 3000}}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request("http://localhost:11434/api/generate", body,
                                         {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                d = json.load(r)
            stats["calls"] += 1
            with LOCK, open(os.path.join(HERE, "ar_ablation_calls.log"), "a") as lf:
                lf.write(f"{time.strftime('%H:%M:%S')} {d.get('prompt_eval_count', 0)} "
                         f"{d.get('eval_count', 0)} {d.get('total_duration', 0) / 1e9:.1f}\n")
            stats["in_tok"] += d.get("prompt_eval_count", 0)
            stats["out_tok"] += d.get("eval_count", 0)
            return d["response"]
        except Exception as e:  # retry transient server errors
            err = e
            time.sleep(5)
    raise err


def strip_code(s):
    m = re.findall(r"```(?:python|py)?\s*\n(.*?)```", s, re.S)
    return max(m, key=len) if m else s.strip()


def verdict(text, ok, bad):
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    for l in reversed(lines[-3:]):
        l2 = l.strip("*` ")
        if l2.startswith(bad):
            return False
        if l2.startswith(ok):
            return True
    return None  # invalid final line; treated as not-OK (conservative)


def load_tasks():
    tasks = []
    with open(DATA) as f:
        for line in f:
            d = json.loads(line)
            pub = json.loads(d["public_test_cases"])
            if not pub or pub[0]["testtype"] != "stdin" or d.get("starter_code"):
                continue
            tasks.append(d)
    return tasks


def tests_of(d):
    pub = json.loads(d["public_test_cases"])
    priv = d["private_test_cases"]
    try:
        priv = json.loads(priv)
    except Exception:
        priv = json.loads(pickle.loads(zlib.decompress(base64.b64decode(priv.encode()))))
    return [(t["input"], t["output"]) for t in pub + priv]


def same(out, exp):
    a, b = out.strip().split(), exp.strip().split()
    if a == b:
        return True
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x == y:
            continue
        try:
            if abs(float(x) - float(y)) > 1e-6 * max(1.0, abs(float(y))):
                return False
        except ValueError:
            return False
    return True


def run_tests(code, tests, cache):
    if code in cache:
        return cache[code]
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code)
        path = f.name
    ok, t0 = True, time.time()
    try:
        for inp, exp in tests:
            try:
                p = subprocess.run([sys.executable, path], input=inp, capture_output=True,
                                   text=True, timeout=10)
            except subprocess.TimeoutExpired:
                ok = False
                break
            if p.returncode != 0 or not same(p.stdout, exp):
                ok = False
                break
            if time.time() - t0 > 240:
                ok = False
                break
    finally:
        os.unlink(path)
    cache[code] = ok
    return ok


def inner_loop(spec, code, first_review, seed, stats, critic, log):
    """Returns (consistent_review, first_pass_clean, n_inner, c_verdicts)."""
    review, exchange, cvs = first_review, "", []
    for k in range(1, INNER_CAP + 1):
        c_text = critic(spec, code, review, exchange, seed + 100 * k, k)
        agree = verdict(c_text, "AGREE", "DISAGREE")
        agree = bool(agree)
        cvs.append((k, agree))
        log.append({"role": "C", "k": k, "agree": agree})
        exchange += f"\n### Review {k}\n{review}\n### Critique {k}\n{c_text}\n"
        r_ok = verdict(review, "APPROVE", "NEEDS_CHANGES")
        if agree:
            return review, (k == 1 and r_ok is True), k, cvs
        if k == INNER_CAP:
            break
        review = llm(REVIEW.format(frozen_ask=spec, artifact_code=code, prior_exchange=exchange),
                     seed + 100 * k + 1, stats)
        log.append({"role": "R", "k": k + 1, "approve": verdict(review, "APPROVE", "NEEDS_CHANGES")})
    return review, False, INNER_CAP, cvs


def iterate(spec, v0, r1, seed, stats, tests, cache, critic):
    """Outer loop shared by RO (critic=None) and AR/ARZ. Returns trajectory dict."""
    code, review, log, cvs = v0, r1, [], []
    edits = 0
    while True:
        log.append({"role": "R", "k": 1, "approve": verdict(review, "APPROVE", "NEEDS_CHANGES")})
        if critic is None:
            clean = verdict(review, "APPROVE", "NEEDS_CHANGES") is True
            cons = review
        else:
            cons, clean, _, cv = inner_loop(spec, code, review, seed + 1000 * edits, stats, critic, log)
            cvs += [(edits, k, a) for k, a in cv]
        if clean or edits == E_CAP:
            break
        code = strip_code(llm(EDIT.format(specification=spec, previous_artifact=code,
                                          consistent_review=cons), seed + 1000 * edits + 7, stats))
        edits += 1
        log.append({"role": "M", "edit": edits, "pass": run_tests(code, tests, cache)})
        if edits == E_CAP:
            break
        review = llm(REVIEW.format(frozen_ask=spec, artifact_code=code, prior_exchange=""),
                     seed + 1000 * edits + 11, stats)
    return {"pass": run_tests(code, tests, cache), "edits": edits, "accepted_clean": bool(clean),
            "c_verdicts": cvs, "log": log}


def llm_critic(stats):
    def f(spec, code, review, exchange, seed, k):
        return llm(CRITIC.format(frozen_ask=spec, artifact_code=code, reviewer_latest=review,
                                 prior_exchange=exchange), seed, stats)
    return f


def zi_critic(q1, q2, rng):
    def f(spec, code, review, exchange, seed, k):
        q = q1 if k == 1 else q2
        return ZI_DISAGREE if rng.random() < q else ZI_AGREE
    return f


DONE_AR = []  # (k==1 disagree count, n) and (k>1 ...)


def rates():
    with LOCK:
        d1 = sum(1 for cv in DONE_AR for (_, k, a) in cv if k == 1 and not a)
        n1 = sum(1 for cv in DONE_AR for (_, k, a) in cv if k == 1)
        d2 = sum(1 for cv in DONE_AR for (_, k, a) in cv if k > 1 and not a)
        n2 = sum(1 for cv in DONE_AR for (_, k, a) in cv if k > 1)
    return (d1 + 1) / (n1 + 2), (d2 + 1) / (n2 + 2), n1, n2


def phase1(i, d):
    spec = d["question_content"]
    tests = tests_of(d)
    cache, seed = {}, 1000003 * (i + 1)
    st = {k: {"calls": 0, "in_tok": 0, "out_tok": 0} for k in ("base", "SR", "RO", "AR")}
    v0 = strip_code(llm(WRITE.format(specification=spec, previous_review="(none)"), seed, st["base"]))
    r1 = llm(REVIEW.format(frozen_ask=spec, artifact_code=v0, prior_exchange=""), seed + 1, st["base"])
    zs = run_tests(v0, tests, cache)
    v1 = strip_code(llm(EDIT.format(specification=spec, previous_artifact=v0, consistent_review=r1),
                        seed + 7, st["SR"]))  # SR edits once, always
    sr = run_tests(v1, tests, cache)
    ro = iterate(spec, v0, r1, seed, st["RO"], tests, cache, None)
    ar = iterate(spec, v0, r1, seed, st["AR"], tests, cache, llm_critic(st["AR"]))
    with LOCK:
        DONE_AR.append(ar["c_verdicts"])
    return {"i": i, "id": d["question_id"], "difficulty": d["difficulty"], "n_tests": len(tests),
            "r1_approve": verdict(r1, "APPROVE", "NEEDS_CHANGES"), "ZS": zs, "SR": sr,
            "RO": ro, "AR": ar, "stats": st, "_spec": spec, "_v0": v0, "_r1": r1,
            "_seed": seed, "_tests": tests, "_cache": cache}


def phase2(rec):
    q1, q2, n1, n2 = rates()
    st = {"calls": 0, "in_tok": 0, "out_tok": 0}
    rng = random.Random(rec["_seed"])
    arz = iterate(rec["_spec"], rec["_v0"], rec["_r1"], rec["_seed"], st, rec["_tests"],
                  rec["_cache"], zi_critic(q1, q2, rng))
    arz["q_used"] = [q1, q2, n1, n2]
    rec["ARZ"] = arz
    rec["stats"]["ARZ"] = st
    out = {k: v for k, v in rec.items() if not k.startswith("_")}
    out["v0_len"] = len(rec["_v0"])
    with LOCK:
        with open(OUT, "a") as f:
            f.write(json.dumps(out) + "\n")
    print(time.strftime("%H:%M:%S"), rec["i"], rec["difficulty"], "ZS", rec["ZS"], "SR", rec["SR"],
          "RO", rec["RO"]["pass"], "AR", rec["AR"]["pass"], "ARZ", arz["pass"],
          "q", round(q1, 2), round(q2, 2), flush=True)


def main():
    tasks = load_tasks()
    rng = random.Random(20260916)
    # medium and hard stdin tasks carry the separation in P; easy ones are near ceiling.
    med = [t for t in tasks if t["difficulty"] == "medium"]
    hard = [t for t in tasks if t["difficulty"] == "hard"]
    rng.shuffle(med)
    rng.shuffle(hard)
    pool = med + hard  # medium first: the local model can solve some, so arms can differ
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)["id"] for l in open(OUT)}
    sel = [(i, t) for i, t in enumerate(pool[:N_TASKS]) if t["question_id"] not in done]
    print(len(tasks), "stdin tasks;", len(pool), "medium/hard; running", len(sel), flush=True)
    warm = int(os.environ.get("AR_WARM", "4"))
    ex2 = ThreadPoolExecutor(1)
    with ThreadPoolExecutor(WORKERS) as ex:
        pending, p2 = [], []
        futs = [ex.submit(phase1, i, t) for i, t in sel]
        from concurrent.futures import as_completed
        for fu in as_completed(futs):
            try:
                rec = fu.result()
            except Exception as e:
                print("phase1 error", repr(e), flush=True)
                continue
            pending.append(rec)
            if len(DONE_AR) >= min(warm, len(sel)):
                for r in pending:
                    p2.append(ex2.submit(phase2, r))
                pending = []
        for r in pending:
            p2.append(ex2.submit(phase2, r))
    for fu in p2:
        try:
            fu.result()
        except Exception as e:
            print("phase2 error", repr(e), flush=True)
    ex2.shutdown()

if __name__ == "__main__":
    main()
