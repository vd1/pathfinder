"""The presentation pass after ACCEPT (nobel pilot on Q472-P527 and Q138-P465, 18 October 2026).

Reviewers accept a paper for its science; readiness for release is a separate state. With "presentation": true an
accepted paper goes through:

1. an editor (stage "present", actor "editor"): notation bound at first use, pipeline labels removed, background
   calibrated on the full text of the two source papers, salience, faithful framing, and every open minor finding
   of the ACCEPT applied, dismissed with a reason, or marked "needs lookup"; it may propose a new title, and it
   escalates what needs a choice of meaning instead of guessing. It never sees the research ledger.
2. a lookup (stage "present_lookup", with web search) when a finding needs one.
3. a fresh check (stage "present_check", "presentation_checkers": 1 or 2, their findings united) that reads the
   manuscript, the change log and the open findings only.
4. meaning and claim findings, and the editor's escalations, go to one targeted review call (stage "review",
   actor "claims") that reads the accepted paper: confirmed (the accepted paper has it), introduced (only the
   edit has it) or dismissed. A confirmed one is amended automatically once per paper (an author round and a
   review round, paper.amend), then the pass starts again on the new accepted paper; a second one stops at
   RETURNED with paper/presentation/amend-findings.json ready for the operator.
5. at most "presentation_cycles" (default 2) correction cycles on the remaining findings (stage "present", actor
   "corrector"): definitions and rewording only, behind `guard`; a refused correction is discarded.

The pass ends CLEARED (paper.json status, with the sha256 of the manuscript it cleared), RETURNED or
PAUSE-ON-PRESENT; its record is paper/presentation/ (state.json, one directory per stage). The accepted paper,
paper/paper.tex, is never changed by the pass."""
from __future__ import annotations
import difflib, hashlib, json, re, shutil, unicodedata
from pathlib import Path
from . import context, contracts, library, paper, research, transport
from .admission import Refused
from .context import Section
from .research import _now, _prompt

SUBSTANTIVE = ("meaning", "claim")
DISPOSED = ("applied", "dismissed", "already applied", "out of scope")   # out of scope: a pipeline file, with a reason
TERMINAL = ("CLEARED", "RETURNED", "PAUSE-ON-PRESENT", "blocked")
AUTO_AMENDS = 1                                   # automatic amends per paper; the next confirmed problem waits
KEEP = (".sty", ".bst", ".png", ".pdf")           # beside paper.tex in each stage, so it builds as the paper does


def enabled(campaign) -> bool:
    return bool((campaign.raw or {}).get("presentation", False))


def checkers(campaign) -> int:
    return (campaign.raw or {}).get("presentation_checkers", 1)


def cycles(campaign) -> int:
    return (campaign.raw or {}).get("presentation_cycles", 2)


def validate(raw: dict) -> None:
    if "presentation" in raw and not isinstance(raw["presentation"], bool):
        raise ValueError(f"presentation must be true or false, got {raw['presentation']!r}")
    for key, low, high in (("presentation_checkers", 1, 2), ("presentation_cycles", 0, 2)):
        v = raw.get(key, low)
        if type(v) is not int or not low <= v <= high:
            raise ValueError(f"{key} must be an integer from {low} to {high}, got {v!r}")
    rel = raw.get("release")
    if rel is not None and (not isinstance(rel, dict) or not isinstance(rel.get("disclosure"), str)
                            or not isinstance(rel.get("author", ""), str)):
        raise ValueError('release must be {"disclosure": "path to the acknowledgement text", "author": "optional"}, '
                         f"got {rel!r}")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def folder(campaign, pair_id) -> Path:
    return paper.folder(campaign, pair_id) / "presentation"


def state(campaign, pair_id) -> dict:
    p = folder(campaign, pair_id) / "state.json"
    return json.loads(p.read_text()) if p.exists() else {"state": "none"}


def final(campaign, pair_id) -> Path | None:
    """The manuscript the pass ended on, or None before its first stage."""
    s = state(campaign, pair_id)
    return folder(campaign, pair_id) / s["stage"] / "paper.tex" if s.get("stage") else None


def _save(campaign, pair_id, **kw) -> dict:
    d = folder(campaign, pair_id); d.mkdir(parents=True, exist_ok=True)
    s = state(campaign, pair_id); before = s.get("state"); s.update(kw, updated=_now())
    (d / "state.json").write_text(json.dumps(s, indent=1))
    if s.get("state") != before:
        from . import events
        events.emit(campaign, "presentation", unit=pair_id, state=s.get("state"), stage=s.get("stage"),
                    reason=s.get("reason"))
    return s


def run(campaign, pair_id: str, restart: bool = False) -> str:
    """The pass for one accepted paper, resuming a stopped one; returns CLEARED, RETURNED, PAUSE-ON-PRESENT,
    blocked or stopped, or the paper's state after an automatic amend that did not end ACCEPTED."""
    if not getattr(campaign, "_edited_publication", False) and research.status(campaign, pair_id).get("status") != "DRAFT":
        raise SystemExit(f"{pair_id} is not DRAFT")
    s = paper.status(campaign, pair_id)
    if s.get("status") in ("CLEARED", "RELEASED") and not restart:
        return s["status"]
    if s.get("status") not in paper.ACCEPTED_STATES:
        raise SystemExit(f"{pair_id}: the paper is {s.get('status')}; the presentation pass needs an ACCEPTED paper")
    try:
        result = _run(campaign, pair_id, restart)
        if not getattr(campaign, "_preserve_presentation_history", False):
            tidy(campaign, pair_id)
        return result
    except Refused as refused:
        _save(campaign, pair_id, state="stopped", reason=f"refused: {refused}"); return "stopped"
    except transport.PromptTooLarge as error:
        _save(campaign, pair_id, state="blocked", reason=str(error)); return "blocked"
    except _Blocked as error:
        _save(campaign, pair_id, state="blocked", reason=str(error)); return "blocked"


class _Blocked(Exception):
    pass


def tidy(campaign, pair_id) -> list[str]:
    """After the pass: each stage but the last keeps its manuscript, BibTeX, report, checks and the model's reply,
    not its PDF or the support files copied beside it to build it."""
    d, last, removed = folder(campaign, pair_id), state(campaign, pair_id).get("stage"), []
    for stage in (p for p in d.iterdir() if p.is_dir() and p.name != last) if d.exists() else ():
        for f in stage.iterdir():
            if f.suffix in KEEP or f.name == "pathfinder-meta.tex":
                f.unlink(); removed.append(f.relative_to(d).as_posix())
    return removed


def _open_findings(campaign, pair_id) -> list[dict]:
    """The minor findings the accepting review left open, numbered F1, F2, ... (the review's own id kept)."""
    p = paper.folder(campaign, pair_id) / "review.json"
    reviews = json.loads(p.read_text()) if p.exists() else []
    last = reviews[-1] if reviews else {}
    if last.get("decision") != "ACCEPT":
        return []
    return [{"id": f"F{i}", "review_id": f.get("id"), **({"reviewer": f["reviewer"]} if f.get("reviewer") else {}),
             "where": f.get("where"), "issue": f.get("issue"), "fix": f.get("fix")}
            for i, f in enumerate(last.get("findings") or [], 1)]


def _run(campaign, pair_id, restart) -> str:
    pd = paper.folder(campaign, pair_id); d = folder(campaign, pair_id)
    accepted = (pd / "paper.tex").read_text(errors="replace")
    s = state(campaign, pair_id)
    if getattr(campaign, "_edited_publication", False) and s.get("state") in TERMINAL and not restart:
        return s["state"]
    if restart or s.get("accepted_sha256") != sha(accepted) or s.get("state") not in ("running", "stopped"):
        if d.exists():
            archive = pd / "presentation-history"
            archive.mkdir(exist_ok=True)
            n = 1
            while (archive / f"attempt-{n:04d}").exists():
                n += 1
            d.rename(archive / f"attempt-{n:04d}")
        d.mkdir(parents=True)
        (d / "open-findings.json").write_text(json.dumps(_open_findings(campaign, pair_id), indent=1))
        s = _save(campaign, pair_id, state="running", accepted_sha256=sha(accepted), stage=None, cycles=0,
                  escalations=[], reviewed=[], started=_now(), reason=None)
    else:
        s = _save(campaign, pair_id, state="running", reason=None)
    opened = json.loads((d / "open-findings.json").read_text())
    if not (d / "pass" / "report.json").exists():
        _edit(campaign, pair_id, "pass", "editor", "present", base=None, opened=opened)
    stage = "pass"
    disposition = _dispositions(d, "pass")
    if any(v["status"] == "needs lookup" for v in disposition.values()):
        if not (d / "lookup" / "report.json").exists():
            _edit(campaign, pair_id, "lookup", "lookup", "present-lookup", base="pass", opened=opened,
                  dispositions=disposition)
        disposition.update(_dispositions(d, "lookup"))
        stage = "lookup"
    stage = state(campaign, pair_id).get("stage") or stage
    _save(campaign, pair_id, stage=stage)
    n = state(campaign, pair_id).get("cycles", 0)
    while True:
        found = list(_check(campaign, pair_id, stage, opened, disposition)["findings"])
        if getattr(campaign, "_edited_publication", False):
            source_findings = _release_language(campaign, (d / stage / "paper.tex").read_text())
            (d / stage / "release-language.json").write_text(json.dumps(source_findings, indent=1))
            found += source_findings
        s = state(campaign, pair_id)
        fresh = [e for e in s.get("escalations", []) if _key(e) not in s.get("reviewed", [])]
        notation = getattr(campaign, "_presentation_notation", None)
        if notation and stage != notation["stage"] and (found or fresh):
            return _pause(campaign, pair_id, "reviewed notation cycle not cleared: " +
                          _summary(found + fresh))
        items = [f for f in found if f.get("kind") in SUBSTANTIVE] + [{**e, "kind": "escalation"} for e in fresh]
        introduced = []
        if items:
            answers = _claims(campaign, pair_id, stage, items, accepted)
            _save(campaign, pair_id, reviewed=s.get("reviewed", []) + [_key(e) for e in fresh])
            confirmed = [{**i, **a} for i, a in zip(items, answers) if a["decision"] == "confirmed"]
            introduced = [{**i, **a} for i, a in zip(items, answers) if a["decision"] in ("introduced", "presentation")]
            if confirmed:
                return _return(campaign, pair_id, confirmed)
        remaining = [f for f in found if f.get("kind") not in SUBSTANTIVE] + introduced
        if not remaining:
            break
        if n >= getattr(campaign, "_presentation_cycle_limit", cycles(campaign)):
            return _pause(campaign, pair_id, "not cleared at the cycle limit: " + _summary(remaining))
        n += 1
        name = f"correct-{n}"
        _edit(campaign, pair_id, name, "corrector", "present-correct", base=stage, findings=remaining,
              accepted=accepted)
        rewordable = [q for f in remaining if f.get("kind") == "unclear" or f.get("decision") == "presentation"
                      for q in quoted(f.get("where"))]
        before = (d / stage / "paper.tex").read_text()
        after = (d / name / "paper.tex").read_text()
        bibliography = (d / name / "references.bib").read_text()
        notation = getattr(campaign, "_presentation_notation", None)
        if notation:
            from . import notation_continuation, pce
            try:
                projected = notation_continuation.projected_correction(before, after, bibliography, notation)
                refused = guard(before, projected, accepted, bibliography, rewordable)
            except pce.Changed as error:
                refused = [str(error)]
        else:
            refused = guard(before, after, accepted, bibliography, rewordable,
                            getattr(campaign, "_presentation_residue_identifiers", ()))
        pairs = reworded((d / stage / "paper.tex").read_text(), (d / name / "paper.tex").read_text(), accepted)
        if pairs:
            (d / name / "reworded.json").write_text(json.dumps(pairs, indent=1))
        if refused:
            (d / name / "guard.json").write_text(json.dumps(refused, indent=1))
            shutil.move(str(d / name), str(d / f"{name}-refused"))
            _save(campaign, pair_id, cycles=n)
            return _pause(campaign, pair_id, "correction refused by the guard: " + "; ".join(refused))
        stage = name
        _save(campaign, pair_id, stage=stage, cycles=n)
    open_items = [f"{f['id']} ({disposition.get(f['id'], {}).get('status', 'left open')})" for f in opened
                  if disposition.get(f["id"], {}).get("status") not in DISPOSED]
    if open_items:
        return _pause(campaign, pair_id, "open review findings not closed: " + ", ".join(open_items))
    text = (d / stage / "paper.tex").read_text()
    _save(campaign, pair_id, state="CLEARED", sha256=sha(text), cleared=_now())
    paper._set(campaign, pair_id, status="CLEARED", cleared_sha256=sha(text), presentation_stage=stage,
               reason=f"presentation cleared at {stage}")
    return "CLEARED"


def _release_language(campaign, tex):
    """Feed release-blocking source language into the guarded presentation correction loop."""
    from . import release
    clean, _ = release.strip_comments(tex)
    findings = []
    for sentence in _sentences(clean):
        hits = release.leak_check(campaign, "\\begin{document}" + sentence, "")
        if hits:
            findings.append({"kind": "unclear", "where": '"' + sentence.replace('"', "'") + '"',
                             "issue": "Reader-facing workflow language fails the release check: " + "; ".join(hits),
                             "fix": "Reword this sentence in scientific terms, preserving every limitation and "
                                    "qualification. Do not replace internal status with a claim of validation "
                                    "or remove a caveat. Editing provides no additional scientific validation.",
                             "checker": "host-release-language"})
    return findings


def _pause(campaign, pair_id, reason) -> str:
    _save(campaign, pair_id, state="PAUSE-ON-PRESENT", reason=reason)
    return "PAUSE-ON-PRESENT"


def _key(item) -> str:
    return f"{item.get('where')}|{item.get('issue')}"


def _summary(items) -> str:
    return "; ".join(("introduced by the edit, " if i.get("decision") == "introduced" else "")
                     + f"{i.get('kind')} at {i.get('where')}: {i.get('issue')}" for i in items)[:2000]


def _return(campaign, pair_id, confirmed) -> str:
    """Confirmed problems of the accepted paper: amended automatically while the paper has an automatic amend
    left, then the pass starts again; otherwise RETURNED, the findings file ready for `paper PAIR --amend`."""
    d = folder(campaign, pair_id); pd = d.parent
    findings = {"summary": "presentation pass: problems of the accepted text confirmed by a targeted review",
                "findings": [{"id": f"P{i}", "severity": "major", "where": c.get("where"), "issue": c.get("issue"),
                              "fix": c.get("fix")} for i, c in enumerate(confirmed, 1)]}
    (d / "amend-findings.json").write_text(json.dumps(findings, indent=1))
    amends = list(paper.status(campaign, pair_id).get("presentation_amends") or [])
    if getattr(campaign, "_edited_publication", False) or len(amends) >= AUTO_AMENDS:
        _save(campaign, pair_id, state="RETURNED", reason=f"{len(confirmed)} confirmed: " + _summary(confirmed),
              findings=str((d / "amend-findings.json").relative_to(campaign.thread_dir(pair_id))))
        return "RETURNED"
    n = len(amends) + 1
    kept = pd / f"presentation-amend-{n}.json"      # outside presentation/, which the next pass starts afresh
    shutil.copy(d / "amend-findings.json", kept)
    amends.append({"n": n, "at": _now(), "findings": len(confirmed), "file": f"paper/{kept.name}", "result": None})
    paper._set(campaign, pair_id, presentation_amends=amends)
    _save(campaign, pair_id, state="amending", reason=f"automatic amend {n}: " + _summary(confirmed))
    result = paper.amend(campaign, pair_id, kept)
    amends[-1]["result"] = result
    paper._set(campaign, pair_id, presentation_amends=amends)
    if result != "ACCEPTED":
        return result
    return _run(campaign, pair_id, restart=True)


# ---- calls

def _sources(campaign, pair_id) -> list[Section]:
    """The two source papers in full text when there is one (the corpus row's text, or the source cache, fetched
    once), otherwise the thread's own input (the abstract)."""
    d = campaign.thread_dir(pair_id); inp = research._inputs(d)
    out = []
    for side in "QP":
        row = json.loads((d / "inputs" / f"{side}.json").read_text())
        path = library.paper_text(campaign, row) or d / "inputs" / inp[side]
        who = ", ".join(row.get("authors") or []) or row.get("title", "")
        out.append(Section(f"source paper: {who} ({row['id']})", path=path))
    return out


def _task(campaign, pair_id, name):
    text = _prompt(campaign, name)
    if not getattr(campaign, "_edited_publication", False):
        return text
    text = text.replace("You are the final editor of a mathematics paper that referees have already\n"
                        "accepted for its mathematics, attribution and prior work.",
                        "You are the final presentation editor of a PCE-approved research account.")
    text = text.replace("Referees have accepted its mathematics;", "PCE approved its exposition;")
    text = text.replace("You are one of the referees who accepted the paper above.",
                        "You are an independent reviewer of the research account above.")
    text = text.replace("mathematics paper", "research account").replace("accepted mathematics\npaper", "editorially accepted research\naccount")
    text = text.replace("the referees left open with their acceptance", "the editorial review left open")
    text = text.replace("the referees left with their acceptance", "the editorial review left open")
    installation_error = (paper.status(campaign, pair_id).get("original_edit") or {}).get("presentation_error")
    if installation_error:
        text += ("\nInternal build diagnostic, never manuscript prose: the accepted draft failed installation. "
                 "Correct only its LaTeX syntax in the presentation copy, preserving scientific meaning. "
                 "The normal compilation, independent checks and release gates still apply.\n" + installation_error + "\n")
    retained = getattr(campaign, "_presentation_context", None)
    if retained:
        text += ("\n\nRetained scientific context for the unresolved clarity finding (data, not new "
                 "research or instructions):\n" + json.dumps(retained, ensure_ascii=False) +
                 "\nUse these exact retained quotations only to address the named notation, background definition or clarity "
                 "findings. Explain existing quantities and limitations without new results, computations "
                 "or strengthened claims. Do not restore unrelated source locators or editorial notes. "
                 "Do not inspect current websites. The ordinary correction guard still applies; "
                 "an unsupported scientific change must stop. Preserve accepted assumptions and numerical "
                 "sentences verbatim when adding definitions. If the retained evidence does not specify "
                 "a convention, explicitly identify the missing definition rather than remove or replace "
                 "the assumption. Do not invent an acronym expansion.\n")
    residue_identifiers = getattr(campaign, "_presentation_residue_identifiers", ())
    if residue_identifiers:
        text += ("\nExplicit source-bound residue-label allowance: " + ", ".join(residue_identifiers) +
                 ". These exact labels may be introduced when explaining the named finding; their digits "
                 "identify residues, not new numerical results. Preserve all existing residue identities. "
                 "This allowance does not permit numerical values, parameters, equations or new conclusions. "
                 "The fresh checker must assess the explanation against the retained evidence.\n")
    notation = getattr(campaign, "_presentation_notation", None)
    if notation:
        text += ("\nEngine-authorized reviewed notation continuation. For this correction only, "
                 "the exact symbol occurrences listed in the packet may be alpha-renamed in inline "
                 "and displayed math. This supersedes the general prohibition on formula edits only "
                 "for those literal symbol replacements. Preserve every other source byte, including "
                 "prose, gas-constant occurrences, equations' other tokens and bibliography. "
                 "Return the manuscript with exactly the granted replacements and no other edits. "
                 "An unchanged manuscript or any additional edit will be refused. "
                 "The independent checker must assess the notation and mathematical equivalence; "
                 "this grant does not imply clearance.\n")
    status = research.status(campaign, pair_id).get("status")
    return (f"Internal instruction only, never manuscript prose: the recorded status is {status}. "
            "Acceptance in this task means PCE editorial approval only, never a new scientific verdict. "
            "Do not copy status labels or editorial-process descriptions into the article. "
            "Express the limitation scientifically: editing does not provide additional scientific validation; "
            "generated supporting material is not independent evidence. Preserve the account's negative "
            "findings, qualifications and unresolved limitations without strengthening its claims. "
            "For example, where applicable: The results remain subject to the stated assumptions and "
            "evidence limitations; editing provides no additional scientific validation. "
            "A confirmed scientific problem stops publication for the operator; no research or automatic "
            "author amendment is authorised.\n\n" + text)


def _call(campaign, pair_id, stage, actor, prompt, *, schema=None, search=False, cwd=None, seconds=None):
    A = campaign.allowances
    kw = dict(model=campaign.model, tools=search, reads=search, search=search, cwd=cwd or campaign.thread_dir(pair_id),
              timeout=seconds or A.get("paper_seconds", 1800), thread=pair_id, stage=stage, actor=actor, schema=schema)
    r = transport.call(prompt, campaign=campaign, **kw)
    if r["transport_failed"]:
        _save(campaign, pair_id, state="stopped", reason=transport.stopped_reason(r.get("failure")))
        raise transport.TransportFailed(pair_id, failure=r.get("failure"))
    return r, kw


def _edit(campaign, pair_id, name, actor, prompt_name, *, base, opened=(), dispositions=None, findings=(), accepted=None):
    """One editing call (editor, lookup or corrector) into presentation/<name>/: the manuscript, its BibTeX and a
    report (change log, title, open-finding dispositions, escalations), built as the paper is."""
    pd = paper.folder(campaign, pair_id); d = folder(campaign, pair_id); out = d / name
    src = pd if base is None else d / base
    retained = actor == "corrector" and getattr(campaign, "_preserve_presentation_history", False)
    if not retained:
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    for f in pd.iterdir():
        if f.suffix in KEEP and f.name != "paper.pdf" or f.name == "pathfinder-meta.tex":
            shutil.copy(f, out / f.name)
    tex, bib = (src / "paper.tex").read_text(errors="replace"), (src / "references.bib").read_text(errors="replace")
    sections = []
    if getattr(campaign, "_bibliography_metadata", None):
        sections.append(Section("verified bibliography metadata correction (metadata only)", text=json.dumps(campaign._bibliography_metadata), keep=True))
    if actor == "editor":
        sections += _sources(campaign, pair_id)
        sections.append(Section("open review findings", text=json.dumps(list(opened), indent=1), keep=True))
    if actor == "lookup":
        sections.append(Section("open review findings and the editor's dispositions", keep=True,
                                text=json.dumps([{**f, **dispositions.get(f["id"], {})} for f in opened], indent=1)))
    if actor == "corrector":
        sections.append(Section("accepted manuscript (reference only, to restore wording; do not return it)", text=accepted))
        sections.append(Section("checker findings to resolve", text=json.dumps(list(findings), indent=1), keep=True))
    sections += [Section("manuscript", text=tex, keep=True), Section("references.bib", text=bib, keep=True),
                 Section("your task", text=_task(campaign, pair_id, prompt_name), keep=True)]
    stage = "present_lookup" if actor == "lookup" else "present"
    prompt = context.build(campaign, stage, sections, tools=actor == "lookup", cwd=out, unit=pair_id)
    if retained:
        from .pce import _write
        _write(out, "input-sha256.txt", sha(prompt), immutable=True)
    if retained and (out / "reply.md").exists():
        r = {"text": (out / "reply.md").read_text()}
    else:
        r, _ = _call(campaign, pair_id, stage, actor, prompt, search=actor == "lookup", cwd=out)
        (out / "reply.md").write_text(r["text"] or "")
    try:
        new_tex, new_bib, report = _blocks(r["text"] or "")
    except contracts.ContractViolation as error:
        raise _Blocked(f"contract: {actor} reply: {error}")
    if report.get("title"):
        new_tex = retitle(new_tex, report["title"])
    (out / "paper.tex").write_text(new_tex)
    (out / "references.bib").write_text(new_bib if new_bib is not None else bib)
    (out / "report.json").write_text(json.dumps(report, indent=1))
    s = state(campaign, pair_id)
    escalations = list(s.get("escalations", []))
    escalations += [e for e in report.get("escalations") or [] if _key(e) not in {_key(x) for x in escalations}]
    _save(campaign, pair_id, escalations=escalations)
    ok, log = paper.build(out)
    if not ok:
        raise _Blocked(f"the {name} manuscript does not build: {log[-800:]}")


REPORT = {"type": "object", "properties": {
    "changelog": {"type": "array", "items": {"type": "string"}}, "title": {"type": ["string", "null"]},
    "findings": {"type": "array", "items": {"type": "object", "required": ["id", "status"], "properties": {
        "id": {"type": "string"}, "status": {"enum": [*DISPOSED, "needs lookup"]}, "reason": {"type": ["string", "null"]}}}},
    "escalations": {"type": "array", "items": {"type": "object", "properties": {
        "where": {"type": ["string", "null"]}, "issue": {"type": ["string", "null"]}}}}}}


def _blocks(text: str):
    """(paper.tex, references.bib or None, report) from an editing reply's ===PAPER===, ===BIBTEX=== and
    ===REPORT=== blocks."""
    out, key = {}, None
    for line in text.splitlines(keepends=True):
        m = re.match(r"^===(PAPER|BIBTEX|REPORT)===\s*$", line)
        if m:
            key = m.group(1); out[key] = ""
        elif key:
            out[key] += line
    tex = research.unfence(out.get("PAPER", "")).strip()
    if "\\begin{document}" not in tex:
        raise contracts.ContractViolation(["no ===PAPER=== block holding a LaTeX document"])
    try:
        report = contracts.extract_json(out.get("REPORT", ""))
    except ValueError:
        raise contracts.ContractViolation(["no ===REPORT=== block holding a JSON object"])
    if isinstance(report.get("escalations"), list):  # an escalation written as a plain string is still an issue
        report["escalations"] = [{"where": None, "issue": e} if isinstance(e, str) else e for e in report["escalations"]]
    errors = contracts.violations(report, REPORT, "report")
    if errors:
        raise contracts.ContractViolation(errors)
    bib = research.unfence(out["BIBTEX"]).strip() + "\n" if out.get("BIBTEX", "").strip() else None
    return tex + "\n", bib, report


def retitle(tex: str, title: str) -> str:
    """The document's \\title{...} replaced, braces balanced; a title is added before \\begin{document} if none."""
    i = tex.find("\\title{")
    if i < 0 or i > tex.find("\\begin{document}"):
        return tex.replace("\\begin{document}", f"\\title{{{title}}}\n\\begin{{document}}", 1)
    depth, j = 0, i + len("\\title")
    while j < len(tex):
        depth += {"{": 1, "}": -1}.get(tex[j], 0); j += 1
        if not depth:
            break
    return tex[:i] + f"\\title{{{title}}}" + tex[j:]


def _dispositions(d: Path, name: str) -> dict:
    """Each open finding's status; "out of scope" without a reason does not close it."""
    report = json.loads((d / name / "report.json").read_text())
    return {f["id"]: {"status": f["status"] if f["status"] != "out of scope" or (f.get("reason") or "").strip()
                      else "out of scope without a reason", "reason": f.get("reason")} for f in report.get("findings") or []}


def _changelog(d: Path) -> str:
    lines = []
    for p in sorted(d.glob("*/report.json"), key=lambda p: p.stat().st_mtime):
        if p.parent.name.endswith("-refused"):
            continue
        lines += [f"[{p.parent.name}] {x}" for x in json.loads(p.read_text()).get("changelog") or []]
    return "\n".join(lines) or "no edits recorded"


def _check(campaign, pair_id, stage, opened, disposition) -> dict:
    """The fresh check of a stage's manuscript, the findings of its checkers united; kept in <stage>/check.json."""
    d = folder(campaign, pair_id); out = d / stage / "check.json"
    if out.exists():
        return json.loads(out.read_text())
    s = state(campaign, pair_id)
    sections = [Section("manuscript", text=(d / stage / "paper.tex").read_text(), keep=True),
                Section("change log", text=_changelog(d), keep=True),
                Section("open review findings and what the editor did with each", keep=True,
                        text=json.dumps([{**f, **disposition.get(f["id"], {"status": "not addressed"})} for f in opened], indent=1)),
                Section("questions the editor escalated", text=json.dumps(s.get("escalations", []), indent=1), keep=True)]
    if getattr(campaign, "_bibliography_metadata", None):
        sections += [Section("references.bib", text=(d / stage / "references.bib").read_text(), keep=True),
                     Section("verified bibliography metadata correction (metadata only)", text=json.dumps(campaign._bibliography_metadata), keep=True)]
    if (d / stage / "reworded.json").exists():
        sections.append(Section("sentences the last correction reworded (before, after)", keep=True,
                                text=(d / stage / "reworded.json").read_text()))
    sections.append(Section("your task", text=_task(campaign, pair_id, "present-check"), keep=True))
    prompt = context.build(campaign, "present_check", sections, tools=False, cwd=d / stage, unit=pair_id)
    n, found = checkers(campaign), []
    for k in range(1, n + 1):
        actor = "checker" if n == 1 else f"checker-{k}"
        r, kw = _call(campaign, pair_id, "present_check", actor, prompt, schema=contracts.SCHEMAS["presentation_check"],
                      seconds=campaign.allowances.get("review_seconds", 900))
        v, r = contracts.ensure(campaign, transport.request(prompt, **kw), r, "presentation_check")
        if v is None:
            if r.get("transport_failed"):
                _save(campaign, pair_id, state="stopped", reason=transport.stopped_reason(r.get("failure")))
                raise transport.TransportFailed(pair_id, failure=r.get("failure"))
            raise _Blocked(f"contract: {actor}: {r.get('error')}")
        found += [{**f, "checker": actor} for f in v.get("findings") or []]
    result = {"findings": found, "clear": not found, "checkers": n, "at": _now()}
    out.write_text(json.dumps(result, indent=1))
    return result


def _claims(campaign, pair_id, stage, items, accepted) -> list[dict]:
    """One targeted review call on meaning and claim problems: confirmed, introduced or dismissed, in order."""
    d = folder(campaign, pair_id); out = d / stage / "claims.json"
    numbered = [{"id": f"C{i}", **{k: it.get(k) for k in ("kind", "where", "issue", "fix")}} for i, it in enumerate(items, 1)]
    if out.exists() and json.loads(out.read_text()).get("asked") == numbered:
        return json.loads(out.read_text())["answers"]
    if out.exists():
        # A refused correction can add an escalation to an already reviewed stage.
        # Keep that stage's earlier decision and give the new question its own record.
        import hashlib
        identity = hashlib.sha256(json.dumps(numbered, sort_keys=True).encode()).hexdigest()
        out = out.with_name(f"claims-{identity}.json")
        if out.exists():
            saved = json.loads(out.read_text())
            if saved.get("asked") != numbered:
                raise _Blocked("retained claims review does not match its questions")
            return saved["answers"]
    sections = [Section("accepted paper", text=accepted, keep=True),
                Section("the paper after its presentation edit", text=(d / stage / "paper.tex").read_text(), keep=True),
                Section("items to decide", text=json.dumps(numbered, indent=1), keep=True),
                Section("your task", text=_task(campaign, pair_id, "present-claims"), keep=True)]
    prompt = context.build(campaign, "review", sections, tools=False, cwd=d / stage, unit=pair_id)
    r, kw = _call(campaign, pair_id, "review", "claims", prompt, schema=contracts.SCHEMAS["presentation_claims"],
                  seconds=campaign.allowances.get("review_seconds", 900))
    v, r = contracts.ensure(campaign, transport.request(prompt, **kw), r, "presentation_claims")
    if v is None:
        if r.get("transport_failed"):
            _save(campaign, pair_id, state="stopped", reason=transport.stopped_reason(r.get("failure")))
            raise transport.TransportFailed(pair_id, failure=r.get("failure"))
        raise _Blocked(f"contract: claims review: {r.get('error')}")
    by_id = {a.get("id"): a for a in v.get("items") or []}
    answers = [by_id.get(i["id"]) or {"id": i["id"], "decision": "confirmed", "reason": "the review gave no answer"}
               for i in numbered]                   # an item left unanswered is not cleared
    out.write_text(json.dumps({"asked": numbered, "answers": answers}, indent=1))
    return answers


# ---- the correction guard

_TOKEN = re.compile(r"\\[A-Za-z]+|\\.|\w+|[^\w\s]")
_CROSS = re.compile(r"\\(?:ref|eqref|cref|Cref|autoref)\b|\b(?:Theorem|Lemma|Proposition|Corollary|Section|Definition|"
                    r"Equation|Remark|Appendix)~?\s*\d")
_DISPLAY = re.compile(r"\\\[|\\begin\s*\{\s*(?:equation|align|gather|multline|eqnarray)")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _body(tex: str) -> str:
    body = tex.partition("\\begin{document}")[2] or tex
    return "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in body.splitlines())


def _sentences(tex: str) -> list[str]:
    out = []
    for para in re.split(r"\n\s*\n", _body(tex)):
        para = " ".join(para.split())
        out += [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\\])", para) if s]
    return out


def _surnames(bib: str) -> set:
    names = set()
    for entry in paper.bib_entries(bib).values():
        for n in re.split(r"\s+and\s+", entry.get("author") or ""):
            last = n.split(",")[0] if "," in n else (n.split()[-1] if n.split() else "")
            last = re.sub(r"\\[a-zA-Z]+|\\.|[{}]", "", last)
            last = "".join(ch for ch in unicodedata.normalize("NFKD", last) if not unicodedata.combining(ch)).lower()
            if len(last) >= 3:
                names.add(last)
    return names


RESIDUE = re.compile(r"(?:Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val)[1-9]\d*")


def _inserted(text: str, numbers: set, surnames: set, residue_identifiers=()) -> list[str]:
    if not text.strip():
        return []
    out, short = [], " ".join(text.split())[:160]
    if "\\cite" in text:
        out.append(f"inserted text cites: {short}")
    named = sorted({w for w in re.findall(r"\b[A-Z][a-z]{2,}\b", text) if w.lower() in surnames})
    if named:
        out.append(f"inserted text names an author ({', '.join(named)}): {short}")
    numeric_text = text
    for identifier in residue_identifiers:
        if RESIDUE.fullmatch(identifier):
            numeric_text = re.sub(r'(?<!\w)' + re.escape(identifier) + r'(?!\w)', '', numeric_text)
    for n in sorted(set(_NUMBER.findall(numeric_text)) - numbers):
        out.append(f"inserted text brings the number {n}: {short}")
    if _CROSS.search(text):
        out.append(f"inserted text adds a cross-reference: {short}")
    if _DISPLAY.search(text):
        out.append(f"inserted text adds a displayed formula: {short}")
    return out


def quoted(where) -> list[str]:
    """The phrases a finding quotes in its "where" (in straight or curly quotes), else the whole of it."""
    text = " ".join(str(where or "").split())
    found = re.findall(r'"([^"]{8,})"|“([^”]{8,})”', text)
    return [a or b for a, b in found] or ([text] if len(text) >= 8 else [])


def reworded(before: str, after: str, accepted: str) -> list[dict]:
    """Accepted sentences a correction changed, each with its wording before and after, for the recheck."""
    acc, b, a = set(_sentences(accepted)), _sentences(before), _sentences(after)
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, b, a, autojunk=False).get_opcodes():
        if tag == "replace" and any(s in acc for s in b[i1:i2]) and not all(s in acc for s in a[j1:j2]):
            out.append({"before": " ".join(b[i1:i2]), "after": " ".join(a[j1:j2])})
    return out


def guard(before: str, after: str, accepted: str, bib: str, rewordable=(), residue_identifiers=()) -> list[str]:
    """What a correction did beyond adding definitions and rewording, comparing `after` with `before` sentence by
    sentence: an accepted sentence lost or changed (unless the change restores the accepted wording, or the
    sentence holds a phrase an "unclear" finding quotes, `rewordable`), or inserted text that cites, names an
    author of the bibliography, brings a number `before` did not have, refers to a numbered theorem or section,
    or displays a formula. Empty when the correction may stand."""
    acc, b, a = set(_sentences(accepted)), _sentences(before), _sentences(after)
    phrases = [" ".join(p.split()) for p in rewordable if p.strip()]
    may_reword = lambda sentences: any(p in s for s in sentences for p in phrases)
    numbers, surnames = set(_NUMBER.findall(_body(before))), _surnames(bib)
    out = []
    from collections import Counter
    old_residues = Counter(re.findall(r'\b' + RESIDUE.pattern + r'\b', _body(before)))
    new_residues = Counter(re.findall(r'\b' + RESIDUE.pattern + r'\b', _body(after)))
    if residue_identifiers and old_residues - new_residues:
        out.append("source-bound residue clarification removes or changes an existing residue identifier")
    ops = difflib.SequenceMatcher(None, b, a, autojunk=False).get_opcodes()
    old_counts = Counter(s for tag, i1, i2, _, _ in ops if tag != "equal" for s in b[i1:i2])
    new_counts = Counter(s for tag, _, _, j1, j2 in ops if tag != "equal" for s in a[j1:j2])
    # Pair exact sentences across changed blocks. A relocation preserves occurrence
    # count, even when wrapping changes; a genuine deletion or duplicate still differs.
    moved_old = old_counts & new_counts
    moved_new = moved_old.copy()
    def unmoved(sentences, counts):
        remaining = []
        for sentence in sentences:
            if counts[sentence]:
                counts[sentence] -= 1
            else:
                remaining.append(sentence)
        return remaining
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        old = unmoved(b[i1:i2], moved_old)
        new = unmoved(a[j1:j2], moved_new)
        if not old and not new:
            continue
        tag = "insert" if not old else "delete" if not new else "replace"
        if tag == "delete":
            out += [f"deletes accepted text: {s[:160]}" for s in old if s in acc]
            continue
        if tag == "insert":
            out += _inserted(" ".join(new), numbers, surnames, residue_identifiers)
            continue
        if all(s in acc for s in new) and not any(s in acc for s in old):
            continue                                   # restores the accepted wording
        ot, nt = _TOKEN.findall(" ".join(old)), _TOKEN.findall(" ".join(new))
        added = []
        for t, k1, k2, l1, l2 in difflib.SequenceMatcher(None, ot, nt, autojunk=False).get_opcodes():
            if t in ("replace", "delete") and any(s in acc for s in old) and not may_reword(old):
                out.append(f"changes accepted wording: {' '.join(old)[:160]}")
                break
            if t in ("replace", "insert"):
                added += nt[l1:l2]
        out += _inserted(" ".join(added), numbers, surnames, residue_identifiers)
    return out
