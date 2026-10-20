import importlib.util,json,hashlib
from pathlib import Path
from pathfinder import account_successor,pce_recovery,pce
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-affinity-record-specifications'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def test_copy(tmp_path,monkeypatch):
 assert Path(pce.__file__).resolve().is_relative_to(Path('/private/tmp/pathfinder-editor-982b7ff'))
 c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q053-P011','scalar-allowance-definition-20261020')
 before=pce_recovery.hashes(t/'edited');science=(t/'status.json').read_bytes();calls=script(monkeypatch,c)
 args=dict(identity='feature-record-specifications-20261020',packet=PACK/'Q053-P011',reason='Offline exact P1 record-reference successor test')
 assert 'no calls' in account_successor.run(c,'Q053-P011',**args)
 root=t/'edited/account-amendments'/args['identity'];old=t/'edited/account-amendments/scalar-allowance-definition-20261020/review'
 source=json.loads((old/'frozen-inputs.json').read_text());target=json.loads((root/'review/frozen-inputs.json').read_text())
 assert {k:v for k,v in source.items() if k.startswith('sources/external/')}=={k:v for k,v in target.items() if k.startswith('sources/external/')}
 assert 'accepted;' in account_successor.run(c,'Q053-P011',**args,apply=True)
 assert len(calls)==5 and (root/'build/paper.pdf').exists()
 after=pce_recovery.hashes(t/'edited');assert all(after[k]==v for k,v in before.items() if k not in ('account-successor.json','account-amendment.json'))
 assert science==(t/'status.json').read_bytes()
 print('Preserved',len(before),'prior edited files; full external mapping identical; five stub roles + real build')
def test_scope():
 p=PACK/'Q053-P011';d=json.loads((p/'successor.json').read_text());s=(p/'account-candidate.tex').read_text();assert len(d['changes'])==1
 ch=d['changes'][0];assert ch['finding']=='P1' and s.count(ch['after'])==1
 assert hashlib.sha256(s.replace(ch['after'],ch['before']).encode()).hexdigest()==d['parent_candidate_sha256']
 assert 'no unique tie-broken optimum witness is claimed' in ch['after']
 assert 'not the preceding' in ch['after']
