import json
import pytest
from pathfinder import account_present, account_release, paper, pce, pce_recovery, presentation
from test_imported_account_release import imported
from test_presentation import _script, edited, check

BEFORE='The proposed experiment remains untested.'
AFTER='The proposed experiment remains untested; no experimental results are supplied.'
FINDING={'kind':'unclear','where':'"'+BEFORE+'"','issue':'Clarify the evidence limitation.','fix':'Explain the missing results.'}


def paused(tmp_path,monkeypatch):
    c,ed,old=imported(tmp_path)
    (old/'frozen-inputs.json').write_text(json.dumps({pce.SUPPLEMENT:json.dumps({'files':{'ada/note.md':'No experimental results are supplied.'}})}))
    c.raw['presentation_cycles']=0
    _script(monkeypatch,{'present/editor':[edited()], 'present_check/checker':[check(FINDING)]})
    assert account_release.present(c,'Q1P1')=='PAUSE-ON-PRESENT'
    context=tmp_path/'clarity.json';context.write_text(json.dumps({'source':'ada/note.md','quote':'No experimental results are supplied.','where':FINDING['where']}))
    return c,dict(identity='clarity-1',context_path=context,reason='Explicit one-cycle clarity grant')


def test_one_guarded_cycle_preserves_history_and_acceptance(tmp_path,monkeypatch):
    c,args=paused(tmp_path,monkeypatch)
    v=account_release.view(c,'Q1P1');d=presentation.folder(v,'Q1P1');before=pce_recovery.hashes(d)
    calls=_script(monkeypatch,{'present/corrector':[edited((BEFORE,AFTER))],'present_check/checker':[check()]})
    assert 'no calls' in account_present.apply(c,'Q1P1',**args)
    assert not calls
    assert account_present.apply(c,'Q1P1',**args,resume=True)=='CLEARED'
    assert [(r.stage,r.actor) for r in calls]==[('present','corrector'),('present_check','checker')]
    assert all('No experimental results are supplied.' in r.prompt for r in calls)
    after=pce_recovery.hashes(d)
    assert all(after[k]==h for k,h in before.items() if k!='state.json')
    pd=paper.folder(v,'Q1P1');grant=json.loads((pd/'presentation-continuations/clarity-1/grant.json').read_text())
    assert grant['prior_files_sha256']==before
    assert grant['prior_state']['state']=='PAUSE-ON-PRESENT'
    assert account_present.apply(c,'Q1P1',**args,resume=True)=='CLEARED'
    assert len(calls)==2
    assert account_release.release(c,'Q1P1',timestamp='20261019T210000Z')['status']=='RELEASED'


def test_failure_stays_paused_without_renewing_budget(tmp_path,monkeypatch):
    c,args=paused(tmp_path,monkeypatch)
    calls=_script(monkeypatch,{'present/corrector':[edited()], 'present_check/checker':[check(FINDING)]})
    assert account_present.apply(c,'Q1P1',**args,resume=True)=='PAUSE-ON-PRESENT'
    assert account_present.apply(c,'Q1P1',**args,resume=True)=='PAUSE-ON-PRESENT'
    assert len(calls)==2


def test_unapproved_quote_refused_before_calls(tmp_path,monkeypatch):
    c,args=paused(tmp_path,monkeypatch)
    data=json.loads(args['context_path'].read_text());data['quote']='New scientific assertion.'
    args['context_path'].write_text(json.dumps(data))
    calls=_script(monkeypatch,{})
    with pytest.raises(pce.Changed,match='accepted scientific evidence'):account_present.apply(c,'Q1P1',**args,resume=True)
    assert not calls


def test_interrupted_check_resumes_without_second_correction(tmp_path,monkeypatch):
    c,args=paused(tmp_path,monkeypatch)
    original_check=presentation._check
    interrupted_once=[]
    def interrupted(c,pair,stage,*args):
        if stage=='correct-1' and not interrupted_once:
            interrupted_once.append(True)
            raise RuntimeError('interrupted before check transport')
        return original_check(c,pair,stage,*args)
    monkeypatch.setattr(presentation,'_check',interrupted)
    calls=_script(monkeypatch,{'present/corrector':[edited((BEFORE,AFTER))], 'present_check/checker':[check()]})
    with pytest.raises(RuntimeError):account_present.apply(c,'Q1P1',**args,resume=True)
    with pytest.raises(pce.Changed,match='active account-present-continue'):account_release.present(c,'Q1P1',restart=True)
    assert account_present.apply(c,'Q1P1',**args,resume=True)=='CLEARED'
    assert sum(r.actor=='corrector' for r in calls)==1


def test_old_artifact_tamper_blocks_resume(tmp_path,monkeypatch):
    c,args=paused(tmp_path,monkeypatch);account_present.apply(c,'Q1P1',**args)
    v=account_release.view(c,'Q1P1');p=presentation.final(v,'Q1P1');p.write_text(p.read_text()+'%changed\n')
    calls=_script(monkeypatch,{})
    with pytest.raises(pce.Changed,match='history changed'):account_present.apply(c,'Q1P1',**args,resume=True)
    assert not calls


def test_retained_corrector_reply_survives_host_interruption(tmp_path,monkeypatch):
    c,args=paused(tmp_path,monkeypatch)
    actual=paper.build;failed=[]
    def interrupt(d,*args,**kw):
        if d.name=='correct-1' and not failed:
            failed.append(True);raise RuntimeError('host interrupted before build')
        return actual(d,*args,**kw)
    monkeypatch.setattr(paper,'build',interrupt)
    calls=_script(monkeypatch,{'present/corrector':[edited((BEFORE,AFTER))], 'present_check/checker':[check()]})
    with pytest.raises(RuntimeError,match='before build'):account_present.apply(c,'Q1P1',**args,resume=True)
    assert account_present.apply(c,'Q1P1',**args,resume=True)=='CLEARED'
    assert sum(r.actor=='corrector' for r in calls)==1
