"""Run an isolated, metered reassessment without changing historical outputs."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from datetime import datetime, timezone

from usage_probe import snapshot

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
THREAD = ROOT / 'threads' / 'Q4P6'


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def hashes():
    paths = [REPO / name for name in
             ('campaign.json', 'receipts.jsonl', 'shortlist.json', 'scan.jsonl')]
    for directory in (REPO / 'threads' / 'Q4P6',
                      REPO / 'experiments' / '2026-09-13-astra-medium-accepted2'
                      / 'threads' / 'Q4P6'):
        paths.extend(path for path in directory.rglob('*') if path.is_file())
    return {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def run():
    THREAD.mkdir(parents=True, exist_ok=False)
    inputs = THREAD / 'inputs'
    shutil.copytree(REPO / 'threads' / 'Q4P6' / 'inputs', inputs)
    for original, target in (('paper.tex', 'r.tex'),
                             ('references.bib', 'r-references.bib')):
        shutil.copy2(REPO / 'threads' / 'Q4P6' / 'paper' / original, inputs / target)
    for path in inputs.iterdir():
        if path.is_file():
            path.chmod(0o444)
    before_hashes = hashes()
    write_json(ROOT / 'original-hashes-before.json', before_hashes)
    before = snapshot()
    if before['account']['type'] != 'chatgpt':
        raise RuntimeError('ChatGPT subscription authentication required.')
    write_json(ROOT / 'usage-before.json', before)
    write_json(ROOT / 'manifest.json', {
        'started_at': datetime.now(timezone.utc).isoformat(),
        'pair': 'Q4P6', 'model': 'gpt-6-astra', 'reasoning_effort': 'medium',
        'scope': 'Independent targeted review of original paper r against Q and P.',
        'auth': 'ChatGPT subscription', 'service_tier_override': None,
        'historical_verdicts_given_to_reviewer': False,
        'timeout_seconds': 1200,
        'quota_caveat': 'Rounded account-wide readings include concurrent activity.'})
    env = {key: value for key, value in os.environ.items()
           if not ('API_KEY' in key or key.startswith(
               ('OPENAI_', 'ANTHROPIC_API', 'ELM_')))}
    command = [sys.executable, str(ROOT / 'codex_meter.py'), 'exec', '--json',
               '--ephemeral', '--ignore-user-config', '--skip-git-repo-check',
               '--cd', str(THREAD), '--model', 'gpt-6-astra',
               '-c', 'approval_policy="never"', '--sandbox', 'workspace-write',
               '-c', 'web_search="live"', '-']
    outcome = {'exit_code': None, 'timed_out': False}
    try:
        with (ROOT / 'REVIEW_REQUEST.md').open() as prompt, \
                (ROOT / 'reviewer.events.jsonl').open('x') as events, \
                (ROOT / 'reviewer.stderr').open('x') as errors:
            proc = subprocess.Popen(command, stdin=prompt, stdout=events,
                                    stderr=errors, env=env, start_new_session=True)
            try:
                outcome['exit_code'] = proc.wait(timeout=1200)
            except subprocess.TimeoutExpired:
                outcome['timed_out'] = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    outcome['exit_code'] = proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    outcome['exit_code'] = proc.wait()
    finally:
        after_hashes = hashes()
        changed = [name for name in before_hashes.keys() | after_hashes.keys()
                   if before_hashes.get(name) != after_hashes.get(name)]
        write_json(ROOT / 'originals-verification.json', {
            'unchanged': not changed, 'changed_paths': sorted(changed),
            'files_checked': len(before_hashes)})
        try:
            write_json(ROOT / 'usage-after.json', snapshot())
        except Exception as exc:
            write_json(ROOT / 'usage-after-error.json', {'error': str(exc)})
        outcome['finished_at'] = datetime.now(timezone.utc).isoformat()
        write_json(ROOT / 'run-outcome.json', outcome)
        print(json.dumps(outcome), flush=True)


if __name__ == '__main__':
    run()
