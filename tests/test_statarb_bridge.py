"""Check the real sibling adapter stages fixes without mutating any statarb job."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def test_new_statarb_jobs_freeze_current_shared_engine(tmp_path, monkeypatch):
    checkout = Path(__file__).resolve().parents[1]
    adapter = checkout.parent / "statarb/arxiv_drip/research_protocol.py"
    if not adapter.exists():
        pytest.skip("Sibling statarb checkout is not installed")
    spec = importlib.util.spec_from_file_location("statarb_protocol_contract", adapter)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "frozen_inputs", lambda d: (
        {"id": "test-paper", "title": "Fixture", "abstract": "Fixture"}, {},
        {"title": "Fixture dossier", "scope": "Fixture only"}))
    def source(aid, root):
        (root / "sources/Q.tex").write_text("Fixture full text")
        return "sources/Q.tex"
    monkeypatch.setattr(module, "paper_source", source)
    root, config = module.prepare({"pathfinder_root": str(checkout), "model": "unused", "codex": "unused"}, tmp_path)
    manifest = json.loads((root / "engine-manifest.json").read_text())
    for name in ("alerts.py", "recovery.py", "supervise.py", "transport.py", "runner.py", "health.py"):
        frozen = root / "engine/pathfinder" / name
        assert frozen.read_bytes() == (checkout / "pathfinder" / name).read_bytes()
        assert manifest["files"][f"pathfinder/{name}"] == hashlib.sha256(frozen.read_bytes()).hexdigest()
    assert config["pair_kind"] == "paper-strategy"
    assert config["codex"]["disable_toolless_shell"] is True
    assert config["billing"] == "subscription"
    # Existing jobs cannot be silently merged/re-frozen by this preparation path.
    with pytest.raises(FileExistsError):
        module.prepare({"model": "unused", "codex": "unused"}, tmp_path)
