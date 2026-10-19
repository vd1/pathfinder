import json
import pytest
from pathfinder import account_amend,account_revision,account_release,pce,pce_recovery,paper
from test_account_amend import packet
from test_pce import script


def prepared(tmp_path,monkeypatch):
    c,ed,candidate,args=packet(tmp_path)
    script(monkeypatch,c,critic=['revise'])
    assert 'review_required' in account_amend.apply(c,'Q1P1',**args,resume=True)
    root=account_amend._root(c,'Q1P1',args['identity'])
    finding=next((root/'review/reviews/current').glob('*critic*'))
    prior=json.loads((root/'request.json').read_text())['changes']
    old=prior['changes'][0]['after'];new=old+' This convention concerns the empty set.'
    updated=candidate.replace(old,new)
    pk=tmp_path/'revision-packet';pk.mkdir()
    changes={**prior,'candidate_sha256':pce._sha(updated),'changes':[{**prior['changes'][0],'after':new}]}
    (pk/'account-candidate.tex').write_text(updated)
    (pk/'changes.json').write_text(json.dumps(changes))
    (pk/'revision.json').write_text(json.dumps({'parent_candidate_sha256':pce._sha(candidate),
      'changes':[{'finding':'critic-clarity','before':old,'after':new}],
      'findings':[{'id':'critic-clarity','path':str(finding.relative_to(root/'review')),
                  'sha256':pce._sha(finding.read_text()),'quote':finding.read_text()}]}))
    return c,ed,root,updated,dict(identity=args['identity'],revision='clarity-1',packet=pk,reason='Approved bounded clarification')


def test_revision_keeps_identity_rounds_and_original_acceptance(tmp_path,monkeypatch):
    c,ed,old,candidate,args=prepared(tmp_path,monkeypatch)
    before=pce_recovery.hashes(ed);calls=script(monkeypatch,c)
    assert 'no calls' in account_revision.run(c,'Q1P1',**args)
    assert not calls
    assert 'accepted;' in account_revision.run(c,'Q1P1',**args,apply=True)
    assert len(calls)==5
    assert 'accepted;' in account_revision.run(c,'Q1P1',**args,apply=True) and len(calls)==5
    assert all(pce_recovery.hashes(ed)[k]==v for k,v in before.items() if k!='account-amendment.json')
    pointer=json.loads((ed/'account-amendment.json').read_text());assert pointer=={'id':'definitions','revision':'clarity-1'}
    view=account_release.view(c,'Q1P1',create=True)
    assert (paper.folder(view,'Q1P1')/'paper.tex').read_text()==candidate
    acceptance=json.loads((paper.folder(view,'Q1P1')/'acceptance.json').read_text())
    assert acceptance['original_acceptance']['kind'].startswith('imported EVA2')


@pytest.mark.parametrize('damage',['hash','delta','history','finding'])
def test_invalid_revision_refused_without_calls(tmp_path,monkeypatch,damage):
    c,ed,old,candidate,args=prepared(tmp_path,monkeypatch)
    pk=args['packet'];delta=json.loads((pk/'revision.json').read_text())
    if damage=='hash':delta['parent_candidate_sha256']='bad'
    elif damage=='delta':delta['changes'][0]['before']='absent'
    elif damage=='finding':delta['findings'][0]['sha256']='bad'
    (pk/'revision.json').write_text(json.dumps(delta))
    if damage=='history':
        account_revision.run(c,'Q1P1',**args)
        (old/'review/result.json').write_text('{}')
    monkeypatch.setattr(pce,'run',lambda *a,**k:pytest.fail('must not dispatch'))
    with pytest.raises(pce.Changed):account_revision.run(c,'Q1P1',**args,apply=True)


def test_preparation_resumes_after_pointer_write_interruption(tmp_path,monkeypatch):
    c,ed,old,candidate,args=prepared(tmp_path,monkeypatch)
    real=pce._write
    def interrupted(root,name,*a,**kw):
        if name=='account-amendment.json':raise RuntimeError('interrupted pointer')
        return real(root,name,*a,**kw)
    monkeypatch.setattr(pce,'_write',interrupted)
    with pytest.raises(RuntimeError):account_revision.run(c,'Q1P1',**args)
    monkeypatch.setattr(pce,'_write',real)
    assert 'no calls' in account_revision.run(c,'Q1P1',**args)
    assert json.loads((ed/'account-amendment.json').read_text())['revision']=='clarity-1'
