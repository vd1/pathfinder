import json
import pytest
from pathfinder import account_amend, account_review, account_release, pce, pce_recovery, paper
from test_account_amend import packet
from test_pce import script


def failed(tmp_path, monkeypatch):
    c, ed, candidate, args = packet(tmp_path)
    script(monkeypatch,c,fact_checker=['fail'])
    assert 'review_required' in account_amend.apply(c,'Q1P1',**args,resume=True)
    root=ed/'account-amendments/definitions'
    original=json.loads((root/'review/frozen-inputs.json').read_text())
    supplement={'files':{'ada/proof.md':'An empty minimum is infinity.',
                          'ledger.jsonl':json.dumps({'kind':'finding','text':'bounded result'})},
                'coverage_limit':'Generated evidence, not independent literature.'}
    inputs=tmp_path/'historical.json'
    inputs.write_text(json.dumps({'internal':{'earlier-review':'SECRET PRIOR REVIEW'},
        'external':{'P.txt':original['sources/external/P.txt'],'Q.txt':original['sources/external/Q.txt'],
                    'research-supplement.md':json.dumps(supplement)}}))
    repair=dict(identity='definitions',grant_id='evidence-1',inputs=inputs,
                inputs_sha256=pce._sha(inputs.read_text()),reason='Explicit evidence repair authority')
    return c,root,candidate,repair


def test_fresh_repair_preserves_failed_round_and_reaches_release(tmp_path,monkeypatch):
    from test_presentation import _script,edited,check
    c,root,candidate,args=failed(tmp_path,monkeypatch)
    original=pce_recovery.hashes(root/'review')
    calls=script(monkeypatch,c)
    assert 'no calls' in account_review.apply(c,'Q1P1',**args)
    assert not calls
    assert 'accepted;' in account_review.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==5
    assert 'accepted;' in account_review.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==5
    assert pce_recovery.hashes(root/'review')==original
    target=root/'review-grants/evidence-1'
    assert len(list((target/'visibility').glob('*.json')))==5
    for call in calls:
        assert 'SECRET PRIOR REVIEW' not in call['prompt']
        shown=json.loads(call['prompt'].split('Allowed input files:\n')[1])
        if call['role'] == 'author':
            assert 'baseline_sha256' not in json.dumps(shown)
        if call['role'] in ('critic','fact-checker'):
            assert shown[pce.DRAFT]==candidate
            assert json.loads(shown[pce.SUPPLEMENT])['files']['ada/proof.md']=='An empty minimum is infinity.'
            assert not any(n.startswith(('reviews/','sources/internal/')) for n in shown)
    _script(monkeypatch,{'present/editor':[edited()], 'present_check/checker':[check()]})
    assert account_release.present(c,'Q1P1')=='CLEARED'
    assert account_release.release(c,'Q1P1',timestamp='20261019T190000Z')['status']=='RELEASED'
    assert pce_recovery.hashes(root/'review')==original
    assert pce.result(c,'Q1P1')['status']=='none'


def test_failed_new_review_never_renews_or_installs(tmp_path,monkeypatch):
    c,root,candidate,args=failed(tmp_path,monkeypatch)
    calls=script(monkeypatch,c,fact_checker=['fail'])
    assert 'review_required' in account_review.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==3
    assert 'review_required' in account_review.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==3
    with pytest.raises(pce.Changed,match='awaiting acceptance'):account_release.view(c,'Q1P1')


@pytest.mark.parametrize('change',['hash','paper','review','oversize','custody'])
def test_bad_repair_refused_before_activation_or_calls(tmp_path,monkeypatch,change):
    c,root,candidate,args=failed(tmp_path,monkeypatch)
    data=json.loads(args['inputs'].read_text())
    if change=='paper':data['external']['Q.txt']+='changed'
    if change=='review':
        s=json.loads(data['external']['research-supplement.md'])
        s['files']['ledger.jsonl']=json.dumps({'kind':'review','text':'accept'})
        data['external']['research-supplement.md']=json.dumps(s)
    args['inputs'].write_text(json.dumps(data));args['inputs_sha256']=pce._sha(args['inputs'].read_text())
    if change=='hash':args['inputs_sha256']='bad'
    if change=='oversize':c.raw['max_prompt_chars']=100
    if change=='custody':(root/'candidate.tex').write_text(candidate+'extra')
    calls=script(monkeypatch,c)
    with pytest.raises(pce.Changed):account_review.apply(c,'Q1P1',**args,resume=True)
    assert not calls
    assert not (root/'review-active.json').exists()


def test_interrupted_resume_and_parent_tamper(tmp_path,monkeypatch):
    from pathfinder.thread import Stopped
    c,root,candidate,args=failed(tmp_path,monkeypatch)
    calls=script(monkeypatch,c);dispatch=pce._dispatch
    def interrupt(c,pair,role,prompt,seconds=None):
        if role=='critic':raise Stopped()
        return dispatch(c,pair,role,prompt,seconds=seconds)
    monkeypatch.setattr(pce,'_dispatch',interrupt)
    with pytest.raises(Stopped):account_review.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==3
    old=(root/'review/result.json').read_text()
    (root/'review/result.json').write_text(old+' ')
    with pytest.raises(pce.Changed,match='parent round'):account_review.apply(c,'Q1P1',**args,resume=True)
    (root/'review/result.json').write_text(old)
    monkeypatch.setattr(pce,'_dispatch',dispatch)
    assert 'accepted;' in account_review.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==5


def test_legacy_command_cannot_touch_repair(tmp_path,monkeypatch):
    c,root,candidate,args=failed(tmp_path,monkeypatch)
    account_review.apply(c,'Q1P1',**args)
    before=pce_recovery.hashes(root)
    with pytest.raises(pce.Changed,match='account-amend-review'):
        account_amend.apply(c,'Q1P1',identity='definitions',packet=tmp_path/'packet',evidence_root=c.root,reason='unused')
    assert pce_recovery.hashes(root)==before


def test_scope_leak_or_expanded_context_stops_without_dropping_evidence(tmp_path,monkeypatch):
    from pathfinder import resources
    import copy
    c,root,candidate,args=failed(tmp_path,monkeypatch)
    account_review.apply(c,'Q1P1',**args)
    c._pce_workflow=root/'review-grants/evidence-1'
    calls=script(monkeypatch,c)
    original=resources.prompt
    def leaky(c,name,**values):
        prompt=original(c,name,**values)
        if name=='pce-fact-checker':prompt=prompt.replace('## Read Scope\n','## Read Scope\n\n- `sources/internal/**`\n')
        return prompt
    monkeypatch.setattr(resources,'prompt',leaky)
    with pytest.raises(pce.Changed,match='fresh review scope'):pce.run(c,'Q1P1')
    assert [x['role'] for x in calls]==['author','archivist']
    assert not (c._pce_workflow/'dispatch/pass-01-fact-checker.json').exists()


def test_cli_grant_uses_stub_routes_and_retained_calls(tmp_path,monkeypatch):
    from pathfinder import cli
    c,root,candidate,args=failed(tmp_path,monkeypatch)
    monkeypatch.undo()
    argv=['--root',str(c.root),'account-amend-review','Q1P1','--id',args['identity'],'--grant',args['grant_id'],
          '--inputs',str(args['inputs']),'--inputs-sha256',args['inputs_sha256'],'--reason',args['reason']]
    cli.main(argv)
    assert not (root/'review-grants/evidence-1/dispatch').exists()
    cli.main(argv+['--apply'])
    rows=list((root/'review-grants/evidence-1/dispatch').glob('*.json'))
    assert len(rows)==5
    assert all(json.loads(p.read_text())['receipt']['backend']=='stub' for p in rows)
    assert (root/'acceptance.json').exists()


def test_evidence_repair_of_selected_child_preserves_identity_and_history(tmp_path,monkeypatch):
    from test_account_revision import prepared
    from pathfinder import account_revision
    c,ed,parent,candidate,revision_args=prepared(tmp_path,monkeypatch)
    script(monkeypatch,c,critic=['contaminated'])
    assert 'review_required' in account_revision.run(c,'Q1P1',**revision_args,apply=True)
    child=parent/'revisions'/revision_args['revision']
    before=pce_recovery.hashes(ed)
    pointer=(ed/'account-amendment.json').read_bytes()
    frozen=json.loads((child/'review/frozen-inputs.json').read_text())
    inputs=tmp_path/'clean-child-evidence.json'
    inputs.write_text(json.dumps({'external':{
        'P.txt':frozen['sources/external/P.txt'],
        'Q.txt':frozen['sources/external/Q.txt'],
        'research-supplement.md':json.dumps({'files':{'ada/proof.md':'An empty minimum is infinity.'}})}}))
    args=dict(identity=revision_args['identity'],grant_id='clean-child-1',inputs=inputs,
              inputs_sha256=pce._sha(inputs.read_text()),reason='Fresh evidence after contaminated child review')
    calls=script(monkeypatch,c)
    assert 'no calls' in account_review.apply(c,'Q1P1',**args)
    assert not calls and (ed/'account-amendment.json').read_bytes()==pointer
    assert account_review.workflow(child)==child/'review-grants/clean-child-1'
    assert 'accepted;' in account_review.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==5
    assert (child/'candidate.tex').read_text()==candidate
    assert (child/'build/paper.pdf').exists()
    assert (ed/'account-amendment.json').read_bytes()==pointer
    assert all(pce_recovery.hashes(ed)[k]==v for k,v in before.items())
    assert 'accepted;' in account_review.apply(c,'Q1P1',**args,resume=True)
    assert len(calls)==5


def clean_packet(tmp_path,root,identity):
    files=json.loads((root/'review/frozen-inputs.json').read_text())
    inputs=tmp_path/'clean-inputs.json'
    inputs.write_text(json.dumps({'external':{'P.txt':files['sources/external/P.txt'],'Q.txt':files['sources/external/Q.txt'],'research-supplement.md':json.dumps({'files':{'ada/proof.txt':'Retained scientific definition.'}})}}))
    return dict(identity=identity,grant_id='preflight-clean',inputs=inputs,inputs_sha256=pce._sha(inputs.read_text()),reason='Explicit preflight evidence isolation',before_first_call=True)


def test_prepared_review_clean_before_first_call(tmp_path,monkeypatch):
    c,ed,candidate,args=packet(tmp_path)
    assert 'no calls' in account_amend.apply(c,'Q1P1',**args)
    root=ed/'account-amendments/definitions';before=pce_recovery.hashes(root/'review')
    opts=clean_packet(tmp_path,root,'definitions');calls=script(monkeypatch,c)
    with pytest.raises(pce.Changed,match='terminal failed'):
        account_review.apply(c,'Q1P1',**{**opts,'before_first_call':False})
    assert 'no calls' in account_review.apply(c,'Q1P1',**opts) and not calls
    assert 'accepted;' in account_review.apply(c,'Q1P1',**opts,resume=True)
    assert len(calls)==5 and pce_recovery.hashes(root/'review')==before
    assert 'accepted;' in account_review.apply(c,'Q1P1',**opts,resume=True) and len(calls)==5


def test_preflight_cannot_relabel_served_review(tmp_path,monkeypatch):
    c,root,candidate,args=failed(tmp_path,monkeypatch);before=pce_recovery.hashes(root)
    with pytest.raises(pce.Changed,match='untouched prepared'):
        account_review.apply(c,'Q1P1',**args,before_first_call=True)
    assert pce_recovery.hashes(root)==before


def test_pending_successor_clean_grant_preserves_predecessor(tmp_path,monkeypatch):
    from test_account_successor import ready
    from pathfinder import account_successor
    c,ed,parent,pd,args=ready(tmp_path,monkeypatch)
    calls=script(monkeypatch,c);pointer=(ed/'account-amendment.json').read_bytes();before=pce_recovery.hashes(parent)
    assert 'no calls' in account_successor.run(c,'Q1P1',**args)
    root=ed/'account-amendments/withdrawal';opts=clean_packet(tmp_path,root,'withdrawal')
    assert 'no calls' in account_review.apply(c,'Q1P1',**opts)
    assert (ed/'account-amendment.json').read_bytes()==pointer
    with pytest.raises(pce.Changed,match='explicit account evidence'):
        account_successor.run(c,'Q1P1',**args,apply=True)
    assert not calls
    assert 'accepted;' in account_review.apply(c,'Q1P1',**opts,resume=True)
    assert len(calls)==5 and pce_recovery.hashes(parent)==before
    assert json.loads((ed/'account-amendment.json').read_text())=={'id':'withdrawal'}
    account_release.view(c,'Q1P1',create=True)
    assert 'accepted;' in account_review.apply(c,'Q1P1',**opts,resume=True) and len(calls)==5
