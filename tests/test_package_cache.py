"""One package cache for every agent (EV rerun of the 10x10 pilot, 2 November 2026: the sandbox let an agent write
only its own folder, so uv could not use ~/.cache/uv; each agent set a cache inside its folder and downloaded the
same wheels again, 2.5 GB over 14 threads). An agent with tools may write the campaign's package cache, and uv
is pointed at it."""
import pytest
from pathfinder import config, sandbox, transport
from stubcampaign import make


def _added(cmd):
    return [cmd[i + 1] for i, a in enumerate(cmd) if a == "--add-dir"]


def test_an_agent_with_tools_may_write_the_package_cache(tmp_path):
    c = make(tmp_path, backend="codex", package_cache=str(tmp_path / "packages"))
    shared = str((tmp_path / "packages").resolve())
    assert shared in _added(transport._command(c, "m", True, True, tmp_path / "t"))
    assert shared not in _added(transport._command(c, "m", False, False, tmp_path / "t"))
    c.backend = "claude"
    assert shared in _added(transport._command(c, "m", True, False, tmp_path / "t"))
    profile = " ".join(sandbox.args(tmp_path / "t", True, True, cache=tmp_path / "cache", packages=tmp_path / "packages"))
    assert f'"{shared}" = "write"' in profile


def test_uv_is_pointed_at_the_package_cache(tmp_path):
    c = make(tmp_path, backend="codex", package_cache=str(tmp_path / "packages"))
    assert transport._env(c, tmp_path / "t")["UV_CACHE_DIR"] == str((tmp_path / "packages").resolve())


def test_the_default_is_one_cache_for_every_campaign(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("PATHFINDER_PACKAGE_CACHE", raising=False)
    a, b = (make(tmp_path / n) for n in "ab")
    for c in (a, b):
        c.raw.pop("package_cache")
    assert transport.package_cache(a) == transport.package_cache(b) == tmp_path / "home/.cache/pathfinder/uv"


def test_a_bad_package_cache_setting_is_refused(tmp_path):
    with pytest.raises(ValueError, match="package_cache"):
        make(tmp_path, package_cache="")
        config.load(tmp_path)
