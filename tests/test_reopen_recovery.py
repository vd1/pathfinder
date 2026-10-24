"""An ignored classic repair grant is recovered without changing its authority or history."""
import hashlib
import json
from pathlib import Path
import pytest
from pathfinder import research, reopen, reopen_recovery, stub, transport
from stubcampaign import make


def broken(tmp_path):
    c = make(tmp_path, stub={'verify': 'REVISE'})
    assert research.run_thread(c, 'Q1P1') == 'PAUSE-ON-REVISE'
    d = c.thread_dir('Q1P1'); verdict = d / 'Q1P1.verdict.json'
    values = json.loads(verdict.read_text()); values[-1]['action'] = 'fix the scalar exactly once'
    verdict.write_text(json.dumps(values))
    snapshot = tmp_path / 'judged.tex'; snapshot.write_bytes((d / 'Q1P1.tex').read_bytes())
    reopen.reopen(c, 'Q1P1', 'repair', 'one authorised repair')
    # Reproduce old engine: unbriefed consolidation, no later verifier.
    research._set(c, 'Q1P1', repair=None, stage='verify', status='stopped')
    (d / 'Q1P1.tex').write_text(stub.NOTE + '\nvoid unbriefed attempt\n')
    (d / 'consolidation/round-1-repair-1.json').write_text(json.dumps({'text': 'void'}))
    # Old records have second-resolution timestamps. Make fixture's pre-grant receipts unambiguously older.
    rows=[json.loads(l) for l in c.path('receipts.jsonl').read_text().splitlines()]
    for row in rows: row['at']='2000-01-01T00:00:00Z'
    c.path('receipts.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    return c, d, snapshot


def test_recovery_preserves_failed_round_grant_receipts_and_runs_one_briefed_verdict(tmp_path, monkeypatch):
    c,d,snapshot=broken(tmp_path)
    files=reopen_recovery._inventory(d); receipts=c.path('receipts.jsonl').read_bytes()
    grant=research.status(c,'Q1P1')['grant']; record=(d/'Q1P1.reopen.json').read_bytes()
    plan=reopen_recovery.recover(c,'Q1P1',snapshot,'restore authorised repair')
    assert files == reopen_recovery._inventory(d)
    result=reopen_recovery.recover(c,'Q1P1',snapshot,'restore authorised repair',apply=True,expected=plan['sha256'])
    archive=Path(result['custody'])/'before'
    assert all(hashlib.sha256((archive/p).read_bytes()).hexdigest()==h for p,h in files.items())
    assert c.path('receipts.jsonl').read_bytes()==receipts
    assert (d/'Q1P1.reopen.json').read_bytes()==record
    assert research.status(c,'Q1P1')['grant']==grant
    assert (d/'Q1P1.tex').read_bytes()==snapshot.read_bytes()
    assert (d/'consolidation/round-1-repair-1.json').read_text()==json.dumps({'text':'void'})
    seen=[]; real=transport.execute
    def execute(c,r):
        seen.append(r);return real(c,r)
    monkeypatch.setattr(transport,'execute',execute)
    c.raw['stub']={'verify':'ITERATE'}
    assert research.run_thread(c,'Q1P1')=='PAUSE-ON-ITERATE'
    assert [r.stage for r in seen]==['consolidate','verify']
    assert 'fix the scalar exactly once' in seen[0].prompt
    assert (d/'Q1P1.reopen.json').read_bytes()==record
    assert all(hashlib.sha256((archive/p).read_bytes()).hexdigest()==h for p,h in files.items())
    with pytest.raises(ValueError):reopen_recovery.recover(c,'Q1P1',snapshot,'again')


@pytest.mark.parametrize('mutation', ['snapshot','state','receipt','pending','active','live_owner'])
def test_recovery_refuses_stale_or_unsafe_evidence(tmp_path,mutation):
    from pathfinder import health
    import os
    c,d,snapshot=broken(tmp_path)
    plan=reopen_recovery.recover(c,'Q1P1',snapshot,'fix')
    if mutation=='snapshot': snapshot.write_text('different')
    elif mutation=='state':research._set(c,'Q1P1',round=99)
    elif mutation=='receipt':
        with c.path('receipts.jsonl').open('a') as f:f.write(json.dumps({'thread':'Q1P1','stage':'verify','at':'9999','outcome':'completed'})+'\n')
    elif mutation=='pending':(d/'verify-pending.json').write_text('{}')
    elif mutation=='active':
        c.path('active-calls').mkdir(exist_ok=True);c.path('active-calls/unknown.json').write_text('{}')
    else:health.write(c.path('runner.json'),{'pid':os.getpid()})
    before=reopen_recovery._inventory(d)
    with pytest.raises((ValueError,RuntimeError)):
        reopen_recovery.recover(c,'Q1P1',snapshot,'fix',apply=True,expected=plan['sha256'])
    assert before==reopen_recovery._inventory(d)


def test_symlink_custody_preserves_target_without_copying_external_payload(tmp_path):
    c,d,snapshot=broken(tmp_path)
    (d/'external-link').symlink_to('/nonexistent/external-payload')
    plan=reopen_recovery.recover(c,'Q1P1',snapshot,'fix')
    result=reopen_recovery.recover(c,'Q1P1',snapshot,'fix',apply=True,expected=plan['sha256'])
    saved=Path(result['custody'])/'before/external-link'
    assert saved.is_symlink() and str(saved.readlink()) == '/nonexistent/external-payload'
    assert plan['files']['external-link'] == 'symlink:/nonexistent/external-payload'
