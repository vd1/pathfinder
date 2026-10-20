import importlib.util,json
from pathlib import Path
import pytest
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

@pytest.mark.parametrize('pair,identity,revision',[('Q053-P011','preparation-spec-20261020','feature-scope-framing-1'),('Q053-P024','conditional-information-20261020','gaussian-noise-framing-1')])
def test_operator_framing_child(tmp_path,monkeypatch,pair,identity,revision):
    helper.test_ready_child(tmp_path,monkeypatch,pair,identity,revision,'2026-10-20-operator-framing')
    root=tmp_path/'copy/threads'/pair/'edited/account-amendments'/identity/'revisions'/revision
    scope=json.loads((root/'operator-framing.json').read_text())
    assert scope['kind']=='operator-framing-v1'
    frozen=json.loads((root/'review/frozen-inputs.json').read_text())
    assert not any('operator-framing' in key for key in frozen)
    assert 'as specified' not in (root/'candidate.tex').read_text()
