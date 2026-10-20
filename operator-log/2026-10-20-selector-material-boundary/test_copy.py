import importlib.util,json
from pathlib import Path
from pathfinder import account_revision,account_review,pce,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-selector-material-boundary'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_latest_clean_grant_child(tmp_path,monkeypatch):
    assert Path(account_revision.__file__).resolve().is_relative_to(Path('/private/tmp/pathfinder-clean-c12d7c8'))
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q010-P030','selector-definitions-20261020')
    parent=t/'edited/account-amendments/selector-definitions-20261020/revisions/reproducibility-definitions-1'
    previous=account_review.workflow(parent);assert previous.name=='review'
    files=json.loads((previous/'frozen-inputs.json').read_text());assert len(json.loads(files[pce.SUPPLEMENT])['files'])==11
    before=pce_recovery.hashes(t/'edited');science=(t/'status.json').read_bytes();calls=script(monkeypatch,c)
    args=dict(identity='selector-definitions-20261020',revision='material-boundary-1',packet=PACK/'Q010-P030',reason='Private copied latest-clean-grant child')
    assert 'no calls' in account_revision.run(c,'Q010-P030',**args)
    root=parent.parent/'material-boundary-1';new=json.loads((root/'review/frozen-inputs.json').read_text())
    assert {k:v for k,v in files.items() if k.startswith('sources/external/')}=={k:v for k,v in new.items() if k.startswith('sources/external/')}
    assert 'accepted;' in account_revision.run(c,'Q010-P030',**args,apply=True);assert len(calls)==5
    assert (root/'build/paper.pdf').exists() and (t/'status.json').read_bytes()==science
    after=pce_recovery.hashes(t/'edited');assert all(after[n]==h for n,h in before.items() if n!='account-amendment.json')
    print('5 stub roles + real build; eleven clean files exact; preserved',len(before),'previous edited files')


def test_scope_and_exact_evidence():
    import hashlib,re
    packet=PACK/'Q010-P030';delta=json.loads((packet/'revision.json').read_text())
    candidate=(packet/'account-candidate.tex').read_text()
    for d in reversed(delta['changes']):
        assert candidate.count(d['after'])==1
        candidate=candidate.replace(d['after'],d['before'])
    assert hashlib.sha256(candidate.encode()).hexdigest()==delta['parent_candidate_sha256']
    assert len(delta['changes'])==2
    context=json.loads((PACK/'retained-context.json').read_text())
    assert len(context['embedded_sha256'])==11
    assert not any(name.endswith(('parent.npz','H-active.npz','V-active.npz','build.py','build-result.json','selected-records.json','water-1926-input.json','summary.json','audit-result.json','stopping_accuracy_audit_result.json','finite_shot_result_audit_result.json')) for name in context['embedded_sha256'])
    assert 'ada/adapt_qsci/result.json' not in context['embedded_sha256']
    assert 'not whether those files exist elsewhere' in (packet/'account-candidate.tex').read_text()
