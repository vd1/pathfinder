import importlib.util,json
from pathlib import Path
import pytest
from pathfinder import account_bibliography as ab,account_release,pce,pce_recovery,paper,presentation,transport
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
PACKET=ROOT/'operator-log/2026-10-20-bibliography/Q027-P024'

def test_metadata_copy(tmp_path,monkeypatch):
    c,dt=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q027-P024','rank-norm-20261020')
    monkeypatch.setattr(transport,'execute',lambda *a,**k:pytest.fail('no model call permitted for metadata installation'))
    before=pce_recovery.hashes(dt);view=account_release.view(c,'Q027-P024');old=paper.folder(view,'Q027-P024')
    args=dict(identity='authoritative-metadata-20261020',packet=PACKET,reason='Private copied metadata validation')
    assert 'no calls' in ab.run(c,'Q027-P024',**args)
    assert 'installed' in ab.run(c,'Q027-P024',**args,apply=True)
    new=paper.folder(account_release.view(c,'Q027-P024'),'Q027-P024')
    assert new!=old
    assert (new/'paper.tex').read_bytes()==(old/'paper.tex').read_bytes()
    assert (new/'acceptance.json').read_bytes()==(old/'acceptance.json').read_bytes()
    entries=paper.bib_entries((new/'references.bib').read_text())
    assert entries['Q']['year']=='2026' and 'note' not in entries['Q']
    assert entries['Lindahl']['title'].startswith('Refinement of docked protein-ligand')
    assert (dt/'edited/bibliography-revisions'/args['identity']/'build/paper.pdf').exists()
    assert all(pce_recovery.hashes(dt)[n]==h for n,h in before.items())
    assert 'installed' in ab.run(c,'Q027-P024',**args,apply=True)
    assert not (new/'presentation/state.json').exists()
    # Check metadata and corrected bibliography are actually visible to the fresh checker.
    v=account_release.view(c,'Q027-P024');stage=presentation.folder(v,'Q027-P024')/'pass';stage.mkdir(parents=True)
    for name in ('paper.tex','references.bib'):(stage/name).write_bytes((new/name).read_bytes())
    seen=[]
    def call(*a,**kw):
        seen.append(a[4]);return {'text':json.dumps({'findings':[]})},{'stage':'present_check'}
    monkeypatch.setattr(presentation,'_call',call)
    monkeypatch.setattr(presentation,'_task',lambda *a:'check metadata')
    monkeypatch.setattr(transport,'request',lambda *a,**k:{})
    monkeypatch.setattr(presentation.contracts,'ensure',lambda c,req,r,s:({'findings':[]},r))
    presentation._check(v,'Q027-P024','pass',[],{})
    assert all('2026' in p and 'registry-year' in p and 'references.bib' in p for p in seen)
    print('Q027-P024 real build; zero installation calls; original files preserved',len(before))

def test_metadata_refuses_wrong_doi_and_year():
    spec=json.loads((PACKET/'metadata.json').read_text());e={k:{**v,'text':Path(v['path']).read_text()} for k,v in spec['evidence'].items()}
    old=helper.BASE/'threads/Q027-P024/edited/publication/afed8b9ee14bb9b2d92a7a4d3d54927ba83da4068900cb6545f2c17a3ae54c19/references.bib'
    ops=spec['operations'];ops[0]['doi']='10.1/wrong'
    with pytest.raises(pce.Changed):ab.transform(old.read_text(),ops,e)
