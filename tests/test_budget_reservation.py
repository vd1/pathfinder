import copy
import hashlib
import json
from pathlib import Path

import pytest
from pathfinder import budget_group as bg, budget_reservation as br, transport, research
from stubcampaign import make


def setup(tmp_path):
    a, b = [make(tmp_path / n, budget_usd=1e9) for n in ('a', 'b')]
    old = tmp_path / 'original.json'
    old.write_text(json.dumps(dict(version=1, campaigns=[str(a.root), str(b.root)],
                                  budget=dict(input_tokens=1000000, output_tokens=100000))))
    for c in (a, b):
        c.raw['budget_group'] = dict(manifest=str(old), sha256=hashlib.sha256(old.read_bytes()).hexdigest())
    msg = 'Selected model is at capacity. Please try a different model.'
    row = dict(call_id='failed', backend='codex', outcome='error', stage='verify', usage=None,
               input_tokens=None, output_tokens=None, error=msg, failure={'class': 'rate'},
               raw_events=[json.dumps(dict(type='thread.started', thread_id='original')),
                           json.dumps(dict(type='item.completed', item=dict(type='agent_message', text='Checking'))),
                           json.dumps(dict(type='turn.failed', error=dict(message=msg)))])
    a.path('receipts.jsonl').write_text(json.dumps(row) + '\n')
    return a, b, old


def proposal(a):
    return br.propose(a, 'failed', 10000, 1000, 'TEST ONLY: explicit heuristic, not a measured upper bound')


def approval(p):
    return dict(proposal_sha256=br.digest(p), approved=True, accept_unknown_usage=True,
                accept_uncertified_actual_total=True, approved_by='OFFLINE TEST',
                approved_at='2026-10-23T00:00:00Z', authority='Synthetic test authority; not a real approval')


def install(tmp_path, a, b, p):
    doc = br.approved_manifest(p, approval(p))
    path = tmp_path / 'approved.json'
    br.write_new(path, doc)
    for c in (a, b):
        c.raw['budget_group'] = dict(manifest=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return path, doc


def test_proposal_inert_and_original_bytes_unchanged(tmp_path):
    a, b, old = setup(tmp_path)
    before = a.path('receipts.jsonl').read_bytes(), old.read_bytes()
    p = proposal(a)
    assert 'unknown' in bg.refusal(*bg.load(b)[1:])
    path, doc = install(tmp_path, a, b, p)
    r = bg.report(b)
    assert r['measured'] == dict(calls=1, input_tokens=0, output_tokens=0)
    assert r['reserved'] == dict(input_tokens=10000, output_tokens=1000)
    assert not r['actual_total_certified']
    assert r['unknown_calls'][0]['reserved']
    assert before == (a.path('receipts.jsonl').read_bytes(), old.read_bytes())
    assert transport.receipts(a)[0]['input_tokens'] is None
    assert bg.refusal(*bg.load(b)[1:], br.records(doc)) is None
    with pytest.raises(FileExistsError):
        br.write_new(path, doc)


@pytest.mark.parametrize('mutation', ['missing', 'false', 'hash', 'amount', 'scope', 'receipt', 'duplicate', 'parent', 'two', 'unknownextra', 'active'])
def test_fail_closed(tmp_path, mutation):
    a, b, old = setup(tmp_path)
    p = proposal(a)
    ap = approval(p)
    if mutation == 'missing':
        del ap['accept_unknown_usage']
    elif mutation == 'false':
        ap['approved'] = False
    elif mutation == 'hash':
        ap['proposal_sha256'] = '0' * 64
    elif mutation == 'amount':
        p['reservation']['input_tokens'] += 1
    elif mutation == 'scope':
        p['scope']['budget']['input_tokens'] += 1
    elif mutation == 'receipt':
        a.path('receipts.jsonl').write_text(a.path('receipts.jsonl').read_text().replace('Checking', 'Altered'))
    elif mutation == 'duplicate':
        with a.path('receipts.jsonl').open('a') as f:
            f.write(a.path('receipts.jsonl').read_text())
    elif mutation == 'parent':
        old.write_text(old.read_text() + ' ')
    if mutation in ('unknownextra', 'active'):
        path, doc = install(tmp_path, a, b, p)
        if mutation == 'unknownextra':
            b.path('receipts.jsonl').write_text(json.dumps(dict(call_id='other', outcome='error')) + '\n')
        else:
            b.path('active-calls').mkdir(); b.path('active-calls/pending.json').write_text('{}')
        assert bg.refusal(*bg.load(b)[1:], br.records(doc))
    elif mutation == 'two':
        doc = br.approved_manifest(p, ap); doc['reservations'] *= 2
        with pytest.raises(ValueError):
            br.records(doc)
    else:
        with pytest.raises(ValueError):
            br.approved_manifest(p, ap)


@pytest.mark.parametrize('n', [0, -1, True, 1000001, None])
def test_amounts_invalid(tmp_path, n):
    a, _, _ = setup(tmp_path)
    with pytest.raises(ValueError):
        br.propose(a, 'failed', n, 1000, 'test')


def test_cap_and_new_admissions(tmp_path):
    a, b, old = setup(tmp_path)
    p = br.propose(a, 'failed', 600000, 1000, 'test policy')
    _, doc = install(tmp_path, a, b, p)
    # The usual mean projection includes the reservation, so the next call is refused.
    assert 'input_tokens' in bg.refusal(*bg.load(b)[1:], br.records(doc))
    req = transport.request('test', model='stub', tools=False, search=False,
                            cwd=b.root, timeout=1, thread='Q1P1', stage='verify', actor='verifier')
    from pathfinder.admission import Refused
    with pytest.raises(Refused):
        transport.execute(b, req)
    assert transport.receipts(b)[0]['outcome'] == 'refused'


def test_resume_verifier_only_preserves_research(tmp_path, monkeypatch):
    a, b, _ = setup(tmp_path)
    # Build a real canonical stub research thread, then place its state at the failed verifier.
    original_failed = a.path('receipts.jsonl').read_bytes()
    a.raw.pop('budget_group')
    research.run_thread(a, 'Q1P1')
    d = a.thread_dir('Q1P1')
    state = json.loads((d / 'status.json').read_text())
    state.update(stage='verify', status='stopped', round=1)
    (d / 'status.json').write_text(json.dumps(state))
    # Include the original failure after the preparatory offline calls.
    with a.path('receipts.jsonl').open('ab') as f:
        f.write(original_failed)
    # Remove the first synthetic occurrence, retaining exactly one immutable failed line.
    lines = a.path('receipts.jsonl').read_bytes().splitlines(keepends=True)
    a.path('receipts.jsonl').write_bytes(b''.join(lines[1:]))
    a.raw['budget_group'] = b.raw['budget_group']
    p = proposal(a)
    install(tmp_path, a, b, p)
    preserved = {str(f.relative_to(d)): f.read_bytes() for f in d.rglob('*') if f.is_file()
                 and (f.name == 'ledger.jsonl' or f.suffix == '.tex' and f.name != 'pathfinder-meta.tex'
                      or 'consolidation' in f.parts or 'ada' in f.parts)}
    receipts_before = a.path('receipts.jsonl').read_bytes()
    real = transport.execute; stages = []
    def only_verify(c, r):
        stages.append(r.stage)
        assert r.stage == 'verify'
        return real(c, r)
    monkeypatch.setattr(transport, 'execute', only_verify)
    research.run_thread(a, 'Q1P1')
    assert stages == ['verify']
    assert json.loads((d / 'status.json').read_text())['status'] == 'DRAFT'
    assert a.path('receipts.jsonl').read_bytes().startswith(receipts_before)
    assert all((d / path).read_bytes() == body for path, body in preserved.items())
    assert not bg.report(a)['actual_total_certified']


def test_runtime_tamper_and_cli_approval_gate(tmp_path, capsys):
    from pathfinder.cli import main
    a, b, old = setup(tmp_path)
    # Persist original test config for canonical CLI loading.
    a.path('campaign.json').write_text(json.dumps(a.raw))
    out = tmp_path / 'proposal.json'
    assert main(['--root', str(a.root), 'budget-reservation', 'propose', '--call-id', 'failed',
                 '--input-tokens', '10000', '--output-tokens', '1000', '--rationale', 'test only',
                 '--out', str(out)]) == 0
    p = json.loads(out.read_text())
    assert main(['budget-reservation', 'manifest', '--proposal', str(out),
                 '--out', str(tmp_path / 'not-approved.json')]) == 1
    assert not (tmp_path / 'not-approved.json').exists()
    path, doc = install(tmp_path, a, b, p)
    assert bg.report(b)['reservation_notice'] == br.NOTICE
    a.path('receipts.jsonl').write_text(a.path('receipts.jsonl').read_text() + ' ')
    # Whitespace not inside the bound receipt line is harmless.
    assert bg.report(b)['reserved']['input_tokens'] == 10000
    a.path('receipts.jsonl').write_text(a.path('receipts.jsonl').read_text().replace('Checking', 'changed'))
    with pytest.raises(ValueError, match='receipt or evidence changed'):
        bg.report(b)
