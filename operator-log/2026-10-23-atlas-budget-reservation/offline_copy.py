"""Read live records, run only stub calls in an isolated copy, save audit results."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from pathfinder import config, coordinator, budget_group, budget_reservation as br, transport, runner

SOURCE = Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-3')
OUT = Path(__file__).resolve().parent
root = Path(tempfile.mkdtemp(prefix='atlas-reservation-copy-', dir='/private/tmp'))
ignore = shutil.ignore_patterns('.venv', '.uv-cache', 'uv-cache', '__pycache__', '.pathfinder')
shutil.copytree(SOURCE / 'runs', root / 'runs', symlinks=False, ignore=ignore)
roots = [root / 'runs' / f'pair-{i}' for i in range(1, 7)]
old = root / 'old-group.json'
old.write_text(json.dumps(dict(version=1, campaigns=list(map(str, roots)),
                              budget=dict(input_tokens=1000000000, output_tokens=14000000))))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
original_receipts = {str(r): (r / 'receipts.jsonl').read_bytes() for r in roots}
for r in roots:
    c = json.loads((r / 'campaign.json').read_text())
    c.update(backend='stub', model='stub', peer_models={}, routes={}, parent='../..',
             source_cache=str(root / 'sources'), budget_usd=1e9,
             budget_group=dict(manifest=str(old), sha256=sha(old)))
    for key in ('account', 'accounts', 'refusal_fallback', 'engine', 'pathfinder_engine'):
        c.pop(key, None)
    (r / 'campaign.json').write_text(json.dumps(c))
cs = [config.load(r) for r in roots]
p = br.propose(cs[4], '398ff543ec6e4b6bab6ae24d278f4d54', 14000560, 68920,
               'OFFLINE TEST heuristic; original live approval remains pending')
ap = dict(proposal_sha256=br.digest(p), approved=True, accept_unknown_usage=True,
          accept_uncertified_actual_total=True, approved_by='OFFLINE TEST ONLY',
          approved_at='2026-10-23T00:00:00Z', authority='Synthetic test, not live authority')
new = root / 'new-group.json'; br.write_new(new, br.approved_manifest(p, ap))
for c in cs[4:]:
    c.raw['budget_group'] = dict(manifest=str(new), sha256=sha(new))
    c.path('campaign.json').write_text(json.dumps(c.raw))
    from pathfinder.cli import main
    assert main(['--root', str(c.root), 'stop', '--clear']) in (0, None)
# Preserve the existing note, derivations, ledger and consolidation artifacts in pair 5.
d = roots[4] / 'threads/Q001-P002'
protected = {str(p.relative_to(d)): sha(p) for p in d.rglob('*') if p.is_file()
             and (p.name in ('ledger.jsonl', 'Q001-P002.tex') or 'ada' in p.parts or 'consolidation' in p.parts)}
schedule = json.loads((SOURCE / 'schedule-expanded.json').read_text())
sp = root / 'schedule-expanded.json'; sp.write_text(json.dumps(schedule))
real = transport._execute
calls = []
def stub_only(c, req, *args):
    assert c.backend == 'stub' and req.model == 'stub', 'live routing forbidden in copy test'
    calls.append((c.root.name, req.stage))
    assert c.root.name in ('pair-5', 'pair-6'), 'completed prefix replay'
    if c.root.name == 'pair-5':
        assert req.stage == 'verify', 'completed peer/consolidation replay'
    return real(c, req, *args)
transport._execute = stub_only
state = coordinator.run(sp, interval=.01, heartbeat=.05, accept_change='OFFLINE STUB COPY ONLY')
assert state['status'] == 'complete', state
assert calls[0] == ('pair-5', 'verify')
assert all(sha(d / p) == h for p, h in protected.items())
for r in roots:
    assert (r / 'receipts.jsonl').read_bytes().startswith(original_receipts[str(r)])
for r in roots[:4]:
    assert (r / 'receipts.jsonl').read_bytes() == original_receipts[str(r)]
report = budget_group.report(config.load(roots[4]))
assert not report['actual_total_certified']
result = dict(copy=str(root), status=state['status'], stub_calls=calls,
              pair5_preserved_files=len(protected), completed_prefix_receipts_unchanged=True,
              original_receipts_retained=True, accounting=report, live_calls=0,
              original_live_receipt_sha256=sha(SOURCE / 'runs/pair-5/receipts.jsonl'))
(OUT / 'offline-copy-result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
