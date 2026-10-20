import importlib.util,json,shutil
from pathlib import Path
import pytest
from pathfinder import account_bibliography as ab,account_successor,account_release,pce,pce_recovery,paper
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-queries-metadata';SCI=ROOT/'operator-log/2026-10-20-common-error-residual/Q024-P022'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_after_genuine_successor_only(tmp_path,monkeypatch):
    assert Path(ab.__file__).resolve().is_relative_to(Path('/private/tmp/pathfinder-metadata-ddc73ee'))
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q024-P022','allocation-definitions-20261020','motivation-context-1')
    args=dict(identity='queries-publisher-title-20261020',packet=PACK,reason='Explicit copied operator metadata authority')
    before=pce_recovery.hashes(t)
    with pytest.raises(pce.Changed,match='another accepted source'):ab.run(c,'Q024-P022',**args)
    assert pce_recovery.hashes(t)==before
    delta=json.loads((SCI/'successor.json').read_text())
    for row in delta['evidence_projection']['include']:
        dst=t/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(helper.BASE/'threads/Q024-P022'/row['path'],dst)
    calls=script(monkeypatch,c)
    assert 'accepted;' in account_successor.run(c,'Q024-P022',identity='common-error-definition-20261020',packet=SCI,reason='Private successor setup',apply=True)
    assert len(calls)==5
    before=pce_recovery.hashes(t);science=(t/'status.json').read_bytes()
    assert 'no calls' in ab.run(c,'Q024-P022',**args)
    assert 'installed' in ab.run(c,'Q024-P022',**args,apply=True)
    assert len(calls)==5 and (t/'status.json').read_bytes()==science
    after=pce_recovery.hashes(t);assert all(after[n]==h for n,h in before.items())
    v=account_release.view(c,'Q024-P022');folder=paper.folder(v,'Q024-P022')
    assert (folder/'paper.tex').read_bytes()==(SCI/'account-candidate.tex').read_bytes()
    new=paper.bib_entries((folder/'references.bib').read_text());old=paper.bib_entries((t/'edited/references.bib').read_text())
    for key in old:
        for field,value in old[key].items():
            if key=='queries' and field in ('title','note'):continue
            assert new[key][field]==value
    built=t/'edited/bibliography-revisions'/args['identity']/'build/paper.pdf';assert built.exists()
    assert 'installed' in ab.run(c,'Q024-P022',**args,apply=True) and len(calls)==5
    print('Metadata zero calls, real build; preserved',len(before),'prior files after private successor setup')

@pytest.mark.parametrize('bad',['raw','export','title','identity','note'])
def test_rejects_unbound_publisher(bad):
    s=json.loads((PACK/'metadata.json').read_text());op=s['operations'][0];proof=json.loads((PACK/'publisher-export.json').read_text())
    bib=(helper.BASE/'threads/Q024-P022/edited/references.bib').read_text()
    if bad=='raw':proof['raw_response']+='changed'
    if bad=='export':proof['bibtex']=proof['bibtex'].replace('Experiments','Different')
    if bad=='title':op['quote']='Unsupported title'
    if bad=='identity':op['doi']='10.1/other'
    if bad=='note':op['old_note']='Not bound'
    with pytest.raises(pce.Changed):ab.transform(bib,[op],{'publisher':{'text':json.dumps(proof)}})
