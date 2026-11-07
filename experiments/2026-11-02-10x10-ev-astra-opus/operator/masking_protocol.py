"""Editorial gate: blind Astra-medium rating of each final DRAFT research note; 6 or more makes it an editorial candidate.

Protocol: nobel's corrected note rating (nobel scripts/paper_significance.note_prompt, commit 63bde83, 27 October
2026): the note alone, with no part of the verifier's verdict, no score history and no catalogue label; Astra-medium
(gpt-6-astra) through the Codex CLI with no tools, one reading per note (Astra repeats are nearly deterministic,
nobel data/cross_rate/REPORT.md). The verifier's own score stays the research-stage signal; this rating decides
which DRAFT notes go to the editorial (paper) stage.

Usage (from the repo root):
  python3 -I scripts/note_rating_gate.py prepare          # freeze jobs for every DRAFT note; no model calls
  python3 -I scripts/note_rating_gate.py run [--workers N] # rate frozen jobs not yet rated (model calls)
  python3 -I scripts/note_rating_gate.py report           # gate table from the ratings
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOBEL = Path('/Users/v/Code_2026/nobel')
NOBEL_SCRIPT = NOBEL / 'scripts/paper_significance.py'
NOBEL_COMMIT = '63bde834e404c340f62a25771383d1c7b88ba55e'
OUT = REPO / 'operator-log/note-rating-gate'
MODEL, EFFORT, THRESHOLD = 'gpt-6-astra', 'medium', 6
FINAL = ('DRAFT',)


RATING_CONTEXT = re.compile(r'score|scores|ITERATE|REVISE|DRAFT|PAUSE|[Vv]erifier|[Rr]eview|assess')
RATING = re.compile(r'(?<![\d.])(10|[1-9])\s*/\s*10(?![\d.])')
OPERATOR = re.compile(r'(\\leq?|\\geq?|\\cdot|\\times|[<>=^+\-*/{|]|\\frac\{?)\s*\$?\s*$')


def mask_ratings(text):
    """Replace the verifier's numerical ratings quoted in a note; returns the masked text and the count."""
    spans = []
    for m in RATING.finditer(text):
        before = text[max(0, m.start() - 200):m.start()]
        if OPERATOR.search(before[-12:].replace('\\(', '').replace('$', '')):
            continue
        if RATING_CONTEXT.search(before) or re.match(r'\s*\$?\\?\)?\s*\\ledger', text[m.end():m.end() + 12]):
            spans.append(m.span())
    for a, b in reversed(spans):
        text = text[:a] + '[rating withheld]' + text[b:]
    text, lists = re.subn(r'(scores?)(\s+)\d{1,2}(?:\s*,\s*\d{1,2})+', r'\1\2[ratings withheld]', text)
    return text, len(spans) + lists


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def nobel_prompt_module():
    """Load nobel's rating module from the pinned commit, so later nobel edits cannot change the protocol."""
    source = subprocess.run(['git', '-C', str(NOBEL), 'show', f'{NOBEL_COMMIT}:scripts/paper_significance.py'],
                            capture_output=True, text=True, check=True).stdout
    path = OUT / 'protocol/paper_significance.py'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != source:
        path.write_text(source)
    spec = importlib.util.spec_from_file_location('paper_significance', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, sha(source)


def final_notes():
    for status in sorted(REPO.glob('pilots/atlas-pilot-*/runs/pair-*/threads/Q001-P002/status.json'),
                         key=lambda p: (int(p.parts[-6].rsplit('-', 1)[1]), int(p.parts[-4].rsplit('-', 1)[1]))):
        state = json.loads(status.read_text())
        if state['status'] not in FINAL:
            continue
        root = status.parents[2]
        unit = json.loads((root / 'state.json').read_text())['units'][0]
        yield {'id': f"{status.parts[-6].removeprefix('atlas-')}-{status.parts[-4]}",
               'cards': [unit['q']['id'], unit['p']['id']],
               'note': str((status.parent / 'Q001-P002.tex').relative_to(REPO))}


def prepare():
    ps, module_sha = nobel_prompt_module()
    jobs_path = OUT / 'jobs.jsonl'
    done = {json.loads(l)['id'] for l in jobs_path.open()} if jobs_path.exists() else set()
    added = 0
    with jobs_path.open('a') as f:
        for job in final_notes():
            if job['id'] in done:
                continue
            note = (REPO / job['note']).read_text(errors='replace')
            masked, count = mask_ratings(note)
            prompt = ps.note_prompt(masked)
            job.update(note_sha256=sha(note), ratings_masked=count, prompt_sha256=sha(prompt), model=MODEL, reasoning_effort=EFFORT,
                       protocol={'nobel_commit': NOBEL_COMMIT, 'module_sha256': module_sha,
                                 'function': 'note_prompt', 'domain': 'quantum'},
                       prepared_utc=datetime.now(timezone.utc).isoformat(timespec='seconds'))
            f.write(json.dumps(job) + '\n')
            added += 1
    print(f'{added} new DRAFT notes frozen; {len(done) + added} jobs in {jobs_path.relative_to(REPO)}; no model calls.')


def call_astra(prompt):
    """Same invocation as nobel scripts/rater_test.call_astra: ephemeral, no user config, read-only, no shell."""
    with tempfile.TemporaryDirectory() as cwd:
        cmd = ['codex', 'exec', '--json', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check',
               '--cd', cwd, '--model', MODEL, '-c', 'approval_policy="never"', '--sandbox', 'read-only',
               '-c', f'model_reasoning_effort="{EFFORT}"', '-c', 'features.shell_tool=false', '-']
        env = {k: v for k, v in os.environ.items()
               if not k.startswith('HERDR_') and k not in {'CODEX_THREAD_ID', 'CODEX_SESSION_ID'}}
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=1800, cwd=cwd, env=env)
    text, usage = '', {}
    for line in r.stdout.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get('type') == 'item.completed' and (row.get('item') or {}).get('type') == 'agent_message':
            text = row['item'].get('text', '')
        elif row.get('type') == 'turn.completed':
            usage = row.get('usage') or {}
    m = re.search(r'\{.*\}', text, flags=re.S)
    d = json.loads(m.group(0)) if m else {}
    if d.get('level') not in ('note', 'journal', 'strong') or not isinstance(d.get('score'), (int, float)):
        raise RuntimeError(f'unparsable Astra reply: {text[:300]!r} {r.stderr[-300:]!r}')
    return d, usage


def run(workers):
    ps, module_sha = nobel_prompt_module()
    jobs = [json.loads(l) for l in (OUT / 'jobs.jsonl').open()]
    out = OUT / 'ratings.jsonl'
    rated = {json.loads(l)['id'] for l in out.open()} if out.exists() else set()

    def one(job):
        note = (REPO / job['note']).read_text(errors='replace')
        prompt = ps.note_prompt(mask_ratings(note)[0])
        assert sha(note) == job['note_sha256'] and sha(prompt) == job['prompt_sha256'], f"input changed: {job['id']}"
        assert module_sha == job['protocol']['module_sha256']
        d, usage = call_astra(prompt)
        row = {'id': job['id'], 'cards': job['cards'], **d, 'gate': d['score'] >= THRESHOLD, 'usage': usage,
               'model': MODEL, 'reasoning_effort': EFFORT, 'prompt_sha256': job['prompt_sha256'],
               'at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
        with out.open('a') as f:
            f.write(json.dumps(row) + '\n')
        print(f"{job['id']} {'+'.join(job['cards'])}: {d['level']} {d['score']}", flush=True)

    todo = [j for j in jobs if j['id'] not in rated]
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(one, todo))


def report():
    rows = [json.loads(l) for l in (OUT / 'ratings.jsonl').open()]
    for r in sorted(rows, key=lambda r: -r['score']):
        print(f"{r['id']:22} {'+'.join(r['cards']):8} {r['score']:>4} {r['level']:8} {'EDITORIAL' if r['gate'] else ''}")
    print(f"{sum(r['gate'] for r in rows)} of {len(rows)} notes at {THRESHOLD} or above")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('prepare', 'run', 'report'))
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    {'prepare': prepare, 'run': lambda: run(args.workers), 'report': report}[args.command]()
