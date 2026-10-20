import importlib.util
from pathlib import Path
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_fmo_control_scope_child(tmp_path,monkeypatch):
    helper.test_ready_child(tmp_path,monkeypatch,'Q002-P072','time-swap-definition-20261020','fmo-control-scope-1','2026-10-20-fmo-control-scope')


def test_exact_scope_and_retained_visibility():
    import hashlib,json
    folder=ROOT/'operator-log/2026-10-20-fmo-control-scope'
    parent=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2/threads/Q002-P072/edited/account-amendments/time-swap-definition-20261020/revisions/coherence-normalisation-1')
    packet=json.loads((folder/'Q002-P072/revision.json').read_text())
    original=(parent/'candidate.tex').read_bytes()
    assert hashlib.sha256(original).hexdigest()==packet['parent_candidate_sha256']
    expected=original.decode()
    for change in packet['changes']:
        assert expected.count(change['before'])==1
        expected=expected.replace(change['before'],change['after'],1)
    assert expected==(folder/'Q002-P072/account-candidate.tex').read_text()
    for finding in packet['findings']:
        raw=(parent/'review'/finding['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==finding['sha256']
        assert finding['quote'] in raw.decode()
    context=json.loads((folder/'retained-context.json').read_text())
    frozen=json.loads((parent/'review/frozen-inputs.json').read_text())
    supplement=frozen['sources/external/research-supplement.md']
    assert hashlib.sha256(supplement.encode()).hexdigest()==context['supplement_sha256']
    for entry in context['entries']:
        assert entry['text'] in supplement
