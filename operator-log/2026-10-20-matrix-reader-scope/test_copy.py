import importlib.util,json,re,hashlib
from pathlib import Path
from pathfinder import account_revision,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
PACKET=ROOT/'operator-log/2026-10-20-matrix-reader-scope/Q010-P072'

def test_pending_successor_reader_child(tmp_path,monkeypatch):
    base=helper.BASE.parent/'campaign-2-batch-1/Q010-P072';pair='Q010-P072';identity='matrix-control-definition-20261020'
    c,dt=helper.copied(tmp_path,monkeypatch,base,pair,identity)
    before=pce_recovery.hashes(dt/'edited');science=(dt/'status.json').read_bytes();pointer=(dt/'edited/account-amendment.json').read_bytes()
    parent=dt/'edited/account-amendments'/identity;candidate=(parent/'candidate.tex').read_text()
    new=(PACKET/'account-candidate.tex').read_text();delta=json.loads((PACKET/'revision.json').read_text())
    assert hashlib.sha256(candidate.encode()).hexdigest()==delta['parent_candidate_sha256']
    transformed=candidate
    for row in delta['changes']:
        assert transformed.count(row['before'])==1
        transformed=transformed.replace(row['before'],row['after'],1)
    assert transformed==new
    assert candidate.split('\\appendix')[1]==new.split('\\appendix')[1]
    assert re.findall(r'\$[^$]*\$|\\begin\{(?:equation\*|align\*)\}.*?\\end\{(?:equation\*|align\*)\}',candidate,re.S)==re.findall(r'\$[^$]*\$|\\begin\{(?:equation\*|align\*)\}.*?\\end\{(?:equation\*|align\*)\}',new,re.S)
    calls=script(monkeypatch,c)
    args=dict(identity=identity,revision='reader-scope-1',packet=PACKET,reason='Private copied pending successor reader-scope test')
    assert 'no calls' in account_revision.run(c,pair,**args)
    assert (dt/'edited/account-amendment.json').read_bytes()==pointer
    child=parent/'revisions/reader-scope-1'
    old=json.loads((parent/'review/frozen-inputs.json').read_text());fresh=json.loads((child/'review/frozen-inputs.json').read_text())
    assert all(fresh[n]==v for n,v in old.items() if n.startswith('sources/external/'))
    assert 'accepted;' in account_revision.run(c,pair,**args,apply=True)
    assert len(calls)==5 and (child/'build/paper.pdf').exists()
    after=pce_recovery.hashes(dt/'edited')
    assert all(after[n]==v for n,v in before.items() if n not in ('account-amendment.json','account-successor.json'))
    assert (dt/'status.json').read_bytes()==science
    assert json.loads((dt/'edited/account-amendment.json').read_text())=={'id':identity,'revision':'reader-scope-1'}
    print('Five stub roles + real build; preserved',len(before),'prior files except engine pointers; science, equations, matrix definitions, appendix and external projection exact')
