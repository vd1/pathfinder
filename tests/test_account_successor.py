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
    register=json.loads((root/'review/replacement-register.json').read_text())
    assert changes['changes']==[{'finding':r['finding'],'after':r['claim']} for r in register['records'] if r['claim']]
    assert len(changes['changes'])==2  # Surviving parent mandate plus the new withdrawal.
    final=(root/'candidate.tex').read_text()
    assert all(x['after'] in final for x in changes['changes'])
    assert 'The empty minimum is infinity.' not in str(changes)


def test_failed_successor_revision_keeps_predecessor_until_accepted(tmp_path,monkeypatch):
    from pathfinder import account_revision
    c,ed,parent,pd,args=ready(tmp_path,monkeypatch)
    script(monkeypatch,c,critic=['revise'])
    assert 'review_required' in account_successor.run(c,'Q1P1',**args,apply=True)
    failed=ed/'account-amendments/withdrawal'
    old=(failed/'candidate.tex').read_text();new=old.replace('The convention remains unspecified.','The convention is not supplied.')
    finding=next((failed/'review/reviews/current').glob('*critic*'))
    pk=tmp_path/'revise-successor';pk.mkdir()
    req=json.loads((failed/'request.json').read_text())
    change=dict(finding='reader',before='The convention remains unspecified.',after='The convention is not supplied.')
    changes={**req['changes'],'candidate_sha256':pce._sha(new),'changes':req['changes']['changes']+[change]}
    (pk/'account-candidate.tex').write_text(new)
    (pk/'changes.json').write_text(json.dumps(changes))
    (pk/'revision.json').write_text(json.dumps(dict(parent_candidate_sha256=pce._sha(old),changes=[change],findings=[dict(id='reader',path=str(finding.relative_to(failed/'review')),sha256=pce._sha(finding.read_text()),quote=finding.read_text())])))
    opts=dict(identity='withdrawal',revision='clarity',packet=pk,reason='Approved retained clarification')
    selected=(ed/'account-amendment.json').read_bytes();before=pce_recovery.hashes(ed)
    calls=script(monkeypatch,c)
    assert 'no calls' in account_revision.run(c,'Q1P1',**opts)
    assert (ed/'account-amendment.json').read_bytes()==selected
    with pytest.raises(pce.Changed,match='account-amend-revise'):account_successor.run(c,'Q1P1',**args,apply=True)
    assert 'accepted;' in account_revision.run(c,'Q1P1',**opts,apply=True)
    assert 'accepted;' in account_revision.run(c,'Q1P1',**opts,apply=True)
    assert len(calls)==5
    after=pce_recovery.hashes(ed)
    assert all(after[k]==h for k,h in before.items() if k not in ('account-amendment.json','account-successor.json'))
    account_release.view(c,'Q1P1',create=True)
    # A completed successor's accepted child may itself have a genuine returned tail.
    # The retained pending pointer names the child, not acceptance at the base folder.
    accepted_child=failed/'revisions/clarity'
    assert not (failed/'acceptance.json').exists()
    v=account_release.view(c,'Q1P1');tail=presentation.folder(v,'Q1P1');tail.mkdir()
    (tail/'state.json').write_text(json.dumps({'state':'RETURNED'}))
    returned=tail/'amend-findings.json';returned.write_text(json.dumps({'findings':[{'id':'P2','issue':'Clarify supplied convention wording.'}]}))
    next_packet=tmp_path/'next-successor';next_packet.mkdir()
    next_candidate=new.replace('The convention is not supplied.','No convention is supplied.')
    (next_packet/'account-candidate.tex').write_text(next_candidate)
    (next_packet/'successor.json').write_text(json.dumps(dict(parent_candidate_sha256=pce._sha(new),parent_acceptance_sha256=pce._sha((accepted_child/'acceptance.json').read_text()),returned_findings_sha256=pce._sha(returned.read_text()),changes=[dict(finding='P2',before='The convention is not supplied.',after='No convention is supplied.')])))
    before=pce_recovery.hashes(ed);calls=script(monkeypatch,c)
    next_args=dict(identity='next-clarity',packet=next_packet,reason='Approved next returned finding')
    assert 'accepted;' in account_successor.run(c,'Q1P1',**next_args,apply=True)
    assert len(calls)==5
    after=pce_recovery.hashes(ed)
    assert all(after[k]==h for k,h in before.items() if k not in ('account-amendment.json','account-successor.json'))
    assert account_successor.run(c,'Q1P1',**next_args,apply=True).startswith('accepted;') and len(calls)==5


def test_additive_retained_evidence_custody(tmp_path, monkeypatch):
    c,ed,parent,pd,args=ready(tmp_path,monkeypatch)
    source=c.thread_dir('Q1P1')/c.peers[0]/'retained-definition.py'
    source.parent.mkdir(parents=True,exist_ok=True)
    source.write_text('# Retained definition only; never executed.\n')
    path=args['packet']/'successor.json';delta=json.loads(path.read_text())
    delta['evidence_projection']={'version':1,'exclude':[],'include':[{
        'path':str(source.relative_to(c.thread_dir('Q1P1'))),
        'sha256':pce._sha(source.read_text()),'purpose':'Explicit retained definition'}]}
    path.write_text(json.dumps(delta));before=pce_recovery.hashes(ed)
    calls=script(monkeypatch,c)
    assert 'accepted;' in account_successor.run(c,'Q1P1',**args,apply=True)
    assert len(calls)==5
    root=ed/'account-amendments/withdrawal'
    old=json.loads((parent/'review/frozen-inputs.json').read_text())
    new=json.loads((root/'review/frozen-inputs.json').read_text())
    assert new[pce.SUPPLEMENT].startswith(old[pce.SUPPLEMENT])
    assert source.read_text() in json.loads(new[pce.SUPPLEMENT].split('## Additional retained scientific files\n\n')[1]).values()
    after=pce_recovery.hashes(ed)
    assert all(after[k]==h for k,h in before.items() if k!='account-amendment.json')
    source.write_text('# altered\n')
    with pytest.raises(pce.Changed,match='hash differs'):
        account_successor.run(c,'Q1P1',**args,apply=True)
    assert len(calls)==5
