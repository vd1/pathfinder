import importlib.util
from pathlib import Path
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('register_copy',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)

def test_allocation_framing_child(tmp_path,monkeypatch):
    helper.test_ready_child(tmp_path,monkeypatch,'Q024-P022','allocation-domain-20261020','input-priority-framing-1','2026-10-20-allocation-framing')
