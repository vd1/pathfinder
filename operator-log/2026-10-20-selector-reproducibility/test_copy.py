import importlib.util,json
from pathlib import Path
from pathfinder import account_revision,account_review,pce,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-selector-reproducibility'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_latest_clean_grant_child(tmp_path,monkeypatch):
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q010-P030','selector-definitions-20261020')
    parent=t/'edited/account-amendments/selector-definitions-20261020/revisions/comparison-scope-1'
    previous=account_review.workflow(parent);assert previous.name=='complete-evidence-1'
    files=json.loads((previous/'frozen-inputs.json').read_text());assert len(json.loads(files[pce.SUPPLEMENT])['files'])==11
    before=pce_recovery.hashes(t/'edited');science=(t/'status.json').read_bytes();calls=script(monkeypatch,c)
    args=dict(identity='selector-definitions-20261020',revision='reproducibility-definitions-1',packet=PACK/'Q010-P030',reason='Private copied latest-clean-grant child')
    assert 'no calls' in account_revision.run(c,'Q010-P030',**args)
    root=parent.parent/'reproducibility-definitions-1';new=json.loads((root/'review/frozen-inputs.json').read_text())
    assert {k:v for k,v in files.items() if k.startswith('sources/external/')}=={k:v for k,v in new.items() if k.startswith('sources/external/')}
    assert 'accepted;' in account_revision.run(c,'Q010-P030',**args,apply=True);assert len(calls)==5
    assert (root/'build/paper.pdf').exists() and (t/'status.json').read_bytes()==science
    after=pce_recovery.hashes(t/'edited');assert all(after[n]==h for n,h in before.items() if n!='account-amendment.json')
    print('5 stub roles + real build; eleven clean files exact; preserved',len(before),'previous edited files')
