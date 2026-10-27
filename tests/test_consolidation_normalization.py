"""New consolidation documents are clean; historical paid replies remain immutable."""
import hashlib
import json
import pytest
from pathfinder import research
from pathfinder.thread import normalize_consolidation, unfence
from test_research_revisions import DOC, thread, drive, at_repair


@pytest.mark.parametrize('document', [DOC % 'clean', (DOC % 'CRLF').replace('\n','\r\n'),
                                     (DOC % 'no final newline').rstrip('\n')])
def test_clean_document_is_byte_identical(document):
    assert normalize_consolidation(document) == document


@pytest.mark.parametrize('prefix', ["I've finished checking the sources. Here is the repaired note.\n",
                                    'The chat before `\\documentclass` is gone.\n', '\n\n'])
def test_preamble_cut_at_line_start_not_inline_mention(prefix):
    assert normalize_consolidation(prefix + DOC % 'body' + 'Closing chat.') == DOC % 'body'


def test_fence_result_matches_existing_extraction():
    text = 'Here is the note.\n```latex\n' + DOC % 'body' + '```\n'
    assert normalize_consolidation(text) == unfence(text)


@pytest.mark.parametrize('text', ['Only chat.', 'Inline \\documentclass{article}\\begin{document}x\\end{document}',
                                 '\\documentclass{article}\\begin{document}unfinished',
                                 '\\documentclassFake{article}\\begin{document}x\\end{document}'])
def test_no_complete_line_anchored_document_is_rejected(text):
    assert normalize_consolidation(text) is None


@pytest.mark.parametrize('wrapper', ['chat', 'fence', 'clean'])
def test_new_paid_reply_preserved_and_verifier_binds_normalized_note(tmp_path, monkeypatch, wrapper):
    c,d=thread(tmp_path);at_repair(c,d)
    document=DOC % 'new science unchanged'
    raw={'chat':'I checked \\documentclass inline.\n'+document+'Done.\n',
         'fence':'```latex\n'+document+'```\n','clean':document}[wrapper]
    calls=drive(monkeypatch, {'consolidate':[{'text':raw}],
                             'verify':[{'text':'{"decision":"PAUSE","reason":"fixture","action":""}'}]})
    assert research.run_thread(c,'Q1P1')=='PAUSE'
    assert calls==['consolidate','verify']
    assert (d/'Q1P1.tex').read_bytes()==document.encode()
    saved=json.loads((d/'consolidation/round-1-repair-1.json').read_text())
    if wrapper=='clean':
        assert 'normalization' not in saved
    else:
        assert saved['raw_text']==raw
        assert saved['normalization']==dict(policy='latex-document-v1',source='reply',
                     input_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                     output_sha256=hashlib.sha256(document.encode()).hexdigest())
    verdict=json.loads((d/'Q1P1.verdict.json').read_text())[-1]
    assert verdict['note_sha256']==hashlib.sha256(document.encode()).hexdigest()


def test_prose_blocks_and_preserves_paid_reply_and_old_note(tmp_path,monkeypatch):
    c,d=thread(tmp_path);at_repair(c,d)
    before=(d/'Q1P1.tex').read_bytes();raw='Only inline \\documentclass{article} and \\begin{document}.'
    calls=drive(monkeypatch,{'consolidate':[{'text':raw}]})
    assert research.run_thread(c,'Q1P1')=='BLOCKED'
    assert calls==['consolidate'] and (d/'Q1P1.tex').read_bytes()==before
    assert (d/'consolidate-unreadable.txt').read_text()==raw


def test_retained_preamble_and_prior_verdict_hash_are_unchanged(tmp_path,monkeypatch):
    c,d=thread(tmp_path);at_repair(c,d)
    raw='Historical chat.\n'+DOC % 'historical'
    (d/'Q1P1.tex').write_text(raw)
    prior=dict(round=1,decision='REVISE',reason='old',action='old',note_sha256=hashlib.sha256(raw.encode()).hexdigest())
    verdicts=d/'Q1P1.verdict.json';verdicts.write_text(json.dumps([prior]))
    response=d/'consolidation/round-1-repair-1.json';response.parent.mkdir();response.write_text(json.dumps({'text':raw}))
    original=response.read_bytes()
    calls=drive(monkeypatch,{'verify':[{'text':'{"decision":"PAUSE","reason":"fixture","action":""}'}]})
    assert research.run_thread(c,'Q1P1')=='PAUSE'
    assert calls==['verify'] and response.read_bytes()==original
    assert (d/'Q1P1.tex').read_bytes()==raw.encode()
    assert json.loads(verdicts.read_text())[0]==prior


def test_written_note_fallback_normalizes_and_keeps_both_sources(tmp_path,monkeypatch):
    c,d=thread(tmp_path);at_repair(c,d)
    raw='Writing now.\n'+DOC % 'from file'
    def stage(c,pair,stage,*args,**kwargs):
        if stage=='consolidate':
            (d/'Q1P1.tex').write_text(raw)
            return dict(text='Saved the note.',error=None,transport_failed=False)
        return dict(text='{"decision":"PAUSE"}',error=None,transport_failed=False)
    monkeypatch.setattr(research,'_stage_call',stage)
    assert research.run_thread(c,'Q1P1')=='PAUSE'
    saved=json.loads((d/'consolidation/round-1-repair-1.json').read_text())
    assert saved['raw_text']=='Saved the note.' and saved['raw_note_text']==raw
    assert saved['normalization']['source']=='written-note'
    assert (d/'Q1P1.tex').read_text()==DOC % 'from file'


def test_interrupted_normalized_install_reuses_paid_reply_with_audit(tmp_path,monkeypatch):
    c,d=thread(tmp_path);at_repair(c,d)
    note=d/'Q1P1.tex';before=note.read_bytes();raw='Status message.\n'+DOC % 'new'
    calls=drive(monkeypatch,{'consolidate':[{'text':raw}],
                             'verify':[{'text':'{"decision":"PAUSE"}'}]})
    real=research._atomic_write
    def interrupted(path,data):
        if path==note:raise OSError('interrupted installation')
        return real(path,data)
    monkeypatch.setattr(research,'_atomic_write',interrupted)
    with pytest.raises(OSError,match='interrupted installation'):
        research.run_thread(c,'Q1P1')
    retained=d/'consolidation/round-1-repair-1.json';saved=retained.read_bytes()
    assert json.loads(saved)['raw_text']==raw and note.read_bytes()==before
    monkeypatch.setattr(research,'_atomic_write',real)
    assert research.run_thread(c,'Q1P1')=='PAUSE'
    assert calls==['consolidate','verify'] and retained.read_bytes()==saved
    assert note.read_text()==DOC % 'new'
