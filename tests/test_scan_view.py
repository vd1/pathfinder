"""The scan on the operator's pages (nobel, 11 October 2026). The monitor's heat map named its cells by position
(Q1P2) while a numbered corpus names pairs Q005-P007, so shortlisted cells were never outlined or clickable. The
operator view showed nothing until research started, though choosing the cut over thousands of scored pairs is
where the operator reads most."""
import json, threading, urllib.request
from pathlib import Path
from pathfinder import campaign_state, config, corpus, monitor, scan, select, view
from stubcampaign import make

PAGE = Path(view.__file__).parent


def _zoo(tmp_path, **raw):
    c = make(tmp_path, same_corpus=True, **raw)
    rows = [{"id": f"2401.0000{i}", "n": n, "title": f"Paper {n}", "abstract": f"Abstract {n}."}
            for i, n in enumerate((433, 265, 294, 17), 1)]
    for side in "QP":
        (tmp_path / f"{side}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    c = config.load(tmp_path)
    scan.run(c)
    return c


def _scores(c, scores):
    rows = [json.loads(line) for line in c.path("scan.jsonl").read_text().splitlines()]
    for r in rows:
        r["feasibility"], r["gain"] = scores[r["pair_id"]]
    c.path("scan.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


SCORES = {"Q017-P265": (90, 90), "Q017-P294": (80, 80), "Q017-P433": (70, 70),
          "Q265-P294": (60, 60), "Q265-P433": (50, 50), "Q294-P433": (40, 40)}


def test_the_heat_map_names_cells_by_the_engine_pair_ids_and_labels_rows_by_number(tmp_path):
    c = _zoo(tmp_path)
    sc = monitor.state(c)["scan"]
    Q = corpus.read(c.path("Q.jsonl"))
    assert sc["ids"][0][1] == corpus.pair_id_for(c, 0, 1, Q, Q) == "Q433-P265"
    assert sc["q_n"] == [433, 265, 294, 17]
    page = (PAGE / "monitor.html").read_text()
    assert "Q${i+1}P${j+1}" not in page and "sc.ids[i][j]" in page


def test_a_cap_per_paper_diversifies_the_selection(tmp_path):
    c = _zoo(tmp_path)
    _scores(c, SCORES)
    # paper 17 is in the three best pairs; with at most one pair per paper only 17-265 and 294-433 remain
    out = select.run(c, min_score=0, per_paper=1)
    assert [p["pair_id"] for p in out["pairs"]] == ["Q017-P265", "Q294-P433"] and out["per_paper"] == 1
    out = select.run(c, cut=50, per_paper=2)
    assert [p["pair_id"] for p in out["pairs"]] == ["Q017-P265", "Q017-P294", "Q265-P294"]


def test_the_state_document_reports_the_scan_while_it_runs(tmp_path):
    c = _zoo(tmp_path)
    s = campaign_state.build(c)["scan"]
    assert s["done"] == 6 and s["total"] == 6 and s["errors"] == 0 and s["same_corpus"] is True
    assert s["selected"] == len(json.loads(c.path("shortlist.json").read_text())["pairs"]) and "rate_per_minute" in s and "eta_seconds" in s and "input_tokens" in s


def test_the_view_serves_the_ranked_scan_with_titles_and_the_selection(tmp_path):
    c = _zoo(tmp_path)
    _scores(c, SCORES)
    select.run(c, min_score=3000)
    srv = view.make_server(c, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/scan") as r:
            doc = json.loads(r.read())
    finally:
        srv.shutdown()
    first = dict(zip(doc["columns"], doc["rows"][0]))
    assert first["pair_id"] == "Q017-P265" and first["score"] == 8100 and first["q"] == 17 and first["p"] == 265
    assert doc["papers"]["Q"]["17"]["title"] == "Paper 17" and doc["papers"]["Q"]["17"]["id"] == "2401.00004"
    assert doc["selected"] == ["Q017-P265", "Q017-P294", "Q017-P433", "Q265-P294"] and doc["same_corpus"] is True
    assert doc["version"] == campaign_state.build(c)["scan"]["version"]


def test_the_view_page_has_a_scan_section_and_a_dark_mode():
    html, js, css = ((PAGE / name).read_text() for name in ("view.html", "view-scan.js", "view.css"))
    assert 'id="scan-section"' in html and 'src="view-scan.js"' in html and "/api/scan" in js
    assert "prefers-color-scheme: dark" in css and "/view-scan.js" in view.STATIC


def test_topic_families_come_from_the_optional_sidecar(tmp_path):
    c = _zoo(tmp_path)
    assert campaign_state.scan_document(c)["papers"]["Q"]["17"]["topics"] == []
    c.path("topics.json").write_text(json.dumps({"17": {"topics": ["Search", "Simulation"], "zoo_entries": ["x"]},
                                                 "265": ["Simulation"], "bad": ["ignored"]}))
    papers = campaign_state.scan_document(c)["papers"]
    assert papers["Q"]["17"]["topics"] == ["Search", "Simulation"] and papers["P"]["265"]["topics"] == ["Simulation"]
    c.path("topics.json").write_text(json.dumps({"Q": {"17": ["Search"]}, "P": {}}))
    papers = campaign_state.scan_document(c)["papers"]
    assert papers["Q"]["17"]["topics"] == ["Search"] and papers["P"]["17"]["topics"] == []
