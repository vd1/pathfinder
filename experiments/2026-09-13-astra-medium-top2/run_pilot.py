"""Run two fresh research threads with isolated inputs, engine, and telemetry."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
from datetime import datetime, timezone
from usage_probe import snapshot

PILOT = Path(__file__).resolve().parent
REPO = PILOT.parents[1]
PAIRS = ['Q4P10', 'Q3P9']


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def hashes():
    paths = [REPO / n for n in ('campaign.json', 'receipts.jsonl', 'shortlist.json', 'scan.jsonl')]
    paths.extend(p for pair in PAIRS for p in (REPO / 'threads' / pair).rglob('*') if p.is_file())
    return {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def prepare():
    if (PILOT / 'campaign.json').exists():
        raise SystemExit('Pilot already prepared; refusing to overwrite or silently rerun.')
    before_hashes = hashes()
    write_json(PILOT / 'original-hashes-before.json', before_hashes)
    (PILOT / 'engine').mkdir()
    shutil.copytree(REPO / 'pathfinder', PILOT / 'engine' / 'pathfinder',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(REPO / 'prompts', PILOT / 'prompts')
    for name in ('Q.jsonl', 'P.jsonl', 'scan.jsonl'):
        shutil.copy2(REPO / name, PILOT / name)
    selection = json.loads((REPO / 'shortlist.json').read_text())
    assert [p['pair_id'] for p in selection['pairs'][:2]] == PAIRS
    selection.update(pairs=selection['pairs'][:2], n_selected=2)
    write_json(PILOT / 'shortlist.json', selection)
    corpora = {side: [json.loads(line) for line in (PILOT / f'{side}.jsonl').read_text().splitlines() if line.strip()]
               for side in ('Q', 'P')}
    for pair in PAIRS:
        qi, pi = (int(part) for part in pair[1:].split('P'))
        for side, idx in (('Q', qi), ('P', pi)):
            row = corpora[side][idx - 1]
            src = REPO / row['text']
            target = PILOT / row['text']
            if not target.resolve().is_relative_to(PILOT):
                raise RuntimeError(f'Source path leaves pilot: {target}')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
    cfg = json.loads((REPO / 'campaign.json').read_text())
    cfg.update(backend='codex', model='gpt-6-astra', scan_model='gpt-6-astra',
               peers=['ada', 'emmy'], seats=2, codex={}, prices={})
    write_json(PILOT / 'campaign.json', cfg)
    write_json(PILOT / 'manifest.json', {
        'created_at': datetime.now(timezone.utc).isoformat(), 'pairs': PAIRS,
        'model': 'gpt-6-astra', 'reasoning_effort': 'medium', 'auth': 'ChatGPT subscription',
        'user_reported_weekly_remaining_percent': 99,
        'scope': 'Fresh research and terminal readable notes; no scan or paper authoring.',
        'comparison': 'Existing corresponding research outputs, accessed only after the pilot for assessment.',
        'engine': 'Snapshot of repository package; original files unchanged.',
        'prompts': 'Exact copies of repository prompts.',
        'billing': 'Subscription use; receipt dollar values are unpriced placeholders, not measured costs.',
        'quota_caveat': 'Account deltas include concurrent Codex activity, including the supervising conversation.',
        'config': cfg})
    return before_hashes


def run():
    before_hashes = prepare()
    before = snapshot()
    if before['account']['type'] != 'chatgpt':
        raise RuntimeError('ChatGPT authentication is required.')
    models = before['astra_models']
    if not models or not any(e['reasoningEffort'] == 'medium' for e in models[0]['supportedReasoningEfforts']):
        raise RuntimeError('Astra medium is not available on this account.')
    write_json(PILOT / 'usage-before.json', before)
    print(json.dumps({'event': 'pilot_start', 'root': str(PILOT), 'pairs': PAIRS,
                      'limits': before['limits']['rateLimits']}), flush=True)
    engine = str(PILOT / 'engine')
    sys.path.insert(0, engine)
    os.environ['PYTHONPATH'] = engine
    os.environ['PYTHONUNBUFFERED'] = '1'
    os.environ['PATHFINDER_CODEX'] = shlex.join([sys.executable, str(PILOT / 'codex_meter.py')])
    from pathfinder import config, runner, research, edit
    campaign = config.load(PILOT)
    try:
        runner.run(campaign)
    finally:
        after_hashes = hashes()
        changed = [p for p in before_hashes.keys() | after_hashes.keys()
                   if before_hashes.get(p) != after_hashes.get(p)]
        write_json(PILOT / 'originals-verification.json', {'unchanged': not changed, 'changed_paths': changed,
                                                         'files_checked': len(before_hashes)})
        try:
            write_json(PILOT / 'usage-after.json', snapshot())
        except Exception as exc:
            write_json(PILOT / 'usage-after-error.json', {'error': str(exc)})
        outcomes = {pair: {'research': research.status(campaign, pair), 'editor': edit.status(campaign, pair)}
                    for pair in PAIRS}
        write_json(PILOT / 'outcomes.json', outcomes)
        print(json.dumps({'event': 'pilot_finished', 'outcomes': outcomes, 'originals_unchanged': not changed}), flush=True)


if __name__ == '__main__':
    run()
