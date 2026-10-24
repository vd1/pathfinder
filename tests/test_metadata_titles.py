"""Source titles are literal metadata, not executable TeX or editable science."""
import json
import shutil
from pathlib import Path
import pytest
from pathfinder import paper, thread, presentation
from stubcampaign import make

TITLE = r'Spectra of Quantized Walks and a $\sqrt{δε}$ rule'


def fixture(tmp_path):
    c = make(tmp_path)
    d = c.thread_dir('Q1P1'); (d / 'inputs').mkdir(parents=True)
    for side, title in [('Q', TITLE), ('P', 'Plain & 50%')]:
        (d / 'inputs' / f'{side}.json').write_text(json.dumps(dict(id='quant-ph/0401053', title=title)))
    return c


def test_literal_escape_does_not_execute_title_commands():
    text = r'$\sqrt{δε}$ \input{secret} \write18{touch x} & % # _ ~ ^'
    result = thread._tex_escape(text)
    assert r'\sqrt' not in result and r'\input' not in result and r'\write18' not in result
    assert result.count(r'\textbackslash{}') == 3
    assert r'\ensuremath{\delta}\ensuremath{\epsilon}' in result
    assert r'\$' in result and r'\{' in result and r'\}' in result
    assert thread._tex_escape('Plain title') == 'Plain title'


def test_stage_refresh_changes_only_title_header_and_is_idempotent(tmp_path):
    c = fixture(tmp_path)
    stage = tmp_path / 'stage'; stage.mkdir()
    old = b'\\pathfinderpair{Q1P1}\r\n\\date{2026-10-23}\r\n\\pathfinderpapers{old}{bad}{old}{bad}\r\n\\pathfinderstatus{preserve}\r\n\\pathfinderprotocol{preserve}\r\n'
    (stage / 'pathfinder-meta.tex').write_bytes(old)
    inputs = {p: p.read_bytes() for p in c.thread_dir('Q1P1').glob('inputs/*')}
    assert thread.refresh_source_titles(c, 'Q1P1', stage)
    after = (stage / 'pathfinder-meta.tex').read_bytes()
    assert old.splitlines(keepends=True)[:2] == after.splitlines(keepends=True)[:2]
    assert old.splitlines(keepends=True)[3:] == after.splitlines(keepends=True)[3:]
    assert after.splitlines(keepends=True)[2].endswith(b'\r\n')
    assert not thread.refresh_source_titles(c, 'Q1P1', stage)
    assert all(p.read_bytes() == b for p, b in inputs.items())


def test_no_header_is_unchanged_and_duplicate_is_rejected(tmp_path):
    c = fixture(tmp_path); stage = tmp_path / 'stage'; stage.mkdir()
    assert not thread.refresh_source_titles(c, 'Q1P1', stage)
    meta = stage / 'pathfinder-meta.tex'; meta.write_text('custom\n')
    assert not thread.refresh_source_titles(c, 'Q1P1', stage)
    meta.write_text('\\pathfinderpapers{}{}{}{}\n' * 2)
    before = meta.read_bytes()
    with pytest.raises(ValueError):
        thread.refresh_source_titles(c, 'Q1P1', stage)
    assert meta.read_bytes() == before


@pytest.mark.skipif(not shutil.which('latexmk'), reason='latexmk required')
def test_real_latex_literal_math_and_injection_are_inert(tmp_path):
    c = fixture(tmp_path)
    q = c.thread_dir('Q1P1') / 'inputs/Q.json'
    obj = json.loads(q.read_text()); obj['title'] += r' \input{NONEXISTENT-PROVENANCE-SENTINEL}'
    q.write_text(json.dumps(obj))
    stage = tmp_path / 'stage'; stage.mkdir()
    (stage / 'paper.tex').write_text(r'\documentclass{article}\usepackage{pathfinder-paper}\title{Metadata test}\begin{document}\maketitle Body.\end{document}')
    thread.write_meta(c, 'Q1P1', stage)
    ok, log = paper.build(stage)
    assert ok, log
    assert (stage / 'paper.pdf').is_file()
