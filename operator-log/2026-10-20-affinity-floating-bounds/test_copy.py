"""Offline copied successor and full actual-report transport proof."""
import importlib.util
import json
import shutil
from pathlib import Path
import pytest
from pathfinder import account_successor, pce, pce_recovery, editor_packet
from test_pce import script

ROOT=Path('/Users/v/Code_2026/pathfinder')
HERE=Path(__file__).resolve().parent
PACK=HERE/'Q053-P011'
RUNTIME=Path('/private/tmp/pathfinder-selector-11efb02')
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
IDENTITY='floating-bound-definition-20261020'


def copied(tmp_path,monkeypatch):
    assert Path(pce.__file__).resolve().is_relative_to(RUNTIME)
    c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q053-P011','feature-record-specifications-20261020')
    delta=json.loads((PACK/'successor.json').read_text())
    for row in delta['evidence_projection']['include']:
        target=t/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(helper.BASE/'threads/Q053-P011'/row['path'],target)
    args=dict(identity=IDENTITY,packet=PACK,reason='Offline P1 floating-bound definition successor test')
    return c,t,args


def test_canonical_preparation_refuses_without_writes(tmp_path,monkeypatch):
    c,t,args=copied(tmp_path,monkeypatch)
    before=pce_recovery.hashes(t);calls=script(monkeypatch,c)
    with pytest.raises(pce.Changed,match='complete successor evidence exceeds prompt allowance'):
        account_successor.run(c,'Q053-P011',**args)
    assert not calls and pce_recovery.hashes(t)==before
    print('Ordinary preparation guard refuses before writes/calls; all copied files preserved')


def test_candidate_real_build(tmp_path):
    from pathfinder import paper
    (tmp_path/'paper.tex').write_bytes((PACK/'account-candidate.tex').read_bytes())
    parent=helper.BASE/'threads/Q053-P011/edited/account-amendments/feature-record-specifications-20261020'
    for f in (parent/'build').glob('*.bib'):
        shutil.copyfile(f,tmp_path/f.name)
    ok,log=paper.build(tmp_path)
    assert ok,log
    assert (tmp_path/'paper.pdf').exists()


def test_lossless_measurement_without_preparation(monkeypatch):
    import runpy
    from pathfinder import editor_blocks
    # Restore the process-local prototype eligibility change after the experiment.
    monkeypatch.setattr(editor_blocks,'_eligible',editor_blocks._eligible)
    monkeypatch.setattr(pce,'_dispatch',lambda *a,**kw:pytest.fail('No role dispatch in sizing'))
    runpy.run_path(str(HERE/'measure_capacity.py'),run_name='__main__')
    result=json.loads((HERE/'capacity-prototype.json').read_text())
    assert result['old_editor_span_chars']==1007886
    assert result['new_editor_span_chars']==1000161
    assert result['raw_wire_plus_unchanged_reserve']==958220
    assert result['reserve']==100000 and result['cap']==1000000


def test_exact_scope_and_bindings():
    import hashlib
    for name,digest in json.loads((HERE/'bindings.json').read_text()).items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    delta=json.loads((PACK/'successor.json').read_text());candidate=(PACK/'account-candidate.tex').read_text()
    assert len(delta['changes'])==1
    ch=delta['changes'][0]
    assert ch['finding']=='P1' and candidate.count(ch['after'])==1
    assert pce._sha(candidate.replace(ch['after'],ch['before'],1))==delta['parent_candidate_sha256']
    assert 'not a spread across preparations' in ch['after']
    assert 'not to the distinct joint polar/v2 preparation ranges' in ch['after']
