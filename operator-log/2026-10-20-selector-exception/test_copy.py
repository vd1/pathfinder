"""Private-copy proof only. Approval fixtures are created only under pytest tmp_path."""
import importlib.util
import json
import os
import shutil
from pathlib import Path

import pytest
from pathfinder import account_exception as ex, account_successor, account_amend, pce, pce_recovery
from test_pce import script

ROOT = Path('/Users/v/Code_2026/pathfinder')
HERE = Path(__file__).resolve().parent
PACK = HERE / 'Q010-P030'
IDENTITY = 'pool-component-definition-20261020'
spec = importlib.util.spec_from_file_location('helper', ROOT/'operator-log/2026-10-20-final-register/test_copy.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)


def setup(tmp_path, monkeypatch):
    assert Path(pce.__file__).resolve().is_relative_to(Path(os.environ.get('PATHFINDER_TEST_RUNTIME', str(ROOT))))
    c, t = helper.copied(tmp_path, monkeypatch, helper.BASE, 'Q010-P030',
                         'selector-definitions-20261020', 'model-decision-1')
    live = helper.BASE/'threads/Q010-P030'
    source = 'ada/adapt_qsci/result.json'
    (t/source).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(live/source, t/source)
    packet = tmp_path/'packet'; shutil.copytree(PACK, packet)
    contract = json.loads((packet/'history-exception.json').read_text())
    approval = tmp_path/'TEST-ONLY-owner-approval.json'
    approval.write_text(pce._json({'version':1,'decision':'approve','authority':'owner',
        'approved_by':'OFFLINE TEST FIXTURE ONLY','approval_reference':'Private copied test, no live authority',
        'contract_sha256':ex.digest(contract)}))
    args = dict(identity=IDENTITY, packet=packet, approval=approval,
                reason='Offline copied test only; no live owner approval')
    return c,t,args


def test_five_roles_real_build_preservation(tmp_path, monkeypatch):
    c,t,args = setup(tmp_path, monkeypatch)
    before = pce_recovery.hashes(t/'edited'); science=(t/'status.json').read_bytes()
    parent=t/'edited/account-amendments/selector-definitions-20261020/revisions/model-decision-1'
    prior=json.loads((parent/'review/frozen-inputs.json').read_text())
    calls=script(monkeypatch,c)
    assert 'no calls' in account_successor.run(c,'Q010-P030',**args)
    root=t/'edited/account-amendments'/IDENTITY
    frozen=json.loads((root/'review/frozen-inputs.json').read_text())
    selected=[k for k in frozen if k.startswith('sources/external/selected-json-')]
    assert len(selected)==1
    assert all(frozen[k]==v for k,v in prior.items() if k.startswith('sources/external/'))
    assert 'omitted_subtrees' not in frozen[selected[0]]
    assert not any('approval' in k or 'omissions' in k for k in frozen)
    assert 'accepted;' in account_successor.run(c,'Q010-P030',**args,apply=True)
    assert [x['role'] for x in calls]==['author','archivist','fact-checker','critic','editor']
    for call in calls:
        if call['role'] != 'archivist':
            assert 'selected-json-' in call['prompt']
        assert 'OFFLINE TEST FIXTURE' not in call['prompt']
    grant=json.loads((root/'review/grant.json').read_text())
    assert grant['settings']['passes']==grant['settings']['fact_checks']==1
    assert 'pass_score' not in grant['settings']['critic']
    assert len(json.loads((root/'request.json').read_text())['changes']['changes'])==23
    assert (root/'build/paper.pdf').exists()
    assert (t/'status.json').read_bytes()==science
    after=pce_recovery.hashes(t/'edited')
    assert all(after[k]==v for k,v in before.items() if k!='account-amendment.json')
    assert 'accepted;' in account_successor.run(c,'Q010-P030',**args,apply=True)
    assert len(calls)==5
    print('Five stub roles, real build; preserved',len(before),'existing edited files and science status')


@pytest.mark.parametrize('damage', ['no-approval','wrong-approval','24','extra-edit','changed-parent',
                                  'failed-parent','selected-source','selected-pointer','old-external'])
def test_refusal_before_calls_or_writes(tmp_path,monkeypatch,damage):
    c,t,args=setup(tmp_path,monkeypatch)
    packet=args['packet']; contract=json.loads((packet/'history-exception.json').read_text())
    parent=t/'edited/account-amendments/selector-definitions-20261020/revisions/model-decision-1'
    if damage=='no-approval':args.pop('approval')
    elif damage=='wrong-approval':
        doc=json.loads(args['approval'].read_text());doc['contract_sha256']='0'*64
        args['approval'].write_text(pce._json(doc))
    elif damage=='24':
        contract['total_count']=24;(packet/'history-exception.json').write_text(pce._json(contract))
    elif damage=='extra-edit':
        with (packet/'account-candidate.tex').open('a') as f:f.write('\nUndeclared edit.')
    elif damage=='changed-parent':
        (t/'edited/account-amendment.json').write_text('{"id":"selector-definitions-20261020"}')
    elif damage=='failed-parent':
        (parent/'review/result.json').write_text('{"status":"review_required"}')
    elif damage=='selected-source':
        with (t/'ada/adapt_qsci/result.json').open('a') as f:f.write(' ')
    elif damage=='selected-pointer':
        contract['selected_json']['pointers'].append('/controls')
        (packet/'history-exception.json').write_text(pce._json(contract))
        approval=json.loads(args['approval'].read_text())
        approval['contract_sha256']=ex.digest(contract)
        args['approval'].write_text(pce._json(approval))
    else:
        f=parent/'review/frozen-inputs.json';data=json.loads(f.read_text())
        data[pce.SUPPLEMENT]+='\nchanged';f.write_text(pce._json(data))
    before=pce_recovery.hashes(t)
    monkeypatch.setattr(pce,'run',lambda *a,**kw:pytest.fail('must not dispatch'))
    with pytest.raises(pce.Changed):
        account_successor.run(c,'Q010-P030',**args,apply=True)
    assert pce_recovery.hashes(t)==before


def test_selected_source_rechecked_before_resume(tmp_path,monkeypatch):
    c,t,args=setup(tmp_path,monkeypatch)
    assert 'no calls' in account_successor.run(c,'Q010-P030',**args)
    with (t/'ada/adapt_qsci/result.json').open('a') as f:f.write(' ')
    calls=script(monkeypatch,c);before=pce_recovery.hashes(t)
    with pytest.raises(pce.Changed):account_successor.run(c,'Q010-P030',**args,apply=True)
    assert not calls and pce_recovery.hashes(t)==before


def test_failed_parent_cannot_be_authorized_even_with_rebound_test_hashes(tmp_path,monkeypatch):
    c,t,args=setup(tmp_path,monkeypatch)
    parent=t/'edited/account-amendments/selector-definitions-20261020/revisions/model-decision-1'
    # Adversarial private-copy fixture: even rehashing the enclosing test acceptance
    # and approving the altered contract cannot turn a failed review into a parent.
    (parent/'review/result.json').write_text('{"status":"review_required"}')
    record=json.loads((parent/'acceptance.json').read_text())
    record['files_sha256']=account_amend._hashes(parent)
    (parent/'acceptance.json').write_text(pce._json(record))
    delta=json.loads((args['packet']/'successor.json').read_text())
    delta['parent_acceptance_sha256']=pce._sha((parent/'acceptance.json').read_text())
    (args['packet']/'successor.json').write_text(pce._json(delta))
    contract=json.loads((args['packet']/'history-exception.json').read_text())
    contract['parent_acceptance_sha256']=delta['parent_acceptance_sha256']
    contract['delta_sha256']=ex.digest(delta)
    (args['packet']/'history-exception.json').write_text(pce._json(contract))
    receipt=json.loads(args['approval'].read_text());receipt['contract_sha256']=ex.digest(contract)
    args['approval'].write_text(pce._json(receipt))
    before=pce_recovery.hashes(t);calls=script(monkeypatch,c)
    with pytest.raises(pce.Changed,match='parent review is not accepted'):
        account_successor.run(c,'Q010-P030',**args,apply=True)
    assert not calls and pce_recovery.hashes(t)==before


def test_full_actual_editor_profile(tmp_path,monkeypatch):
    c,t,args=setup(tmp_path,monkeypatch)
    parent=t/'edited/account-amendments/selector-definitions-20261020/revisions/model-decision-1/review'
    live=helper.BASE/'threads/Q010-P030'
    live_before=pce_recovery.hashes(live/'edited')
    calls=script(monkeypatch,c)
    visible=pce.visible; actual_paths=[]

    def actual(files,contract):
        shown=visible(files,contract)
        if contract.startswith('# Editor\n'):
            for name in list(shown):
                if name.startswith(('claims/','reviews/','revisions/')) and not name.endswith('.tex'):
                    path=parent/name
                    assert path.is_file(), name
                    shown[name]=path.read_bytes().decode('utf-8')
                    actual_paths.append(name)
        return shown
    monkeypatch.setattr(pce,'visible',actual)
    dispatch=pce._dispatch
    class Measured(Exception):pass
    def measure(c,pair,role,prompt,**kw):
        if role!='editor':return dispatch(c,pair,role,prompt,**kw)
        root=t/'edited/account-amendments'/IDENTITY/'review'
        visibility=json.loads((root/'visibility/pass-01-editor.json').read_text())
        assert visibility['prompt_chars']==len(prompt)<1_000_000
        assert visibility['truncated'] is False
        assert visibility['encoding']=='whole-file-alias-v1'
        envelope=json.loads(prompt.split('Allowed input files:\n',1)[1])
        expanded={**envelope['contents'], **{
            name:envelope['contents'][target] for name,target in envelope['aliases'].items()}}
        assert {name:pce._sha(text) for name,text in expanded.items()}==visibility['files_sha256']
        frozen=json.loads((root/'frozen-inputs.json').read_text())
        assert all(expanded[name]==text for name,text in frozen.items()
                   if name.startswith('sources/external/'))
        assert any('evidence-diff' in p for p in actual_paths),actual_paths
        for name in actual_paths:
            assert visibility['files_sha256'][name]==pce._sha((parent/name).read_bytes().decode())
        assert len(json.loads((parent/'claims/current.json').read_text())) >= 130
        measurement={'purpose':'Offline sizing with ALL actual parent claims/review/revision reports, including archivist. Not fresh scientific judgements or a guarantee on future reports.',
                     'prompt_chars':len(prompt),'cap':1_000_000,'headroom':1_000_000-len(prompt),
                     'actual_report_paths':actual_paths,'visibility':visibility}
        (HERE/'actual-profile.json').write_text(pce._json(measurement))
        print('Actual complete report profile',len(prompt),'chars; headroom',1_000_000-len(prompt))
        raise Measured
    monkeypatch.setattr(pce,'_dispatch',measure)
    with pytest.raises(Measured):account_successor.run(c,'Q010-P030',**args,apply=True)
    assert len(calls)==4
    assert pce_recovery.hashes(live/'edited')==live_before
