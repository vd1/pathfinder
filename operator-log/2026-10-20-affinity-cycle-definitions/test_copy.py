import importlib.util
from pathlib import Path
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_affinity_cycle_child(tmp_path,monkeypatch):
    helper.test_ready_child(tmp_path,monkeypatch,'Q053-P011','preparation-spec-20261020','affinity-cycle-definitions-1','2026-10-20-affinity-cycle-definitions')


def test_retained_order_sign_and_missing_covariance():
    import json,hashlib
    folder=ROOT/'operator-log/2026-10-20-affinity-cycle-definitions'
    candidate=(folder/'Q053-P011/account-candidate.tex').read_text()
    delta=json.loads((folder/'Q053-P011/revision.json').read_text())
    restored=candidate
    assert len(delta['changes'])==2
    for row in reversed(delta['changes']):
        assert restored.count(row['after'])==1
        restored=restored.replace(row['after'],row['before'],1)
    assert hashlib.sha256(restored.encode()).hexdigest()==delta['parent_candidate_sha256']
    assert r'z=(g_{5R},g_{5B},g_{3R},g_{3B})^T' in candidate
    assert r'C=g_{5R}-g_{5B}-g_{3R}+g_{3B}=c^Tz' in candidate
    assert r'c=(1,-1,-1,1)^T' in candidate
    assert 'retained Branch 1 covariance convention' in candidate
    assert 'The covariance was not recovered.' in candidate
    assert 'No numerical improvement threshold or replication criterion has been established here.' in candidate
    context=json.loads((folder/'retained-context.json').read_text())
    order=next(q for q in context['branch_covariance_quote'] if q.startswith('#11 '))
    assert '(5F,5B,3F,3B)' in order and '(1,-1,-1,1)^T' in order
