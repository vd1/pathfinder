import importlib.util,json,shutil
import pytest
from pathlib import Path
from pathfinder import account_successor,account_release,pce,pce_recovery,paper
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_allocation_successor_after_accepted_child(tmp_path,monkeypatch):
    base=helper.BASE;pair='Q024-P022'
    c,dt=helper.copied(tmp_path,monkeypatch,base,pair,'allocation-domain-20261020','aggregate-validation-1')
    delta=json.loads((ROOT/'operator-log/2026-10-20-allocation-definitions/Q024-P022/successor.json').read_text())
    for row in delta['evidence_projection']['include']:
        dst=dt/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(base/'threads'/pair/row['path'],dst)
    before=pce_recovery.hashes(dt/'edited');science=(dt/'status.json').read_bytes();calls=script(monkeypatch,c)
    args=dict(identity='allocation-definitions-20261020',packet=ROOT/'operator-log/2026-10-20-allocation-definitions/Q024-P022',reason='Private copied P1 P2 P3 definition validation')
    assert 'no calls' in account_successor.run(c,pair,**args)
    root=dt/'edited/account-amendments'/args['identity'];parent=dt/'edited/account-amendments/allocation-domain-20261020/revisions/aggregate-validation-1'
    old=json.loads((parent/'review/frozen-inputs.json').read_text());new=json.loads((root/'review/frozen-inputs.json').read_text())
    assert all(new[n]==s for n,s in old.items() if n.startswith('sources/external/') and n!=pce.SUPPLEMENT)
    assert new[pce.SUPPLEMENT].startswith(old[pce.SUPPLEMENT])
    extra=json.loads(new[pce.SUPPLEMENT].split('## Additional retained scientific files\n\n')[1])
    assert extra=={r['path']:(dt/r['path']).read_text() for r in delta['evidence_projection']['include']}
    assert (dt/'edited/account-amendment.json').read_text().find('aggregate-validation-1')>=0
    assert 'accepted;' in account_successor.run(c,pair,**args,apply=True);assert len(calls)==5
    for call in calls:
        if call['role']=='archivist':continue
        shown=json.loads(call['prompt'].split('Allowed input files:\n',1)[1]);assert shown[pce.SUPPLEMENT]==new[pce.SUPPLEMENT]
    print('role chars', [len(x['prompt']) for x in calls])
    after=pce_recovery.hashes(dt/'edited');assert all(after[n]==h for n,h in before.items() if n not in ('account-amendment.json','account-successor.json'))
    assert (dt/'status.json').read_bytes()==science
    assert (root/'build/paper.pdf').exists()
    assert 'accepted;' in account_successor.run(c,pair,**args,apply=True) and len(calls)==5
    view=account_release.view(c,pair,create=True);assert (paper.folder(view,pair)/'paper.tex').read_text()==(root/'candidate.tex').read_text()
    print('Q024-P022: five stub roles, real build; preserved prior files',len(before),'and scientific status; inherited external evidence preserved with four exact additions')

@pytest.mark.parametrize('bad',['hash','escape','exclusion','partial'])
def test_evidence_rejection(tmp_path,monkeypatch,bad):
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q024-P022','allocation-domain-20261020','aggregate-validation-1')
    packet=tmp_path/'packet';shutil.copytree(ROOT/'operator-log/2026-10-20-allocation-definitions/Q024-P022',packet)
    d=json.loads((packet/'successor.json').read_text())
    for row in d['evidence_projection']['include']:
        dst=t/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(helper.BASE/'threads/Q024-P022'/row['path'],dst)
    if bad=='hash':d['evidence_projection']['include'][0]['sha256']='0'*64
    if bad=='escape':d['evidence_projection']['include'][0]['path']='../other.py'
    if bad=='exclusion':d['evidence_projection']['exclude']=[{}]
    if bad=='partial':d['evidence_projection']['include'][0]['json_fields']=['scope']
    (packet/'successor.json').write_text(json.dumps(d));before=pce_recovery.hashes(t)
    with pytest.raises(pce.Changed):account_successor.run(c,'Q024-P022',identity='allocation-definitions-20261020',packet=packet,reason='copy rejection test')
    assert pce_recovery.hashes(t)==before
