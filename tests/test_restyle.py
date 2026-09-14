import json, shutil, subprocess
import pytest
from pathfinder import paper, restyle

LEGACY = r"""\documentclass{article}
\usepackage{amsmath,amssymb,graphicx}
\usepackage[hidelinks]{hyperref}
\newtheorem{theorem}{Theorem}
\newtheorem{conjecture}{Conjecture}
\title{A Title}
\author{ada\\[2pt]
  \small with emmy}
\date{11 September 2026}
\begin{document}
\maketitle
\begin{theorem}t\end{theorem}\begin{conjecture}c\end{conjecture}
\date{this one is in the body and stays}
\bibliographystyle{plain}
\end{document}
"""


def test_restyle_rewrites_only_the_preamble():
    t = restyle.restyle(LEGACY, "pathfinder-paper")
    pre, body = t.split("\\begin{document}")
    assert pre.startswith("\\documentclass{article}\n\\usepackage{pathfinder-paper}\n")
    assert "\\usepackage{graphicx}" in pre and "amsmath" not in pre and "hyperref" not in pre   # provided packages dropped, others kept
    assert "{theorem}" not in pre and "\\newtheorem{conjecture}{Conjecture}" in pre            # provided environments dropped
    assert "\\author" not in pre and "\\date" not in pre and "\\title{A Title}" in pre          # author and date left to the style
    assert "\\date{this one is in the body and stays}" in body and "\\bibliographystyle{plainurl}" in body


def test_restyle_leaves_styled_documents_alone():
    t = "\\documentclass{article}\\usepackage{pathfinder-note}\\title{x}\\begin{document}\\end{document}"
    assert restyle.restyle(t, "pathfinder-note") == t


@pytest.mark.skipif(not shutil.which("latexmk"), reason="latexmk not installed")
def test_restyled_build_keeps_the_source(tmp_path):
    src = LEGACY.replace("\\usepackage{amsmath,amssymb,graphicx}", "\\usepackage{amsmath,amssymb}").replace("\\bibliographystyle{plain}\n", "")
    (tmp_path / "paper.tex").write_text(src)
    ok, log = paper.build(tmp_path, "paper.tex", restyle="pathfinder-paper")
    assert ok, log
    assert (tmp_path / "paper.tex").read_text() == src                                            # the judged source is untouched
    txt = subprocess.run(["pdftotext", str(tmp_path / "paper.pdf"), "-"], capture_output=True, text=True).stdout
    assert "PATHFINDER PAPER" in txt
