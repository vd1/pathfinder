import importlib.util
import json
from pathlib import Path
import pytest
from pathfinder import library, research, stub, transport, thread, pce
from stubcampaign import make

spec = importlib.util.spec_from_file_location('atlas_assess', Path(__file__).with_name('assess.py'))
assessment = importlib.util.module_from_spec(spec); spec.loader.exec_module(assessment)
REPLY = {'rating': {'strongest_result': 'Bounded contribution', 'nonobvious': 'somewhat',
                   'level': 'journal', 'score': 5, 'reason': 'Specialist result'},
         'novelty': {'status': 'undetermined', 'basis': 'Only the supplied inspected papers',
                     'limitations': 'Search coverage is incomplete'}}


def terminal(tmp_path):
    c = make(tmp_path / 'run', prefetch_limit=0)
    d = thread.prepare(c, 'Q1P1')
    (d / 'Q1P1.tex').write_text('Complete final note')
    (d / 'Q1P1.verdict.json').write_text('{"verdict":"DRAFT"}')
    thread._set(c, 'Q1P1', status='DRAFT')
    context = tmp_path / 'context.txt'; context.write_text('Dated queries and evidence supplied by operator.')
    return c, d, context


def test_assessment_once_bound_and_no_science_changes(tmp_path, monkeypatch):
    c, d, context = terminal(tmp_path)
    before = {p: p.read_bytes() for p in d.rglob('*') if p.is_file()}
    calls = []
    def reply(c, req):
        calls.append(req)
        assert req.model == 'gpt-6.1-sol' and not req.tools and not req.search
        assert c.raw['codex']['reasoning_effort'] == 'medium'
        assert c.raw['refusal_fallback'] is None
        assert 'not an independent web search' in req.prompt
        return json.dumps(REPLY)
    monkeypatch.setattr(stub, 'reply', reply)
    assert assessment.assess(c, 'Q1P1', context)['status'] == 'prepared'
    result = assessment.assess(c, 'Q1P1', context, True)
    assert result['status'] == 'complete'
    assert assessment.assess(c, 'Q1P1', context, True) == result
    assert len(calls) == 1 and len(transport.receipts(c)) == 1
    assert all(p.read_bytes() == b for p, b in before.items())
    context.write_text('Different evidence')
    with pytest.raises(pce.Changed):
        assessment.assess(c, 'Q1P1', context, True)
    assert len(calls) == 1


def test_failed_result_never_repeats(tmp_path, monkeypatch):
    c, d, context = terminal(tmp_path); calls = []
    def reply(c, req):
        calls.append(req); return '{}'
    monkeypatch.setattr(stub, 'reply', reply)
    for _ in range(2):
        with pytest.raises(ValueError):
            assessment.assess(c, 'Q1P1', context, True)
    assert len(calls) == 1


def test_stop_and_uncertain_dispatch(tmp_path):
    c, d, context = terminal(tmp_path)
    (c.root / 'stop.json').write_text('{"reason":"operator stop"}')
    assert assessment.assess(c, 'Q1P1', context, True)['status'] == 'stopped'
    (c.root / 'stop.json').unlink()
    (d/'post-research-assessment/dispatch.json').write_text('{}')
    with pytest.raises(ValueError, match='uncertain'):
        assessment.assess(c, 'Q1P1', context, True)
    assert not transport.receipts(c)


def test_full_cards_no_scan_pool_hit_no_fetch(tmp_path, monkeypatch):
    pool = tmp_path / 'pool';pool.mkdir()
    (pool / '2401.00001.tex').write_text('Existing pooled LaTeX')
    c = make(tmp_path / 'run', prefetch_limit=0, source_cache=str(pool),
             codex={'filesystem_profile': {'read': [str(pool)]}})
    for side in 'QP':
        path = tmp_path / f'{side}-card.md';path.write_text('FULL CURRENT CARD ' + side)
        rows = [json.loads(x) for x in c.path(side+'.jsonl').read_text().splitlines()]
        rows[0]['text'] = str(path)
        c.path(side+'.jsonl').write_text(json.dumps(rows[0])+'\n')
    def forbidden(*a, **k): raise AssertionError('unexpected network access')
    monkeypatch.setattr(library.net, 'urlopen', forbidden)
    d = thread.prepare(c, 'Q1P1')
    assert (d/'inputs/Q.md').read_text() == 'FULL CURRENT CARD Q'
    assert not c.path('scan.jsonl').exists()
    assert not (d/'inputs/pair-context.md').exists()
    assert library.get(c, '2401.00001') == pool/'2401.00001.tex'
    c.backend = 'codex'
    command = transport._command(c,'gpt-6-astra',True,True,d)
    assert any('permissions.pathfinder.filesystem' in x and str(pool) in x for x in command)
    assert library.install(c,d).find(str(pool)) >= 0


def test_exact_frozen_import():
    assert Path(research.__file__).resolve().is_relative_to('/private/tmp/pathfinder-research-only-b18d4dd')


def test_budget_provider_and_cap_prevent_dispatch(tmp_path, monkeypatch):
    c,d,context=terminal(tmp_path)
    calls=[]
    monkeypatch.setattr(stub,'reply',lambda *a: calls.append(a))
    monkeypatch.setattr(assessment.exhaustion,'active',lambda *a: {'reason':'quota'})
    assert assessment.assess(c,'Q1P1',context,True)['status']=='provider_paused'
    monkeypatch.setattr(assessment.exhaustion,'active',lambda *a: None)
    monkeypatch.setattr(assessment.runner,'guard_ok',lambda *a,**k: False)
    assert assessment.assess(c,'Q1P1',context,True)['status']=='stopped'
    c.raw['max_prompt_chars']=100
    with pytest.raises(ValueError,match='transport cap'):
        assessment.assess(c,'Q1P1',context,True)
    assert not calls and not transport.receipts(c)


def test_live_and_changed_note_refused(tmp_path,monkeypatch):
    c,d,context=terminal(tmp_path)
    thread._set(c,'Q1P1',status='running')
    with pytest.raises(ValueError,match='terminal'):
        assessment.assess(c,'Q1P1',context)
    thread._set(c,'Q1P1',status='DRAFT')
    assessment.assess(c,'Q1P1',context)
    (d/'Q1P1.tex').write_text('different note')
    with pytest.raises(pce.Changed):
        assessment.assess(c,'Q1P1',context,True)
    assert not transport.receipts(c)
