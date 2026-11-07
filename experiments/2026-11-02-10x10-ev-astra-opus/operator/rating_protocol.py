"""Rate the significance of accepted research papers, as a referee would, from the paper alone.

Acceptance says a paper is correct, fairly attributed and cites its closest prior work; it says nothing about how much
the paper matters. Each call reads only the LaTeX of the paper (campaign/threads/<pair>/paper/paper.tex), with no tools
and no information on how it was produced, and returns the strongest result, whether an expert would find it
non-obvious, the venue level it fits and a score from 1 to 10. Each paper is rated twice, independently, to see how
stable the rating is.

Usage (from the repo root):
  python3 -I scripts/paper_significance.py [--threads DIR] [--note] OUT.jsonl PAIR ...   # DIR default campaign/threads
--note rates the thread's final research note (<pair>.tex) instead of its paper, so that a pair without an accepted
paper (PAUSE) is rated on the same terms as one with a paper. The note is rated alone: no part of the verifier's
verdict, masked or not, goes into the prompt.
--domain KEY swaps the referee's field and venue examples in the rubric (default quantum); see DOMAINS.
Results: one line per (pair, repeat) in OUT.jsonl; rows already in OUT are skipped.
"""
import hashlib
import json
import re
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MODEL, WORKERS, REPEATS = "claude-opus-5-5", 4, 2

# The rubric names the referee's field and example venues; the rest of it is domain-neutral.
DOMAINS = {
    "quantum": ("quantum algorithms and quantum information theory", "Quantum, TQC, PRA",
                "STOC, FOCS, QIP plenary, PRX Quantum, Nature Physics"),
    "mechanisms-agents": ("mechanism design, algorithmic game theory and multi-agent learning",
                          "Games and Economic Behavior, AAMAS, JAIR, Autonomous Agents and Multi-Agent Systems",
                          "EC, STOC, FOCS, Econometrica, NeurIPS or ICML oral"),
}


def localise(text, domain):
    f, j, t = DOMAINS[domain]
    return (text.replace("quantum algorithms and quantum information theory", f)
                .replace("Quantum, TQC, PRA", j).replace("STOC, FOCS, QIP plenary, PRX Quantum, Nature Physics", t))

PROMPT = """You are an expert referee in quantum algorithms and quantum information theory. Below is the full LaTeX
source of a paper that has already been checked for correctness and for fair attribution of prior work. Do not
re-check those. Judge only how significant its contribution is, as an expert in the area would, using the paper's
own account of prior work and your knowledge of the field. Who wrote it does not matter.

Return only one JSON object, no prose and no code fence:
{{"strongest_result": "the paper's strongest new result, in one sentence",
  "nonobvious": "no" | "somewhat" | "yes",
  "level": "note" | "journal" | "strong",
  "score": 1 to 10,
  "reason": "two or three sentences: what makes the contribution matter or not"}}

nonobvious: would an expert who knows the cited prior work have found the strongest result quickly?
"no" means quickly, "somewhat" means with real work, "yes" means it needs an idea they would not readily have had.
level: "note" = a workshop paper, short note or arXiv-only preprint; "journal" = a solid paper in a good specialist
journal or conference (for example Quantum, TQC, PRA); "strong" = a top venue (for example STOC, FOCS, QIP plenary,
PRX Quantum, Nature Physics).
score: 1 to 10, where 5 is a typical solid specialist-journal paper.

PAPER:
{paper}
"""

# A note is rated from the note alone. Until 27 October 2026 (Pilot 6 to the production campaign) the verifier's last
# assessment was appended with its number masked; its text still endorsed the work ("supports entry to paper review",
# which the verifier rubric ties to a score of 5 or more) and raised Astra's note scores by about 0.85 points
# (data/cross_rate/REPORT.md). NOTE_PREFACE_WITH_VERIFIER is kept only so that those recorded runs reproduce.
NOTE_PREFACE = """You are an expert referee in quantum algorithms and quantum information theory. Below is the full
LaTeX source of a research note written by two researchers at the end of their work. It is not a polished paper and
its results have not all been accepted. Judge how
significant the strongest result the note supports would be as a contribution, as an expert in the area would,
using the note's own account of prior work and your knowledge of the field. Ignore presentation. Who wrote it does
not matter.
"""

NOTE_PREFACE_WITH_VERIFIER = """You are an expert referee in quantum algorithms and quantum information theory. Below is the full
LaTeX source of a research note written by two researchers at the end of their work. It is not a polished paper and
its results have not all been accepted; a verifier's assessment follows the note when there is one. Judge how
significant the strongest result the note supports would be as a contribution, as an expert in the area would,
using the note's own account of prior work and your knowledge of the field. Ignore presentation. Who wrote it does
not matter.
"""


def note_prompt(note_tex, domain="quantum"):
    """The rating prompt for a research note: the note alone, with no part of the verifier's verdict."""
    prompt_t = localise(PROMPT, domain)
    return (localise(NOTE_PREFACE, domain) + prompt_t[prompt_t.index("\nReturn only"):].replace("PAPER:", "NOTE:")
            ).format(paper=note_tex)


def call(prompt):
    call_id = f"claude-significance-{uuid.uuid4().hex}"
    log_dir = Path("doc/logs/claude_outputs")
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["claude", "-p", "--model", MODEL, "--tools", "", "--no-session-persistence", "--output-format", "json"]
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=1800, cwd="/tmp")
    (log_dir / f"{call_id}.txt").write_text(r.stdout + ("\nSTDERR:\n" + r.stderr if r.stderr else ""))
    with open("doc/logs/claude_calls.jsonl", "a") as f:
        f.write(json.dumps({"call_id": call_id, "phase": "paper-significance", "owner": "claude",
                            "purpose": "rate paper significance", "status": "completed" if r.returncode == 0 else "failed",
                            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    reply = json.loads(r.stdout)
    m = re.search(r"\{.*\}", reply.get("result") or "", flags=re.S)
    d = json.loads(m.group(0)) if m else {}
    if d.get("level") not in ("note", "journal", "strong") or not isinstance(d.get("score"), (int, float)):
        raise RuntimeError(f"unparsable reply, see {call_id}")
    return d, reply.get("total_cost_usd", 0)


def main():
    args = sys.argv[1:]
    domain = "quantum"
    if args[:1] == ["--domain"]:
        domain, args = args[1], args[2:]
    prompt_t = localise(PROMPT, domain)
    threads = Path("campaign/threads")
    if args[:1] == ["--threads"]:                 # another campaign's threads, e.g. an arm of the question pilot
        threads, args = Path(args[1]), args[2:]
    note = args[:1] == ["--note"]
    if note:
        args = args[1:]
    out, wanted = Path(args[0]), args[1:]
    done = {(json.loads(l)["pair_id"], json.loads(l)["repeat"]) for l in out.open()} if out.exists() else set()
    jobs = [(p, k) for p in dict.fromkeys(wanted) for k in range(1, REPEATS + 1) if (p, k) not in done]

    def run(job):
        pid, k = job
        if note:
            tex = (threads / pid / f"{pid}.tex").read_text(errors="replace")   # the note alone, no verdict
            d, cost = call(note_prompt(tex, domain))
        else:
            tex = (threads / pid / "paper/paper.tex").read_text(errors="replace")
            d, cost = call(prompt_t.format(paper=tex))
        with open(out, "a") as f:
            f.write(json.dumps({"pair_id": pid, "repeat": k, **d, "cost": cost, "model": MODEL,
                                "domain": domain,
                                "paper_sha256": hashlib.sha256(tex.encode()).hexdigest()}, ensure_ascii=False) + "\n")
        print(f"{pid} #{k}: {d['level']} {d['score']} nonobvious={d.get('nonobvious')}", flush=True)

    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(run, jobs))


if __name__ == "__main__":
    main()
