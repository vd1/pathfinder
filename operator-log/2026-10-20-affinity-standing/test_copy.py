import importlib.util,json
from pathlib import Path
from pathfinder import account_revision,account_review,pce,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-affinity-standing'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_latest_clean_grant_child(tmp_path,monkeypatch):
    assert Path(account_revision.__file__).resolve().is_relative_to(Path("/private/tmp/pathfinder-clean-c12d7c8"))
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q053-P011','preparation-spec-20261020')
    parent=t/'edited/account-amendments/preparation-spec-20261020/revisions/affinity-cycle-definitions-1'
    previous=account_review.workflow(parent);assert previous.name=='clean-scientific-inputs-1'
    files=json.loads((previous/'frozen-inputs.json').read_text());assert len(json.loads(files[pce.SUPPLEMENT])['files'])==14
    before=pce_recovery.hashes(t/'edited');science=(t/'status.json').read_bytes();calls=script(monkeypatch,c)
    args=dict(identity='preparation-spec-20261020',revision='control-standing-1',packet=PACK/'Q053-P011',reason='Private copied latest-clean-grant child')
    assert 'no calls' in account_revision.run(c,'Q053-P011',**args)
    root=parent.parent/'control-standing-1';new=json.loads((root/'review/frozen-inputs.json').read_text())
    assert {k:v for k,v in files.items() if k.startswith('sources/external/')}=={k:v for k,v in new.items() if k.startswith('sources/external/')}
    assert 'accepted;' in account_revision.run(c,'Q053-P011',**args,apply=True);assert len(calls)==5
    assert (root/'build/paper.pdf').exists() and (t/'status.json').read_bytes()==science
    after=pce_recovery.hashes(t/'edited');assert all(after[n]==h for n,h in before.items() if n!='account-amendment.json')
    print('5 stub roles + real build; fourteen clean files exact; preserved',len(before),'previous edited files')


def test_only_unsupported_status_word_removed():
    import hashlib
    packet=PACK/'Q053-P011';delta=json.loads((packet/'revision.json').read_text())
    assert delta['changes']==[{'finding':'reader-control-standing','before':'Supporting unadopted branch-1 controls','after':'Supporting branch-1 controls'}]
    current=(packet/'account-candidate.tex').read_text()
    assert current.count('Supporting branch-1 controls')==1
    original=current.replace('Supporting branch-1 controls','Supporting unadopted branch-1 controls')
    assert hashlib.sha256(original.encode()).hexdigest()==delta['parent_candidate_sha256']
    assert 'These conditional examples are not observed thrombin mechanisms and do not identify cliques with physical microstates.' in current
