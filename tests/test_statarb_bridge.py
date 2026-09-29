"""Check the real sibling adapter freezes the pinned engine release without mutating any statarb job."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def test_new_statarb_jobs_freeze_the_pinned_engine_release(tmp_path, monkeypatch):
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
    # new jobs freeze the pinned engine release, verified against its commit, not the moving checkout
    from pathfinder import freeze
    manifest = json.loads((root / "engine-manifest.json").read_text())
    assert manifest["ref"] == module.ENGINE_REF and manifest["verification"] == "verified"
    assert freeze.verify(root / "engine", checkout)["status"] == "verified"
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((root / "engine" / name).read_bytes()).hexdigest() == digest
    assert config["pair_kind"] == "paper-strategy"
    assert config["codex"]["disable_toolless_shell"] is True
    assert config["billing"] == "subscription"
    # Existing jobs cannot be silently merged/re-frozen by this preparation path.
    with pytest.raises(FileExistsError):
        module.prepare({"model": "unused", "codex": "unused"}, tmp_path)
