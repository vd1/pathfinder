import importlib.util
from pathlib import Path
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_selector_scope_child(tmp_path,monkeypatch):
    helper.test_ready_child(tmp_path,monkeypatch,'Q010-P030','selector-definitions-20261020','selector-scope-1','2026-10-20-selector-scope')
