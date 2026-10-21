"""Same pending identity, actual stopped round; all dispatches are stubbed on private copies."""
import importlib.util,json,os,shutil
from pathlib import Path
import pytest
from pathfinder import account_revision as ar,account_exception as ex,pce,pce_recovery
from test_pce import script
HERE=Path(__file__).resolve().parent
REPO=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('copy_helper',REPO/'operator-log/2026-10-20-final-register/test_copy.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
ID='ideal-control-definition-20261021';REV='scalar-convention-1'

def setup(tmp_path,monkeypatch):
    assert Path(pce.__file__).resolve().is_relative_to(os.environ.get('PATHFINDER_TEST_RUNTIME',str(REPO)))
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q010-P030',ID)
    for name in ('ada/adapt_qsci/build.py','ada/adapt_qsci/result.json'):
        dst=t/name;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(helper.BASE/'threads/Q010-P030'/name,dst)
    packet=tmp_path/'packet';shutil.copytree(HERE/'Q010-P030',packet)
    contract=json.loads((packet/'revision-exception.json').read_text())
    approval=tmp_path/'TEST-ONLY-approval.json'
    approval.write_text(pce._json(dict(version=1,decision='approve',authority='owner',approved_by='OFFLINE TEST ONLY',approval_reference='No live authority; copied fixture',contract_sha256=ex.digest(contract))))
    return c,t,dict(identity=ID,revision=REV,packet=packet,reason='Offline copied test only',approval=approval)


def test_five_roles_real_build_and_history(tmp_path,monkeypatch):
    c,t,args=setup(tmp_path,monkeypatch);parent=t/'edited/account-amendments'/ID
    before=pce_recovery.hashes(t/'edited');science=(t/'status.json').read_bytes()
    selected=(t/'edited/account-amendment.json').read_bytes()
    old=json.loads((parent/'review/frozen-inputs.json').read_text())
    calls=script(monkeypatch,c)
    assert 'no calls' in ar.run(c,'Q010-P030',**args)
    assert (t/'edited/account-amendment.json').read_bytes()==selected and not calls
    root=parent/'revisions'/REV
    new=json.loads((root/'review/frozen-inputs.json').read_text())
    assert all(new[n]==v for n,v in old.items() if n.startswith('sources/external/'))
    added=set(new)-set(old);assert len(added)==1
    key=next(iter(added));assert key.startswith('sources/external/amendment-retained-')
    assert (t/'ada/adapt_qsci/build.py').read_text() in new[key]
    oldrows=json.loads((parent/'request.json').read_text())['changes']['changes']
    rows=json.loads((root/'request.json').read_text())['changes']['changes']
    assert r'\(w_0\)' in rows[24]['after'] and r'u_0' not in rows[24]['after']
    assert r'E_s^{\mathrm{sel}}' in rows[24]['after']
    assert r'E_1-E_0' not in rows[24]['after']
    assert rows[:24]==oldrows and len(rows)==26
    assert 'accepted;' in ar.run(c,'Q010-P030',**args,apply=True)
    assert [x['role'] for x in calls]==['author','archivist','fact-checker','critic','editor']
    assert all('OFFLINE TEST ONLY' not in x['prompt'] for x in calls)
    assert (root/'build/paper.pdf').exists() and (t/'status.json').read_bytes()==science
    after=pce_recovery.hashes(t/'edited')
    assert all(after[n]==h for n,h in before.items() if n not in ('account-amendment.json','account-successor.json'))
    assert json.loads((t/'edited/account-amendment.json').read_text())==dict(id=ID,revision=REV)
    assert 'accepted;' in ar.run(c,'Q010-P030',**args,apply=True) and len(calls)==5
    grant=json.loads((root/'review/grant.json').read_text())
    assert grant['settings']['passes']==grant['settings']['fact_checks']==1
    assert grant['strict_evidence'] and 'pass_score' not in grant['settings']['critic']
    (HERE/'verification.json').write_text(pce._json(dict(old_edited_files=len(before),old_files_preserved_except_canonical_pointers=True,science_unchanged=True,old_records=24,total_records=26,real_build=True,roles=[x['role'] for x in calls],old_external={n:pce._sha(v) for n,v in old.items() if n.startswith('sources/external/')},new_source=key,prep_chars=len(pce._json(new)),reserve=100000,cap=1000000)))


@pytest.mark.parametrize('damage',['no-approval','wrong-approval','27','old-record','extra-edit','changed-selected','failed-round','review-quote','old-source','new-source'])
def test_invalid_no_calls_or_writes(tmp_path,monkeypatch,damage):
    c,t,args=setup(tmp_path,monkeypatch);pk=args['packet'];parent=t/'edited/account-amendments'/ID
    if damage=='no-approval':args.pop('approval')
    elif damage=='wrong-approval':
        d=json.loads(args['approval'].read_text());d['contract_sha256']='old24approval';args['approval'].write_text(pce._json(d))
    elif damage=='27':
        f=pk/'revision-exception.json';d=json.loads(f.read_text());d['total_count']=27;f.write_text(pce._json(d))
    elif damage=='old-record':
        f=pk/'changes.json';d=json.loads(f.read_text());d['changes'][0]['after']+=' altered';f.write_text(pce._json(d))
    elif damage=='extra-edit':
        with (pk/'account-candidate.tex').open('a') as f:f.write('\nundeclared')
    elif damage=='changed-selected':(t/'edited/account-amendment.json').write_text('{"id":"other"}')
    elif damage=='failed-round':(parent/'review/result.json').write_text('{"status":"accepted"}')
    elif damage=='review-quote':
        with (parent/'review/reviews/current/critic-computational-chemist.md').open('a') as f:f.write('changed')
    elif damage=='old-source':
        with (t/'ada/adapt_qsci/result.json').open('a') as f:f.write(' ')
    else:
        with (t/'ada/adapt_qsci/build.py').open('a') as f:f.write('#changed')
    before=pce_recovery.hashes(t);monkeypatch.setattr(pce,'run',lambda *a,**kw:pytest.fail('dispatch'))
    with pytest.raises((pce.Changed,FileNotFoundError)):ar.run(c,'Q010-P030',**args,apply=True)
    assert pce_recovery.hashes(t)==before


def test_ordinary_guard_and_no_silent_merge(tmp_path,monkeypatch):
    c,t,args=setup(tmp_path,monkeypatch)
    (args['packet']/'revision-exception.json').unlink();args.pop('approval')
    before=pce_recovery.hashes(t)
    with pytest.raises(pce.Changed):ar.run(c,'Q010-P030',**args)
    assert pce_recovery.hashes(t)==before


@pytest.mark.parametrize('growth',[0,8192,32768])
def test_actual_report_profile(tmp_path,monkeypatch,growth):
    c,t,args=setup(tmp_path,monkeypatch);parent=t/'edited/account-amendments'/ID/'review'
    calls=script(monkeypatch,c);visible=pce.visible;paths=[]
    def actual(files,contract):
        shown=visible(files,contract)
        if contract.startswith('# Editor\n'):
            for name in list(shown):
                if name.startswith(('claims/','reviews/','revisions/')) and not name.endswith('.tex'):
                    assert (parent/name).is_file(),name
                    shown[name]=(parent/name).read_text();paths.append(name)
            if growth:shown['reviews/current/critic-computational-chemist.md']+='\n'+'X'*growth
        return shown
    monkeypatch.setattr(pce,'visible',actual);dispatch=pce._dispatch
    class Measured(Exception):pass
    def measure(c,pair,role,prompt,**kwargs):
        if role!='editor':return dispatch(c,pair,role,prompt,**kwargs)
        root=parent.parent/'revisions'/REV/'review'
        vis=json.loads((root/'visibility/pass-01-editor.json').read_text())
        assert len(prompt)==vis['prompt_chars']<=1000000 and not vis['truncated']
        assert len(json.loads((parent/'claims/current.json').read_text()))>=142
        assert any('evidence-diff' in n for n in paths)
        frozen=json.loads((root/'frozen-inputs.json').read_text())
        assert all(vis['files_sha256'][k]==pce._sha(v) for k,v in frozen.items() if k.startswith('sources/external/'))
        (HERE/f'actual-profile-{growth}.json').write_text(pce._json(dict(prompt_chars=len(prompt),headroom=1000000-len(prompt),growth=growth,actual_report_paths=paths,visibility=vis,purpose='Offline full actual142claim plus archivist profile; not fresh judgments.')))
        raise Measured
    monkeypatch.setattr(pce,'_dispatch',measure)
    with pytest.raises(Measured):ar.run(c,'Q010-P030',**args,apply=True)
    assert len(calls)==4


def test_visibility_scope_is_not_a_fabricated_critic_finding(tmp_path,monkeypatch):
    c,t,args=setup(tmp_path,monkeypatch);pk=args['packet']
    d=json.loads((pk/'revision.json').read_text())
    assert len(d['findings'])==1 and d['findings'][0]['id']=='scalar-convention'
    assert d['operator_evidence_visibility']['change']==d['changes'][1]
    assert d['changes'][1]['after']==d['changes'][1]['before']+d['operator_evidence_visibility']['append']
    d['operator_evidence_visibility']['change']['after']='unbound rewrite'
    (pk/'revision.json').write_text(pce._json(d))
    contract=json.loads((pk/'revision-exception.json').read_text());contract['delta_sha256']=ex.digest(d)
    (pk/'revision-exception.json').write_text(pce._json(contract))
    receipt=json.loads(args['approval'].read_text());receipt['contract_sha256']=ex.digest(contract)
    args['approval'].write_text(pce._json(receipt))
    before=pce_recovery.hashes(t)
    with pytest.raises(pce.Changed):ar.run(c,'Q010-P030',**args)
    assert pce_recovery.hashes(t)==before


def test_failed_fresh_round_preserves_selection_and_does_not_renew(tmp_path,monkeypatch):
    c,t,args=setup(tmp_path,monkeypatch);selected=(t/'edited/account-amendment.json').read_bytes()
    calls=script(monkeypatch,c,critic=['revise'])
    assert 'review_required' in ar.run(c,'Q010-P030',**args,apply=True)
    assert len(calls)==4 and (t/'edited/account-amendment.json').read_bytes()==selected
    assert 'review_required' in ar.run(c,'Q010-P030',**args,apply=True) and len(calls)==4


def test_resume_rechecks_operator_visibility_record(tmp_path,monkeypatch):
    c,t,args=setup(tmp_path,monkeypatch)
    ar.run(c,'Q010-P030',**args)
    path=t/'edited/account-amendments'/ID/'revisions'/REV/'operator-evidence-visibility.json'
    path.write_text('{}');before=pce_recovery.hashes(t)
    monkeypatch.setattr(pce,'run',lambda *a,**kw:pytest.fail('dispatch'))
    with pytest.raises(pce.Changed,match='visibility scope changed'):ar.run(c,'Q010-P030',**args,apply=True)
    assert pce_recovery.hashes(t)==before
