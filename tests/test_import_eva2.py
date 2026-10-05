"""julien-2's eva2 experiments (three direct-EVA branch campaigns and a joint campaign) as one canonical composable pair."""
import json, shutil
from pathfinder import composable, config, edit, import_eva2, reconcile, research, transport
from stubcampaign import make


def _eva2(tmp_path):
    exp = tmp_path / "experiments" / "eva-top-ten-01-q002-p024"
    for k in (1, 2, 3):
        c = make(exp / "runs" / f"branch-{k}", research_scheme="direct_eva", ledger_reviews=4, rounds=3)
        research.run_thread(c, "Q1P1")
        assert research.status(c, "Q1P1")["status"] == "HANDOFF"
    joint = make(exp / "runs" / "joint", research_scheme="eva", rounds=2,
                 research_bundles=[f"branches/branch-{k}" for k in (1, 2, 3)])
    d = research.prepare(joint, "Q1P1")
    for k in (1, 2, 3):                                  # eva2 copies each frozen handoff into the joint thread
        src = exp / "runs" / f"branch-{k}" / "threads" / "Q1P1"
        shutil.copytree(src, d / "branches" / f"branch-{k}", ignore=shutil.ignore_patterns(".pathfinder"))
        (d / "branches" / f"branch-{k}" / "bundle.json").write_text(json.dumps({"eva2": True, "label": f"branch-{k}"}))
    research._set(joint, "Q1P1", status="running", stage="peers", round=1)
    assert research.run_thread(joint, "Q1P1") == "DRAFT"
    (exp / "runs" / "joint" / "prompts").mkdir(exist_ok=True)
    (exp / "runs" / "joint" / "prompts" / "peer.md").write_text("julien-2 joint peer prompt {{ACTOR}}")
    return exp


def test_an_eva2_experiment_becomes_a_canonical_composable_pair(tmp_path):
    exp = _eva2(tmp_path)
    out = tmp_path / "canon"
    import_eva2.run(exp, out)
    c = config.load(out)
    assert c.raw["research_scheme"] == "composable" and c.raw["branches"] == 3
    assert c.raw["branch"]["ledger_reviews"] == 4 and c.raw["branch"]["rounds"] == 3 and c.raw["rounds"] == 2
    composable.check_frozen(c, "Q1P1")                            # canonical inventories over eva2's exact files
    s = research.status(c, "Q1P1")
    assert s["status"] == "DRAFT" and set(s["branches_frozen"]) == {"branch-1", "branch-2", "branch-3"}
    d = c.thread_dir("Q1P1")
    assert (d / "branches" / "branch-1" / "eva2-bundle.json").exists()
    assert (d / "branch-runs" / "branch-2" / "status.json").exists()
    assert (out / "prompts" / "peer.md").read_text().startswith("julien-2 joint")
    assert json.loads((out / "import.json").read_text())["experiment"] == str(exp)


def test_the_imported_pair_goes_on_to_edit_without_new_research(tmp_path):
    exp = _eva2(tmp_path)
    out = tmp_path / "canon"
    import_eva2.run(exp, out)
    c = config.load(out)
    before = len(transport.receipts(c))
    from pathfinder import runner
    assert runner.pending(c) == ["Q1P1"]                          # research done, edit to do
    assert research.run_thread(c, "Q1P1") == "DRAFT"
    assert len(transport.receipts(c)) == before
    assert edit.run(c, "Q1P1") == "done"


def _accepted_pce(exp, name="pce-recovery-08", editorial="accepted"):
    """eva2's reports: the PCE round the index links as the reviewed account, with its delivery record."""
    reports = exp / "reports"; d = reports / name; d.mkdir(parents=True)
    (d / "account.tex").write_text("\\documentclass{article}\\begin{document}PCE account\\end{document}\n")
    (d / "account.pdf").write_bytes(b"%PDF-1.5 reviewed account")
    (d / "drafts").mkdir(); (d / "drafts" / "current.tex").write_text("draft")
    (d / "delivery.json").write_text(json.dumps({"pce_result": {"status": editorial}, "editorial_status": editorial,
                                                 "pdf": f"reports/{name}/account.pdf"}))
    (reports / "index.md").write_text(f"- [Joint research account](account/account.pdf)\n"
                                      f"- [Reviewed PCE account]({name}/account.pdf)\n\nEditorial status: {editorial}.\n")
    return d


def test_the_accepted_pce_account_is_the_pairs_edited_note(tmp_path):
    exp = _eva2(tmp_path)
    pce = _accepted_pce(exp)
    out = tmp_path / "canon"
    import_eva2.run(exp, out)
    c = config.load(out)
    ed = c.thread_dir("Q1P1") / "edited"
    assert edit.status(c, "Q1P1")["status"] == "done"
    assert (ed / "note.tex").read_text() == (pce / "account.tex").read_text()
    assert (ed / "note.pdf").read_bytes() == (pce / "account.pdf").read_bytes()
    assert (ed / "eva2-pce" / "drafts" / "current.tex").exists()      # the whole accepted round, for the record
    provenance = json.loads((out / "import.json").read_text())["edit"]
    assert provenance["source"] == "reports/pce-recovery-08" and provenance["editorial_status"] == "accepted"
    assert provenance["note_sha256"] and provenance["pdf_sha256"]
    from pathfinder import runner
    assert runner.pending(c) == []                                    # nothing to re-edit


def test_a_pce_account_not_accepted_leaves_the_edit_queued(tmp_path):
    exp = _eva2(tmp_path)
    _accepted_pce(exp, editorial="review_required")
    out = tmp_path / "canon"
    import_eva2.run(exp, out)
    c = config.load(out)
    assert edit.status(c, "Q1P1")["status"] == "none"
    assert json.loads((out / "import.json").read_text())["edit"] is None


def test_a_pause_pair_with_its_accepted_account_is_not_unfinished_editing(tmp_path):
    exp = _eva2(tmp_path)
    status = exp / "runs" / "joint" / "threads" / "Q1P1" / "status.json"
    s = json.loads(status.read_text()); s["status"] = "PAUSE"; status.write_text(json.dumps(s))
    out = tmp_path / "queued"
    import_eva2.run(exp, out)                                         # engine semantics: a PAUSE ending is edited too
    from pathfinder import health
    assert [w["needs_edit"] for w in health.snapshot(config.load(out))["work"]] == [True]
    _accepted_pce(exp)
    out = tmp_path / "canon"
    import_eva2.run(exp, out)
    assert [w["needs_edit"] for w in health.snapshot(config.load(out))["work"]] == [False]


def _receipt(exp, name, identity, mtime, **extra):
    import os
    d = exp / "runtime" / "receipts"; d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.json"
    p.write_text(json.dumps({"text": "", "seconds": 1.0, "usage": {"input_tokens": 10, "output_tokens": 2},
                             "cost": None, "outcome": "completed", "identity": identity,
                             "route": {"runtime": "codex", "model": "gpt-6-astra", "effort": "medium"}, **extra}))
    os.utime(p, (mtime, mtime))


def test_eva2_receipts_take_stage_actor_and_time_from_what_eva2_kept(tmp_path):
    exp = _eva2(tmp_path)
    name = exp.name
    calls = {"a": (f"{name}/branch-2/1/0/0/Q1P1:peers:ada:round-1:review-0:repair-0:call-0", 1_790_000_005),
             "b": (f"{name}/branch-1/1/0/0/Q1P1:ledger_review:verifier:round-1:review-0:repair-0:call-2", 1_790_000_004),
             "c": ("joint/account/2", 1_790_000_003),
             "d": ("joint/pce-recovery-07/pass-01/fact-checker", 1_790_000_002),
             "e": ("joint/pce-recovery-10/editor", 1_790_000_001),
             "f": ("joint/downstream-recovery-07/actionability/2", 1_790_000_000),
             "g": ("joint/actionability/1", 1_790_000_006)}
    for call, (identity, mtime) in calls.items():
        _receipt(exp, call, identity, mtime)
    _receipt(exp, "h", "joint/pce/pass-01/author", 1_790_000_007, outcome="blocked", error="quota")
    out = tmp_path / "canon"
    import_eva2.run(exp, out)
    rows = {r["call_id"]: r for r in transport.receipts(config.load(out)) if r.get("imported_from") == "eva2"}
    got = {k: (r["stage"], r["actor"], r["branch"]) for k, r in rows.items()}
    assert got == {"a": ("peer", "ada", "branch-2"), "b": ("ledger_review", "verifier", "branch-1"),
                   "c": ("edit", "account-editor", None), "d": ("edit", "fact-checker", None),
                   "e": ("edit", "editor", None), "f": ("actionability", "assessor", None),
                   "g": ("actionability", "assessor", None), "h": ("edit", "author", None)}
    assert all(r["model"] == "gpt-6-astra" and r["backend"] == "codex" for r in rows.values())
    assert rows["e"]["at"] == "2026-09-21T14:13:21Z" and rows["e"]["at_source"] == "file mtime"
    assert rows["d"]["eva2_identity"] == "joint/pce-recovery-07/pass-01/fact-checker"
    assert rows["h"]["error"] == "quota" and rows["h"]["outcome"] == "blocked"
    order = [r["call_id"] for r in transport.receipts(config.load(out)) if r.get("imported_from") == "eva2"]
    assert order == ["f", "e", "d", "c", "b", "a", "g", "h"]            # in the order the calls ended


def _eva2_bundle(path, files):
    """A bundle as eva2.evidence.freeze writes it: a list inventory, digested over its canonical JSON."""
    import hashlib
    path.mkdir(parents=True)
    rows = []
    for name, data in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_bytes(data)
        rows.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
    digest = hashlib.sha256((json.dumps(rows, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()).hexdigest()
    (path / "bundle.json").write_text(json.dumps({"schema_version": 1, "branch": path.name, "files": rows,
                                                  "inventory_sha256": digest}))
    return path


def test_a_recorded_eva2_bundle_verifies_by_its_inventory_and_any_change_is_refused(tmp_path):
    import os, pytest
    files = {"ledger.jsonl": b'{"seq": 1}\n', "ada/note.tex": "π".encode(), "ada/note.log": b"fonts/cm/cmr10.pfb"}
    bundle = _eva2_bundle(tmp_path / "ok" / "branch-1", files)
    assert import_eva2.verify_bundle(bundle)["branch"] == "branch-1"         # by-products recorded then still verify

    def refused(change, match):
        b = _eva2_bundle(tmp_path / match.replace(" ", "-") / "branch-1", files)
        change(b)
        with pytest.raises(composable.BundleError, match=match):
            import_eva2.verify_bundle(b)
    refused(lambda b: (b / "ada/note.tex").write_text("rewritten"), "changed")
    refused(lambda b: (b / "ada/late.json").write_text("{}"), "added")
    refused(lambda b: (b / "ada/note.log").unlink(), "missing")
    refused(lambda b: (os.unlink(b / "ada/note.tex"), os.symlink(tmp_path / "elsewhere", b / "ada/note.tex")), "symbolic link")

    def forged(b):
        record = json.loads((b / "bundle.json").read_text())
        record["files"][0]["path"] = "../outside.jsonl"
        (b / "bundle.json").write_text(json.dumps(record))
    refused(forged, "inventory digest")


def test_eva2s_actionability_assessment_is_the_pairs_actionability(tmp_path):
    from pathfinder import actionability
    exp = _eva2(tmp_path)
    d = exp / "reports" / "assessments" / "downstream-recovery-07"; d.mkdir(parents=True)
    answer = {"decision": "NEEDS_INPUTS", "rationale": "r",                   # the shape eva2's assessor gave
              "evidence": [{"observation": "o", "source": "papers/Q.txt p. 3", "role": "why it matters"}],
              "required_inputs": [{"input": "CDK2 set", "why": "w"}],
              "next_experiment": {"step": "n"}, "falsification": ["f1", "f2"]}
    (d / "actionability.json").write_text(json.dumps({"status": "available", "assessment": answer, "input_sha256": "x"}))
    out = import_eva2.run(exp, tmp_path / "canon")
    c = config.load(out)
    s = actionability.status(c, "Q1P1")
    assert s["status"] == "done" and s["decision"] == "NEEDS_INPUTS" and s["assessment"] == answer
    assert s["imported_from"] == "reports/assessments/downstream-recovery-07/actionability.json"
    assert json.loads((out / "import.json").read_text())["actionability"] == s["imported_from"]


def test_an_experiment_without_an_assessment_imports_none(tmp_path):
    from pathfinder import actionability
    out = import_eva2.run(_eva2(tmp_path), tmp_path / "canon")
    assert actionability.status(config.load(out), "Q1P1") == {"status": "none"}
