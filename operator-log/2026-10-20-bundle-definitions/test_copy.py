import importlib.util
from pathlib import Path
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_bundle_definition_child(tmp_path,monkeypatch):
    helper.test_ready_child(tmp_path,monkeypatch,'Q053-P024','conditional-information-20261020','bundle-definition-1','2026-10-20-bundle-definitions')

def test_scope_and_retained_definitions():
    import json,hashlib
    packet=ROOT/'operator-log/2026-10-20-bundle-definitions/Q053-P024';delta=json.loads((packet/'revision.json').read_text());text=(packet/'account-candidate.tex').read_text();restored=text
    assert len(delta['changes'])==3
    for row in reversed(delta['changes']):
        assert restored.count(row['after'])==1;restored=restored.replace(row['after'],row['before'],1)
    assert hashlib.sha256(restored.encode()).hexdigest()==delta['parent_candidate_sha256']
    for phrase in ['Gaussian and are independent of each other', 'estimator, physical calibration procedure', 'quantitative rejection threshold were not selected', 'No validated correspondence', 'merely small conditional information does not imply', 'not fitted chemical-substitution effects']:assert phrase in text
    context=json.loads((packet.parent/'retained-context.json').read_text())
    assert 'projected into this space' in context['retained_bundle_source']['text']
    assert 'nonzero singular values' in context['retained_bundle_source']['text']
    assert 'sufficient condition' in context['fixed_space_quote']
