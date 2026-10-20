import importlib.util,json
from pathlib import Path
from pathfinder import account_revision,account_review,pce,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-bundle-attained-limits'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_latest_clean_grant_child(tmp_path,monkeypatch):
    assert Path(account_revision.__file__).resolve().is_relative_to(Path("/private/tmp/pathfinder-clean-c12d7c8"))
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q053-P024','conditional-information-20261020')
    parent=t/'edited/account-amendments/conditional-information-20261020/revisions/bundle-definition-1'
    previous=account_review.workflow(parent);assert previous.name=='clean-scientific-inputs-1'
    files=json.loads((previous/'frozen-inputs.json').read_text());assert len(json.loads(files[pce.SUPPLEMENT])['files'])==9
    before=pce_recovery.hashes(t/'edited');science=(t/'status.json').read_bytes();calls=script(monkeypatch,c)
    args=dict(identity='conditional-information-20261020',revision='attained-limits-1',packet=PACK/'Q053-P024',reason='Private copied latest-clean-grant child')
    assert 'no calls' in account_revision.run(c,'Q053-P024',**args)
    root=parent.parent/'attained-limits-1';new=json.loads((root/'review/frozen-inputs.json').read_text())
    assert {k:v for k,v in files.items() if k.startswith('sources/external/')}=={k:v for k,v in new.items() if k.startswith('sources/external/')}
    assert 'accepted;' in account_revision.run(c,'Q053-P024',**args,apply=True);assert len(calls)==5
    assert (root/'build/paper.pdf').exists() and (t/'status.json').read_bytes()==science
    after=pce_recovery.hashes(t/'edited');assert all(after[n]==h for n,h in before.items() if n!='account-amendment.json')
    print('5 stub roles + real build; nine clean files exact; preserved',len(before),'previous edited files')



def test_retained_limits_and_exact_delta():
    import hashlib
    packet=PACK/'Q053-P024';delta=json.loads((packet/'revision.json').read_text());candidate=(packet/'account-candidate.tex').read_text()
    original=candidate
    for change in reversed(delta['changes']):
        assert original.count(change['after'])==1
        original=original.replace(change['after'],change['before'])
    assert hashlib.sha256(original.encode()).hexdigest()==delta['parent_candidate_sha256'] and len(delta['changes'])==2
    for phrase in ('not a rejection of that diagnostic','not Q Hessians','22U is not a Q ligand','not inferred Q timescales','Neither relaxation times nor the finite-window temporal correction follow from a static Hessian alone'):
        assert phrase in candidate
    context=json.loads((PACK/'retained-context.json').read_text())
    assert [e['seq'] for e in context['entries']]==[51,54,62,63,69]
    assert all(e['standing']=='current; not cited by the joint ledger' for e in context['entries'])
    assert len(context['embedded_sha256'])==9
