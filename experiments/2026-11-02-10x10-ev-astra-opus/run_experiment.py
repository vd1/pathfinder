"""Run fresh EV research, then two blind Opus ratings of every old and new note."""
import copy
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'engine'))
from pathfinder import config, runner, transport


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'operator' / f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def prepare_jobs(root):
    path = root / 'operator/rating-jobs.json'
    if path.exists():
        return json.loads(path.read_text())
    protocol, masking = module('rating_protocol'), module('masking_protocol')
    jobs = []
    pairs = json.loads((root / 'shortlist.json').read_text())['pairs']
    for pair in pairs:
        pid = pair['pair_id']
        for arm in ('old', 'new'):
            folder = root / ('operator/baseline' if arm == 'old' else 'threads') / pid
            state = json.loads((folder / 'status.json').read_text())
            if state['status'] not in ('DRAFT', 'PAUSE', 'PAUSE-ON-ITERATE', 'PAUSE-ON-REVISE'):
                raise RuntimeError(f'Nonterminal research: {arm} {pid}')
            note = (folder / f'{pid}.tex').read_text()
            masked, count = masking.mask_ratings(note)
            prompt = protocol.note_prompt(masked, 'mechanisms-agents')
            for repeat in (1, 2):
                key = digest(f'{arm}/{pid}/{repeat}')[:20]
                prompt_path = root / 'operator/rating-prompts' / f'{key}.prompt'
                prompt_path.parent.mkdir(parents=True, exist_ok=True)
                prompt_path.write_text(prompt)
                jobs.append(dict(id=key, arm=arm, pair_id=pid, repeat=repeat,
                                 prompt=str(prompt_path.relative_to(root)),
                                 prompt_sha256=digest(prompt), note_sha256=digest(note), masked=count))
    random.Random(20261102).shuffle(jobs)
    path.write_text(json.dumps(jobs, indent=2) + '\n')
    return jobs


def rate(root, campaign):
    jobs = prepare_jobs(root)
    out = root / 'operator/note-ratings.jsonl'
    rows = [json.loads(line) for line in out.read_text().splitlines()] if out.exists() else []
    done = {row['id'] for row in rows}
    c = copy.copy(campaign)
    c.raw = {**c.raw, 'routes': {}, 'claude': {}}
    c.backend = 'stub' if campaign.backend == 'stub' else 'claude'
    for job in jobs:
        if job['id'] in done:
            continue
        prompt = (root / job['prompt']).read_text()
        if digest(prompt) != job['prompt_sha256']:
            raise RuntimeError('Rating prompt changed')
        cwd = root / 'operator/rating-work' / job['id']
        cwd.mkdir(parents=True, exist_ok=True)
        request = transport.ModelRequest(identity=job['id'], prompt=prompt, model='claude-opus-5-5',
            tools=False, search=False, timeout=1800, thread=job['id'], stage='rating', actor='blind-rater', cwd=cwd)
        result = transport.execute(c, request)
        if result.get('transport_failed') or result.get('outcome') != 'completed':
            raise RuntimeError(f"Rating failed: {job['id']}: {result.get('failure') or result.get('error')}")
        text = result.get('text', '').strip()
        if text.startswith('```'):
            text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
        rating = json.loads(text)
        score = rating.get('score')
        if (type(score) not in (int, float) or not 1 <= score <= 10
                or rating.get('level') not in ('note', 'journal', 'strong')
                or rating.get('nonobvious') not in ('no', 'somewhat', 'yes')
                or not all(isinstance(rating.get(k), str) and rating[k] for k in ('reason', 'strongest_result'))):
            raise RuntimeError(f"Invalid rating: {job['id']}")
        row = {**job, **rating, 'model': request.model, 'domain': 'mechanisms-agents'}
        with out.open('a') as stream:
            stream.write(json.dumps(row) + '\n')
        rows.append(row)
        print(f"Rated {job['id']}: {score}/10", flush=True)
    report(root, rows)


def report(root, rows):
    baseline = json.loads((root / 'operator/baseline.json').read_text())
    table = []
    for item in baseline:
        pid = item['pair_id']
        scores = {arm: [r['score'] for r in rows if r['pair_id'] == pid and r['arm'] == arm]
                  for arm in ('old', 'new')}
        if any(len(values) != 2 for values in scores.values()):
            raise RuntimeError(f'Incomplete ratings for {pid}')
        old, new = (sum(scores[arm]) / 2 for arm in ('old', 'new'))
        table.append(dict(pair_id=pid, historical_paper_mean=item['historical_paper_mean'],
                          old_note_mean=old, new_note_mean=new, delta=new-old))
    with (root / 'operator/comparison.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]))
        writer.writeheader(); writer.writerows(table)
    summary = dict(n_pairs=len(table), old_mean=sum(r['old_note_mean'] for r in table)/len(table),
                   new_mean=sum(r['new_note_mean'] for r in table)/len(table),
                   mean_delta=sum(r['delta'] for r in table)/len(table),
                   improved=sum(r['delta'] > 0 for r in table), tied=sum(r['delta'] == 0 for r in table),
                   declined=sum(r['delta'] < 0 for r in table))
    (root / 'operator/comparison.json').write_text(json.dumps(summary, indent=2) + '\n')


def main():
    os.environ.setdefault('PATHFINDER_CODEX', str(ROOT.parents[2] / 'nobel/pilot-question/runtime-codex-0.163.0-bazel/bin/codex'))
    c = config.load(ROOT)
    acceptance = None
    if sys.argv[1:] == ['--accept-seat-change']:
        previous = json.loads((ROOT / 'run.json').read_text())['config']['raw']
        if previous != {**c.raw, 'seats': 2} or c.seats != 4:
            raise RuntimeError('Seat-change restart permits only seats 2 -> 4')
        acceptance = 'User-authorized concurrency increase from 2 to 4 after graceful drain'
    elif sys.argv[1:]:
        raise RuntimeError('Unknown experiment-driver arguments')
    record = ROOT / 'operator/experiment-status.json'
    try:
        record.write_text(json.dumps({'status': 'research', 'pid': os.getpid()}))
        if runner.run(c, research_only=True, accept_change=acceptance) != 0:
            raise RuntimeError('Research stopped; inspect campaign health and receipts before resuming')
        if (ROOT / 'stop.json').exists():
            record.write_text(json.dumps({'status': 'stopped', 'pid': os.getpid(), 'reason': 'graceful drain'}))
            return
        record.write_text(json.dumps({'status': 'rating', 'pid': os.getpid()}))
        rate(ROOT, c)
        record.write_text(json.dumps({'status': 'complete', 'pid': os.getpid()}))
    except Exception as error:
        record.write_text(json.dumps({'status': 'stopped', 'pid': os.getpid(), 'error': str(error)}))
        raise


if __name__ == '__main__':
    main()
