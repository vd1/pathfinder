"""Correct a separate Q4P6 copy and run the isolated Q7P1 paper cycle."""

import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from usage_probe import snapshot

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
BASE = REPO / 'experiments' / '2026-09-13-astra-medium-accepted2'


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def hashes():
    paths = [REPO / name for name in
             ('campaign.json', 'receipts.jsonl', 'shortlist.json', 'scan.jsonl')]
    for directory in (REPO / 'threads' / 'Q4P6', REPO / 'threads' / 'Q7P1',
                      BASE / 'threads' / 'Q7P1'):
        paths.extend(path for path in directory.rglob('*') if path.is_file())
    return {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def correct_q4():
    directory = ROOT / 'threads' / 'Q4P6' / 'paper'
    directory.mkdir(parents=True)
    original = REPO / 'threads' / 'Q4P6' / 'paper'
    text = (original / 'paper.tex').read_text()
    replacements = [
        (
            "P proves convergence to a stable comparator preference when comparisons share a Bradley--Terry latent vector and the comparison graph is connected.  Its interpretation in terms of true contribution or Shapley value assumes the required equality rather than recovering it from heterogeneous views.",
            "P states convergence to a stable comparator preference under a Bradley--Terry model.  Its appendix additionally invokes uniform pair sampling and a local-curvature approximation; graph connectedness alone does not ensure a finite unregularised maximum-likelihood estimator or the claimed statistical rate.  We do not rely on that rate: the theorem below uses observable population probabilities and direct logit inversion.  P's interpretation in terms of true contribution or Shapley value assumes the required equality rather than recovering it from heterogeneous views."
        ),
        (
            "In particular, neither a single co-labelled realisation nor connected observer links without a calibrating triangle and edge coverage suffice.",
            "A single co-labelled realisation does not supply the population moments used here, and observer-graph connectivity alone does not guarantee calibration.  The triangle is a convenient sufficient condition, not a necessary one: more general odd-cycle designs can also calibrate positive reliabilities \\cite{ma2017crowdsourcing,ma2019gradient}.  Likewise, covering every edge is a convenient sufficient condition; calibrated coverage of a connected spanning subgraph would suffice to identify the score vector.  We retain the stronger coverage assumptions below."
        ),
        (
            "Finally, no experiment in the source material tests the moment restrictions.",
            "Finally, no experiment in the source material tests this interface's observer-moment restrictions.  P reports comparator cycle, held-out likelihood and accuracy diagnostics, but these do not test the shared-draw observer model assumed here."
        ),
        (
            "The resulting cross-peer moments can then be tested for edge invariance and rank-one factorisation.  Failure would reject this interface and point towards anchors or correlated or asymmetric observation models.",
            "The resulting cross-peer moments can then be tested for edge invariance and compatibility with the off-diagonal products \\(q_{rs}=a_ra_s\\), allowing for sampling error.  Passing these necessary observable checks would not establish a shared latent draw, conditional independence, truthful reporting, or the interpretation as contribution.  An admissible positive triangle fixes its reliability parameters without redundant equality restrictions, so additional overlaps or edge-stratified populations are needed for overidentification checks.  Evidence against the restrictions would reject this proposed interface for the sampled setting and point towards anchors or correlated or asymmetric observation models."
        ),
    ]
    for old, new in replacements:
        if text.count(old) != 1:
            raise RuntimeError('Expected Q4P6 correction anchor is absent or ambiguous.')
        text = text.replace(old, new, 1)
    text = ('% Separate exposition-corrected copy, 2026-09-13; original accepted paper unchanged.\n'
            + text)
    (directory / 'paper.tex').write_text(text)
    shutil.copy2(original / 'references.bib', directory / 'references.bib')
    write_json(directory / 'corrections.json', {
        'source': str(original / 'paper.tex'),
        'source_sha256': hashlib.sha256((original / 'paper.tex').read_bytes()).hexdigest(),
        'review': 'experiments/2026-09-13-astra-medium-Q4P6-reassessment/threads/Q4P6/review.md',
        'scope': ['Qualify P convergence attribution',
                  'Distinguish sufficient from necessary graph coverage',
                  'Clarify observer-moment diagnostics and their limits'],
        'central_theorem_changed': False,
        'status': 'Corrected copy; not a new automated acceptance.'})
    return directory


def run():
    if (ROOT / 'manifest.json').exists():
        raise SystemExit('Refusing to overwrite an existing follow-up run.')
    before_hashes = hashes()
    write_json(ROOT / 'original-hashes-before.json', before_hashes)
    write_json(ROOT / 'manifest.json', {
        'started_at': datetime.now(timezone.utc).isoformat(),
        'model': 'gpt-6-astra', 'reasoning_effort': 'medium',
        'auth': 'ChatGPT subscription', 'service_tier_override': None,
        'scope': 'Separate corrected Q4P6 copy; author/reviewer cycle on Astra Q7P1 DRAFT.',
        'paper_rounds': 3,
        'quota_caveat': 'Rounded account-wide readings include concurrent activity.'})
    shutil.copytree(BASE / 'engine', ROOT / 'engine',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(BASE / 'prompts', ROOT / 'prompts')
    for name in ('Q.jsonl', 'P.jsonl', 'shortlist.json'):
        shutil.copy2(BASE / name, ROOT / name)
    config_data = json.loads((BASE / 'campaign.json').read_text())
    config_data.update(paper_rounds=3, prices={}, codex={})
    write_json(ROOT / 'campaign.json', config_data)
    shutil.copytree(BASE / 'threads' / 'Q7P1', ROOT / 'threads' / 'Q7P1',
                    ignore=shutil.ignore_patterns('paper', 'lock', 'ledger.lock',
                                                  '__pycache__', '*.pyc'))
    author = ROOT / 'prompts' / 'author.md'
    with author.open('a') as stream:
        stream.write('\nIsolation: work only in this copied thread. Do not change inputs, the ledger, '
                     'research notes or files outside it. Preserve the supported scope.\n'
                     'Before finishing, run /Users/v/.local/bin/style-ban-artifacts on paper/paper.tex '
                     'and paper/search.md, and /Users/v/.codex/skills/style-gates/scripts/style_gate.py '
                     'on those files and paper/paper.pdf. Correct artifact errors.\n')
    for key in list(os.environ):
        if 'API_KEY' in key or key.startswith(('OPENAI_', 'ANTHROPIC_API', 'ELM_')):
            os.environ.pop(key)
    sys.path.insert(0, str(ROOT / 'engine'))
    os.environ['PYTHONPATH'] = str(ROOT / 'engine')
    os.environ['PATHFINDER_CODEX'] = shlex.join([sys.executable, str(ROOT / 'codex_meter.py')])
    from pathfinder import config, paper
    outcome = {}
    try:
        q4 = correct_q4()
        ok, log = paper.build(q4)
        outcome['Q4P6'] = {'build_ok': ok, 'build_messages': log}
        if not ok:
            raise RuntimeError('Corrected Q4P6 paper did not compile.')
        for command in (
            ['/Users/v/.local/bin/style-ban-artifacts', str(q4 / 'paper.tex')],
            ['/Users/v/.codex/skills/style-gates/scripts/style_gate.py',
             str(q4 / 'paper.tex'), str(q4 / 'paper.pdf')],
        ):
            result = subprocess.run(command, capture_output=True, text=True)
            print(result.stdout + result.stderr, flush=True)
            if result.returncode:
                raise RuntimeError('Corrected Q4P6 artifact gate failed.')
        before = snapshot()
        if before['account']['type'] != 'chatgpt':
            raise RuntimeError('ChatGPT subscription authentication required.')
        write_json(ROOT / 'usage-before.json', before)
        print('Q4P6 corrected copy built; starting Q7P1 paper cycle.', flush=True)
        campaign = config.load(ROOT)
        outcome['Q7P1'] = {'result': paper.run(campaign, 'Q7P1'),
                           'paper': paper.status(campaign, 'Q7P1')}
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
        write_json(ROOT / 'outcomes.json', outcome)
        print(json.dumps(outcome), flush=True)


if __name__ == '__main__':
    run()
