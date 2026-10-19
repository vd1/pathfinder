import json
import pytest
from pathfinder import account_successor, account_amend, account_release, paper, pce, pce_recovery, presentation
from test_account_amend import packet
from test_pce import script


def ready(tmp_path, monkeypatch):
    c, ed, candidate, args = packet(tmp_path)
    script(monkeypatch,c)
    assert 'accepted;' in account_amend.apply(c,'Q1P1',**args,resume=True)
    parent=account_amend._root(c,'Q1P1',args['identity'])
    v=account_release.view(c,'Q1P1',create=True)
    pd=presentation.folder(v,'Q1P1');pd.mkdir()
    (pd/'state.json').write_text(json.dumps({'state':'RETURNED'}))
    f=pd/'amend-findings.json';f.write_text(json.dumps({'findings':[{'id':'P1','issue':'Withdraw claim.'}]}))
    pk=tmp_path/'successor';pk.mkdir()
    before='The empty minimum is infinity.';after='The convention remains unspecified.'
    (pk/'account-candidate.tex').write_text(candidate.replace(before,after))
    (pk/'successor.json').write_text(json.dumps(dict(parent_candidate_sha256=pce._sha(candidate),
        parent_acceptance_sha256=pce._sha((parent/'acceptance.json').read_text()),
        returned_findings_sha256=pce._sha(f.read_text()),changes=[dict(finding='P1',before=before,after=after)])))
    return c,ed,parent,pd,dict(identity='withdrawal',packet=pk,reason='Approved withdrawal scope')


def test_successor_acceptance_history_and_idempotent_install(tmp_path,monkeypatch):
    c,ed,parent,pd,args=ready(tmp_path,monkeypatch)
    before=pce_recovery.hashes(ed);pointer=(ed/'account-amendment.json').read_bytes()
    calls=script(monkeypatch,c)
    assert 'no calls' in account_successor.run(c,'Q1P1',**args)
    assert not calls and (ed/'account-amendment.json').read_bytes()==pointer
    assert 'accepted;' in account_successor.run(c,'Q1P1',**args,apply=True)
    assert len(calls)==5
    assert 'accepted;' in account_successor.run(c,'Q1P1',**args,apply=True)
    assert len(calls)==5
    after=pce_recovery.hashes(ed)
    assert all(after[k]==h for k,h in before.items() if k!='account-amendment.json')
    v=account_release.view(c,'Q1P1',create=True)
    record=json.loads((paper.folder(v,'Q1P1')/'acceptance.json').read_text())
    assert record['predecessor']['workflow']==str(parent.relative_to(c.thread_dir('Q1P1')))
    assert record['original_acceptance']['kind'].startswith('imported EVA2')
    assert not presentation.folder(v,'Q1P1').exists()


@pytest.mark.parametrize('damage',['candidate','acceptance','finding','history','state'])
def test_invalid_successor_no_dispatch(tmp_path,monkeypatch,damage):
    c,ed,parent,pd,args=ready(tmp_path,monkeypatch)
    pk=args['packet']
    if damage=='history':
        account_successor.run(c,'Q1P1',**args)
        (pd/'state.json').write_text('{}')
    elif damage=='state':(pd/'state.json').write_text('{"state":"CLEARED"}')
    elif damage=='candidate':
        with (pk/'account-candidate.tex').open('a') as f:f.write('undeclared')
    else:
        path=pk/'successor.json';d=json.loads(path.read_text())
        d['parent_acceptance_sha256' if damage=='acceptance' else 'returned_findings_sha256']='bad'
        path.write_text(json.dumps(d))
    monkeypatch.setattr(pce,'run',lambda *a,**kw:pytest.fail('must not dispatch'))
    with pytest.raises(pce.Changed):account_successor.run(c,'Q1P1',**args,apply=True)


def test_failed_review_preserves_selection_and_exhausts_grant(tmp_path,monkeypatch):
    c,ed,parent,pd,args=ready(tmp_path,monkeypatch)
    pointer=(ed/'account-amendment.json').read_bytes()
    calls=script(monkeypatch,c,critic=['revise'])
    assert 'review_required' in account_successor.run(c,'Q1P1',**args,apply=True)
    count=len(calls)
    assert 'review_required' in account_successor.run(c,'Q1P1',**args,apply=True)
    assert len(calls)==count and (ed/'account-amendment.json').read_bytes()==pointer


def test_install_interruption_reuses_acceptance_without_calls(tmp_path,monkeypatch):
    c,ed,parent,pd,args=ready(tmp_path,monkeypatch)
    calls=script(monkeypatch,c);real=pce._write
    def interrupt(root,name,*a,**kw):
        if name=='account-amendment.json':raise RuntimeError('install interrupted')
        return real(root,name,*a,**kw)
    monkeypatch.setattr(pce,'_write',interrupt)
    with pytest.raises(RuntimeError):account_successor.run(c,'Q1P1',**args,apply=True)
    monkeypatch.setattr(pce,'_write',real)
    assert 'accepted;' in account_successor.run(c,'Q1P1',**args,apply=True)
    assert len(calls)==5


def test_stop_guard_and_competing_successor(tmp_path,monkeypatch):
    from pathfinder import runner
    c,ed,parent,pd,args=ready(tmp_path,monkeypatch)
    pointer=(ed/'account-amendment.json').read_bytes()
    calls=script(monkeypatch,c)
    monkeypatch.setattr(runner,'guard_ok',lambda *a,**kw:False)
    assert 'stopped:' in account_successor.run(c,'Q1P1',**args,apply=True)
    assert not calls and (ed/'account-amendment.json').read_bytes()==pointer
    with pytest.raises(pce.Changed,match='existing successor'):
        account_successor.run(c,'Q1P1',**{**args,'identity':'competing'})


def test_inherits_external_evidence_without_parent_reviews(tmp_path,monkeypatch):
    c,ed,parent,pd,args=ready(tmp_path,monkeypatch)
    account_successor.run(c,'Q1P1',**args)
    root=ed/'account-amendments/withdrawal'
    old=json.loads((parent/'review/frozen-inputs.json').read_text())
    new=json.loads((root/'review/frozen-inputs.json').read_text())
    for name in old:
        if name.startswith('sources/external/'):
            assert new[name]==old[name]
    assert not any(name.startswith('reviews/') for name in new)
    changes=json.loads(new['sources/internal/changes.json'])
    assert len(changes['changes'])==1
    assert changes['baseline_sha256']==pce._sha((parent/'candidate.tex').read_text())
