import importlib.util,json
from pathlib import Path
from pathfinder import account_successor,account_release,pce,pce_recovery,paper
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_matrix_successor_after_accepted_child(tmp_path,monkeypatch):
    base=helper.BASE.parent/'campaign-2-batch-1/Q010-P072';pair='Q010-P072'
    c,dt=helper.copied(tmp_path,monkeypatch,base,pair,'shot-budget-withdrawal-20261020','definitions-1')
    before=pce_recovery.hashes(dt/'edited');science=(dt/'status.json').read_bytes();calls=script(monkeypatch,c)
    args=dict(identity='matrix-control-definition-20261020',packet=ROOT/'operator-log/2026-10-20-matrix-control/Q010-P072',reason='Private copied matrix descriptor and scale validation')
    assert 'no calls' in account_successor.run(c,pair,**args)
    root=dt/'edited/account-amendments'/args['identity'];parent=dt/'edited/account-amendments/shot-budget-withdrawal-20261020/revisions/definitions-1'
    old=json.loads((parent/'review-grants/final-candidate-register-v1/frozen-inputs.json').read_text());new=json.loads((root/'review/frozen-inputs.json').read_text())
    assert all(new[n]==s for n,s in old.items() if n.startswith('sources/external/'))
    assert (dt/'edited/account-amendment.json').read_text().find('definitions-1')>=0
    assert 'accepted;' in account_successor.run(c,pair,**args,apply=True);assert len(calls)==5
    after=pce_recovery.hashes(dt/'edited');assert all(after[n]==h for n,h in before.items() if n not in ('account-amendment.json','account-successor.json'))
    assert (dt/'status.json').read_bytes()==science
    assert (root/'build/paper.pdf').exists()
    assert 'accepted;' in account_successor.run(c,pair,**args,apply=True) and len(calls)==5
    view=account_release.view(c,pair,create=True);assert (paper.folder(view,pair)/'paper.tex').read_text()==(root/'candidate.tex').read_text()
    print('Q010-P072: five stub roles, real build; preserved prior files',len(before),'and scientific status; external sources unchanged')
