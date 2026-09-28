"""Build supervisor-clarified copies without altering the archived outputs."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def replace(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after, 1)


def prepare(arm, pair):
    source = ROOT / arm / "threads" / pair / "paper"
    dest = ROOT / "reviewed" / f"{arm}-{pair}-v2"
    dest.mkdir(parents=True, exist_ok=False)
    text = (source / "paper.tex").read_text()
    bib = (source / "references.bib").read_text()
    digest = hashlib.sha256((source / "paper.tex").read_bytes()).hexdigest()
    review = json.loads((source / "review.json").read_text())[-1]
    assert review["decision"] == "ACCEPT" and review["paper_sha256"] == digest
    text = replace(text, r"\begin{document}",
                   "\\date{28 September 2026; supervisor-clarified version 2}\n\\begin{document}")
    if pair == "Q4P1":
        text = replace(text, "Now retain independent edge draws and personal-flip channels,",
                       "Let \\(G=(V,E)\\) be a finite undirected comparison graph.\n"
                       "Now retain independent edge draws and personal-flip channels,")
    elif pair == "Q1P2":
        text = replace(text, "has empirical utility sum \\(\\widehat C\\) satisfying",
                       "uses actions \\(a_1,\\ldots,a_K,a_{K+1}=a_1\\) and specified signals\n"
                       "\\(s_k\\) with \\(a(s_k)=a_k\\), define\n"
                       "\\[\\widehat C=\\sum_{k=1}^K[\\widehat U(a_k,s_k)"
                       "-\\widehat U(a_{k+1},s_k)].\\]\n"
                       "If \\(\\widehat C\\) satisfies")
    else:
        text = replace(text, r"Let the common tail", r"Let the common upper-tail mass")
        text = replace(text, r"level be \(\alpha\in(0,1)\)", r"be \(\alpha\in(0,1)\)")
        text = replace(text, "under a law where \\(Z=U\\) with probability",
                       "choose \\(0<b<U\\). Under a law where \\(Z=U\\) with probability")
    if arm == "recursive":
        bib = re.sub(r"^\s*url = \{(?:file:)?\.\./inputs/P\.tex\}\s*\n", "\n", bib, flags=re.M)
        for before in ("Supplied unpublished local manuscript", "Supplied unpublished manuscript"):
            if before in bib:
                bib = replace(bib, before, "Supplied unpublished manuscript; package item local-source/P.tex")
                break
        (dest / "local-source").mkdir()
        shutil.copy2(source.parent / "inputs/P.tex", dest / "local-source/P.tex")
    (dest / "paper.tex").write_text(text.rstrip()+"\n")
    (dest / "references.bib").write_text(bib.rstrip()+"\n")
    provenance = {"parent": str(source.relative_to(ROOT)), "parent_sha256": digest,
                  "parent_review": review, "version": 2,
                  "status": "Supervisor clarification; no new independent review",
                  "scope": "Minor definition and local-reference corrections; main claims unchanged"}
    (dest / "provenance.json").write_text(json.dumps(provenance, indent=2)+"\n")
    env = dict(os.environ, TEXINPUTS=str(ROOT / "engine/pathfinder/styles")+os.pathsep)
    build = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
                           cwd=dest, env=env, capture_output=True, text=True)
    (dest / "build.log").write_text(build.stdout+build.stderr)
    build.check_returncode()
    assert hashlib.sha256((source / "paper.tex").read_bytes()).hexdigest() == digest
    print(dest.relative_to(ROOT), "built; archived parent unchanged")


if __name__ == "__main__":
    for arm, pair in (("recursive", "Q4P1"), ("recursive", "Q1P2"), ("repeat", "Q1P1")):
        prepare(arm, pair)
