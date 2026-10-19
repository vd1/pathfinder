"""Presentation and export of a PCE-accepted account, without commissioning a paper."""
import copy
from . import edit, paper, pce, pce_recovery, presentation, research, runner


def view(campaign, pair_id, *, create=False):
    pce_recovery.preflight(campaign, presentation=True)
    e = edit.status(campaign, pair_id)
    if research.status(campaign, pair_id).get("status") not in research.TERMINAL:
        raise pce.Changed("account presentation requires terminal research")
    ed = campaign.thread_dir(pair_id) / "edited"
    if e.get("imported_from") == "eva2 PCE":
        from . import imported_account
        note, bib, acceptance = imported_account.source(campaign, pair_id, e)
    else:
        if (pce.result(campaign, pair_id).get("status") != "accepted"
                or not e.get("accepted_note") or e.get("presentation_error")):
            raise pce.Changed("account presentation requires completed PCE gates and an installed accepted note")
        note, bib = (ed / "note.tex").read_text(), (ed / "references.bib").read_text()
        if note != (pce.workflow(campaign, pair_id) / pce.DRAFT).read_text():
            raise pce.Changed("the account changed after PCE acceptance")
        acceptance = {"kind": "PCE editorial acceptance",
                      "workflow": str(pce.workflow(campaign, pair_id).relative_to(campaign.thread_dir(pair_id)))}
    identity = pce._sha(note + '\0' + bib)
    root = ed / "publication" / identity
    c = copy.copy(campaign)
    c._publication_folder = root
    c._edited_publication = True
    if not root.exists() and not create:
        raise pce.Changed("run present PAIR --edited before release")
    if create:
        pce._write(root, "acceptance.json", pce._json(acceptance), immutable=True)
        pce._write(root, "paper.tex", note, immutable=True)
        pce._write(root, "references.bib", bib, immutable=True)
        if not (root / "paper.json").exists():
            paper._set(c, pair_id, status="ACCEPTED", acceptance_kind=acceptance["kind"],
                       research_status=research.status(campaign, pair_id).get("status"),
                       pce=acceptance["workflow"],
                       accepted_sha256=pce._sha(note), original_edit=e)
    return c


def present(campaign, pair_id, *, restart=False):
    pce_recovery.preflight(campaign, presentation=True)
    with runner.Lock(campaign.thread_dir(pair_id)):
        if runner.stopped(campaign) or not runner.guard_ok(campaign, inflight=1):
            return "stopped: campaign stop or budget guard"
        c = view(campaign, pair_id, create=True)
        d = presentation.folder(c, pair_id)
        # Preserve a finished/failed presentation attempt before an explicit restart.
        if restart and d.exists():
            archive = d.parent / "presentation-history"
            archive.mkdir(exist_ok=True)
            d.rename(archive / f"attempt-{len(list(archive.iterdir())) + 1:04d}")
        return presentation.run(c, pair_id)


def release(campaign, pair_id, timestamp=None):
    from . import release as exporter
    with runner.Lock(campaign.thread_dir(pair_id)):
        c = view(campaign, pair_id)
        return exporter.run(c, pair_id, timestamp=timestamp)
