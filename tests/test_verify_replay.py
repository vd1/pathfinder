import hashlib,json,shutil
import pytest
from pathfinder import config, pce, pce_recovery, research, stub, verify_replay as vr, transport
from stubcampaign import make


def copied(tmp_path):
    c=make(tmp_path/'original',rounds=3,repairs=2)
    research.run_thread(c,'Q1P1')
    research._set(c,'Q1P1',status='PAUSE',stage='done')
    d=c.thread_dir('Q1P1')
    (d/'verify-pending.json').write_text(json.dumps({'old':'saved reply'}))
    (d/'paper').mkdir();(d/'paper/old.json').write_text('{}')
    shutil.copytree(c.root,tmp_path/'followup')
    return c,config.load(tmp_path/'followup')


@pytest.mark.parametrize('decision',['DRAFT','PAUSE','ITERATE','REVISE'])
def test_classic_copy_verifier_only_then_ordinary_next_stage(tmp_path,monkeypatch,decision):
    original,c=copied(tmp_path);before=pce_recovery.hashes(original.root);calls=[]
    def reply(c,r):
        calls.append(r)
        return json.dumps({'decision':decision,'reason':'Existing bounded result reassessed.','action':'A concrete next step.'})
    monkeypatch.setattr(stub,'reply',reply)
    assert vr.run(c,'Q1P1',origin=original.root,reason='Authorised copy replay')['status']=='prepared'
    d=c.thread_dir('Q1P1');root=d/'reassessment'
    assert not (d/'paper').exists() and (root/'prior/paper/old.json').exists()
    assert (root/'prior/verify-pending.json').exists() and not (d/'verify-pending.json').exists()
    result=vr.run(c,'Q1P1',apply=True)
    assert len(calls)==1 and calls[0].stage=='verify'
    assert vr.run(c,'Q1P1',apply=True)==result and len(calls)==1
    assert pce_recovery.hashes(original.root)==before
    assert (d/'Q1P1.tex').read_bytes()==(original.thread_dir('Q1P1')/'Q1P1.tex').read_bytes()
    assert result['status']['stage']=={'ITERATE':'peers','REVISE':'consolidate'}.get(decision,'done')
    old=json.loads((root/'prior/Q1P1.verdict.json').read_text());new=json.loads((d/'Q1P1.verdict.json').read_text())
    assert new[:-1]==old and new[-1]['decision']==decision


def test_reject_original_and_changed_copy(tmp_path):
    original,c=copied(tmp_path)
    with pytest.raises(pce.Changed,match='distinct'):vr.run(original,'Q1P1',origin=original.root,reason='No')
    (c.thread_dir('Q1P1')/'Q1P1.tex').write_text('changed')
    with pytest.raises(pce.Changed,match='exact'):vr.run(c,'Q1P1',origin=original.root,reason='No')


def test_prompt_is_frozen_and_pending_not_reused(tmp_path,monkeypatch):
    original,c=copied(tmp_path)
    (c.root/'prompts').mkdir();(c.root/'prompts/verify.md').write_text('A more exploratory verifier criterion.')
    vr.run(c,'Q1P1',origin=original.root,reason='Prompt-only reassessment')
    (c.root/'prompts/verify.md').write_text('Changed after preparation')
    with pytest.raises(pce.Changed,match='prompt changed'):vr.run(c,'Q1P1',apply=True)


def test_commit_interruption_resumes_without_call(tmp_path,monkeypatch):
    original,c=copied(tmp_path);calls=[]
    monkeypatch.setattr(stub,'reply',lambda c,r:calls.append(r) or json.dumps({'decision':'DRAFT'}))
    vr.run(c,'Q1P1',origin=original.root,reason='Replay')
    real=vr._install
    monkeypatch.setattr(vr,'_install',lambda *a:(_ for _ in ()).throw(RuntimeError('interrupted')))
    with pytest.raises(RuntimeError):vr.run(c,'Q1P1',apply=True)
    monkeypatch.setattr(vr,'_install',real)
    assert vr.run(c,'Q1P1',apply=True)['status']['status']=='DRAFT' and len(calls)==1
