import dataclasses
import hashlib
import json
from pathlib import Path

import pytest
from pathfinder import collection, library, research, thread, transport
from stubcampaign import make


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def case(tmp_path, monkeypatch):
    # Unit fixtures are temporary; production rejects evidence in runtime-readable roots.
    monkeypatch.setattr(collection, "RUNTIME_ROOTS", ())
    monkeypatch.delenv("PATHFINDER_CODEX", raising=False)
    pool = tmp_path / "pool"; pool.mkdir()
    allowed = pool / "paper-v1.tex"; allowed.write_text("An admitted historical source.")
    denied = pool / "paper-v2.tex"; denied.write_text("WITHHELD_POST_CUTOFF_TARGET")
    cards = tmp_path / "cards"; cards.mkdir()
    data = {"version": 1, "pair_id": "Q1P1", "pool_roots": [str(pool)],
            "cutoff_utc": "2020-01-01T00:00:00Z",
            "sources": [{"id": "paper", "version": "v1", "first_appearance_utc": "2018-01-01T00:00:00Z",
                         "version_appearance_utc": "2019-01-01T00:00:00Z",
                         "files": [{"path": str(allowed), "sha256": digest(allowed)}]}], "inputs": {}}
    c = make(tmp_path / "campaign", pairs=("Q1P1",))
    rows = thread._pair(c, "Q1P1")
    for side, row in zip("QP", rows):
        path = cards / f"{side}.md"; path.write_text(f"Primitive {side} from the admitted paper.")
        data["inputs"][side] = {"id": row["id"], "title": row["title"], "path": str(path),
                                "sha256": digest(path), "source_ids": ["paper"]}
    manifest = tmp_path / "collection.json"
    def seal():
        manifest.write_text(json.dumps(data))
        c.raw["restricted_collection"] = {"manifest": str(manifest), "sha256": digest(manifest)}
    seal()
    return c, data, seal, allowed, denied


def test_research_uses_references_and_no_retrieval(case, monkeypatch):
    c, data, _, allowed, denied = case
    from pathfinder import net, paper_source
    monkeypatch.setattr(net, "urlopen", lambda *a, **kw: pytest.fail("network"))
    monkeypatch.setattr(paper_source, "resolve", lambda *a, **kw: pytest.fail("fetch"))
    before = {p: digest(p) for p in (allowed, denied)}
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    d = c.thread_dir("Q1P1")
    for side in "QP":
        assert (d / "inputs" / f"{side}.md").is_symlink()
        assert (d / "inputs" / f"{side}.md").resolve() == Path(data["inputs"][side]["path"])
    assert {p: digest(p) for p in before} == before
    assert not (d / "inputs/pair-context.md").exists()
    assert not (d / ".pathfinder/paper_source.py").exists()
    assert library.get(c, "paper") == allowed
    with pytest.raises(collection.Refused, match="request logged"):
        library.get(c, "unlisted")
    assert not any("WITHHELD_POST_CUTOFF_TARGET" in p.read_text(errors="replace")
                   for p in d.rglob("*") if p.is_file())


def test_exact_file_permission_profile_and_closed_tools(case):
    c, data, _, allowed, denied = case
    d = thread.prepare(c, "Q1P1")
    c = dataclasses.replace(c, backend="codex")
    cmd = transport._command(c, "gpt-6-astra", True, True, d)
    from pathfinder.sandbox import toml
    settings = collection.settings(c, d, True)
    fs = settings[f"permissions.{collection.PROFILE}.filesystem"]
    assert fs[str(allowed)] == "read" and str(denied) not in fs
    assert str(allowed.parent) not in fs
    assert fs["/private/tmp"] == fs["/private/var/folders"] == "deny"
    assert fs[str(d / "inputs")] == "read"
    assert "--search" not in cmd and "--add-dir" not in cmd
    assert 'web_search="disabled"' in cmd
    assert "project_doc_max_bytes=0" in cmd
    assert all(f"features.{name}=false" in cmd for name in collection.DISABLED_FEATURES)
    assert f"permissions.{collection.PROFILE}.filesystem={toml(fs)}" in cmd


@pytest.mark.parametrize("value", ["2020-01-01T00:00:00Z", "2021-01-01T00:00:00Z"])
def test_late_version_of_early_paper_refused(case, value):
    c, data, seal, *_ = case
    data["sources"][0]["version_appearance_utc"] = value; seal()
    with pytest.raises(collection.Refused, match="strictly before"):
        thread.prepare(c, "Q1P1")
    assert not c.thread_dir("Q1P1").exists()


def test_hash_change_and_input_substitution_refused(case):
    c, data, _, allowed, denied = case
    d = thread.prepare(c, "Q1P1")
    request = transport.request("test", model="m", tools=True, search=True, cwd=d,
                                timeout=2, thread="Q1P1", stage="peer", actor="ada")
    collection.check_request(c, request)
    allowed.write_text("changed")
    with pytest.raises(collection.Refused, match="hash differs"):
        collection.check_request(c, request)
    allowed.write_text("An admitted historical source.")
    link = d / "inputs/Q.md"; link.unlink(); link.symlink_to(denied)
    with pytest.raises(collection.Refused, match="reference changed"):
        collection.check_request(c, request)


@pytest.mark.parametrize("key,value", [
    ("extensions", {"transport": "local:unsafe"}),
    ("refusal_fallback", {"backend": "claude", "model": "other"}),
    ("codex", {"config": ["sandbox_mode=\"danger-full-access\""]}),
    ("codex", {"filesystem_profile": {"read": ["/"]}}),
    ("research_scheme", "composable"),
])
def test_configuration_bypasses_refused(case, key, value):
    c, *_ = case; c.raw[key] = value
    with pytest.raises(collection.Refused):
        thread.prepare(c, "Q1P1")


def test_unknown_source_version_and_symlink_refused(case):
    c, data, seal, allowed, denied = case
    data["sources"][0]["version"] = "latest"; seal()
    with pytest.raises(collection.Refused, match="pinned"):
        collection.load(c)
    data["sources"][0]["version"] = "v1"
    allowed.unlink(); allowed.symlink_to(denied); seal()
    with pytest.raises(collection.Refused, match="canonical"):
        collection.load(c)


def test_pool_union_and_read_only_check(case,tmp_path):
    c,data,seal,allowed,_=case
    second=tmp_path/'secondary';second.mkdir();source=second/'second.tex';source.write_text('Second admitted source.')
    data['pool_roots'].append(str(second));data['sources'][0]['files'].append({'path':str(source),'sha256':digest(source)});seal()
    result=collection.inspect(c)
    assert result['admitted_file_count']==2 and not c.thread_dir('Q1P1').exists()
    fs=result['permission_settings'][f'permissions.{collection.PROFILE}.filesystem']
    assert fs[str(source)]=='read' and str(second) not in fs


def test_unadmitted_stages_and_cli_fetch_refused(case,monkeypatch):
    c,data,_,_,_=case;d=thread.prepare(c,'Q1P1')
    r=transport.request('test',model='stub',tools=True,search=True,cwd=d,timeout=1,thread='Q1P1',stage='scan',actor='ada')
    with pytest.raises(collection.Refused):transport.execute(c,r)
    assert not c.path('receipts.jsonl').exists()
    from pathfinder import cli,config,corpus
    monkeypatch.setattr(config,'load',lambda *a:c)
    monkeypatch.setattr(corpus,'fetch',lambda *a,**kw:pytest.fail('retrieval'))
    with pytest.raises(collection.Refused):cli.main(['--root',str(c.root),'fetch'])


def test_operator_cutoff_seal_not_model_visible(case):
    c,data,_,_,_=case;d=thread.prepare(c,'Q1P1')
    rule=collection.rule(c,d)
    intro=rule.split('{',1)[0]
    assert 'Approved research collection' in intro and 'historical' not in intro and 'cutoff' not in intro
    assert data['cutoff_utc'] not in rule and data['sources'][0]['first_appearance_utc'] not in rule
    fs=collection.settings(c,d,True)[f'permissions.{collection.PROFILE}.filesystem']
    assert fs[str(d/'inputs')]=='read'
    assert fs[str(d/'inputs/restricted-collection.json')]=='deny'
    collection.check_inputs(d,data)
