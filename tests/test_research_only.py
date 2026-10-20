"""Native restricted research coordination, with real stages and stub transport only."""
import hashlib
import json
from pathlib import Path

import pytest
from pathfinder import collection, config, coordinator, edit, health, runner, transport, thread
from stubcampaign import make


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def six(tmp_path, monkeypatch):
    monkeypatch.setattr(collection, 'RUNTIME_ROOTS', ())
    monkeypatch.delenv('PATHFINDER_CODEX', raising=False)
    pool = tmp_path / 'sources'; pool.mkdir()
    source = pool / 'paper.tex'; source.write_text('Admitted historical source only.')
    children = {}
    for i in range(6):
        name = f'child{i}'
        c = make(tmp_path / name, parent='..')
        cards = tmp_path / f'cards{i}'; cards.mkdir()
        inputs = {}
        for side, row in zip('QP', thread._pair(c, 'Q1P1')):
            p = cards / f'{side}.md'; p.write_text(f'Primitive {side}.')
            inputs[side] = dict(id=row['id'], title=row['title'], path=str(p), sha256=sha(p), source_ids=['paper'])
        manifest = tmp_path / f'collection{i}.json'
        manifest.write_text(json.dumps(dict(version=1, pair_id='Q1P1', pool_roots=[str(pool)],
            cutoff_utc='2020-01-01T00:00:00Z', inputs=inputs,
            sources=[dict(id='paper', version='v1', first_appearance_utc='2018-01-01T00:00:00Z',
                version_appearance_utc='2019-01-01T00:00:00Z', files=[dict(path=str(source), sha256=sha(source))])])))
        c.raw['restricted_collection'] = dict(manifest=str(manifest), sha256=sha(manifest))
        children[name] = c
    group = tmp_path / 'budget-group.json'
    group.write_text(json.dumps(dict(version=1, campaigns=[str(c.root) for c in children.values()],
                                    budget=dict(calls=100, input_tokens=10000000, output_tokens=10000000))))
    for c in children.values():
        c.raw['budget_group'] = dict(manifest=str(group), sha256=sha(group))
        c.path('campaign.json').write_text(json.dumps(c.raw))
    path = tmp_path / 'schedule.json'
    path.write_text(json.dumps(dict(arms={n:n for n in children}, stages=['research'],
                                   schedule=[dict(arm=n,pair='Q1P1') for n in children])))
    return path, children, source


def receipts(children):
    return {n: c.path('receipts.jsonl').read_bytes() if c.path('receipts.jsonl').exists() else b''
            for n,c in children.items()}


def forbid_editor(*a, **kw):
    pytest.fail('research-only execution reached editorial work')


def test_six_restricted_children_sequence_restart_and_receipt_preservation(six, monkeypatch):
    path, children, source = six
    before_source = sha(source)
    monkeypatch.setattr(edit, 'run', forbid_editor)
    from pathfinder import actionability, paper
    monkeypatch.setattr(actionability, 'run', forbid_editor)
    monkeypatch.setattr(paper, 'run', forbid_editor)
    seen = []
    real = collection.check_request
    def check(c, request):
        seen.append(c.root.name)
        return real(c, request)
    monkeypatch.setattr(collection, 'check_request', check)
    real_pair = runner.run_pair
    def interrupted(c, pair, **kw):
        out = real_pair(c, pair, **kw)
        if c.root.name == 'child2':
            path.with_name('stop.json').write_text('{"reason":"operator test interruption"}')
        return out
    monkeypatch.setattr(runner, 'run_pair', interrupted)
    assert coordinator.run(path, interval=.01, heartbeat=.02)['status'] == 'stopped'
    old = receipts(children)
    assert all(old[n] for n in list(children)[:3])
    assert not any(old[n] for n in list(children)[3:])
    path.with_name('stop.json').unlink()  # explicit operator resume in the copy
    monkeypatch.setattr(runner, 'run_pair', real_pair)
    assert coordinator.run(path, interval=.01, heartbeat=.02)['status'] == 'complete'
    final = receipts(children)
    assert all(final[n] == old[n] for n in list(children)[:3])
    assert list(dict.fromkeys(seen)) == list(children)
    for c in children.values():
        assert runner.pair_complete(c, 'Q1P1', ('research',))
        assert not runner.pair_complete(c, 'Q1P1', ('research', 'edit'))
        assert not (c.thread_dir('Q1P1') / 'edited').exists()
        assert json.loads(c.path('runner.json').read_text())['stages'] == ['research']
        assert {r['stage'] for r in transport.receipts(c)} <= {'peer','consolidate','verify'}
    assert coordinator.run(path, interval=.01, heartbeat=.02)['status'] == 'complete'
    assert receipts(children) == final and sha(source) == before_source


def test_shared_unresolved_call_refuses_before_research(six):
    path, children, _ = six
    active = children['child5'].path('active-calls'); active.mkdir()
    (active / 'unresolved.json').write_text('{}')
    result = coordinator.run(path, interval=.01, heartbeat=.02)
    assert result['status'] == 'censored'
    assert all(not any(r['outcome'] not in transport.UNCHARGED for r in transport.receipts(c))
               for c in children.values())
    assert (active / 'unresolved.json').read_text() == '{}'


def test_parent_stop_and_child_ownership(six):
    path, children, _ = six
    path.with_name('stop.json').write_text('{"reason":"operator"}')
    assert coordinator.run(path, interval=.01, heartbeat=.02)['status'] == 'stopped'
    assert not any(receipts(children).values())
    path.with_name('stop.json').unlink()
    c = children['child0']
    with runner.Lock(c.thread_dir('Q1P1')):
        with pytest.raises(RuntimeError, match='held'):
            runner.run_pair(c, 'Q1P1', stages=('research',), interval=.01)
    assert not any(receipts(children).values())


def test_cli_explicit_mode_and_legacy_default(tmp_path, monkeypatch):
    from pathfinder import cli
    c = make(tmp_path)
    seen = []
    monkeypatch.setattr(runner, 'run', lambda c, **kw: seen.append(kw) or 0)
    assert cli.main(['--root', str(c.root), 'research', '--research-only', '--pairs', 'Q1P1']) == 0
    assert cli.main(['--root', str(c.root), 'research']) == 0
    assert seen[0]['research_only'] is True and seen[0]['pairs'] == ['Q1P1']
    assert seen[1]['research_only'] is False


def test_invocation_mode_does_not_leak_and_default_still_edits(tmp_path):
    c = make(tmp_path)
    assert runner.run(c, interval=.01, pairs=['Q1P1'], research_only=True) == 0
    assert not hasattr(c, '_research_only') and not hasattr(c, 'selection')
    assert not runner.pair_complete(c, 'Q1P1', ('research','edit'))
    assert runner.run(c, interval=.01, pairs=['Q1P1']) == 0
    assert runner.pair_complete(c, 'Q1P1', ('research','edit'))


@pytest.mark.parametrize('kind', ['extra', 'foreign-lock', 'symlink-lock'])
def test_fresh_collection_exception_only_admits_own_regular_lock(six, kind):
    _, children, source = six
    c = children['child0']; d = c.thread_dir('Q1P1'); d.mkdir(parents=True)
    if kind == 'extra':
        (d / 'old-science.txt').write_text('not admitted')
    elif kind == 'foreign-lock':
        (d / 'lock').write_text('999999999')
    else:
        (d / 'lock').symlink_to(source)
    with pytest.raises(collection.Refused, match='fresh thread'):
        thread.prepare(c, 'Q1P1')
    assert not (d / 'inputs').exists()


def test_shared_budget_cap_survives_restart(six):
    path, children, _ = six
    group = path.with_name('budget-group.json')
    doc = json.loads(group.read_text()); doc['budget']['calls'] = 1
    group.write_text(json.dumps(doc))
    for c in children.values():
        c.raw['budget_group']['sha256'] = sha(group)
        c.path('campaign.json').write_text(json.dumps(c.raw))
    assert coordinator.run(path, interval=.01, heartbeat=.02)['status'] == 'censored'
    charged = lambda: sum(r['outcome'] not in transport.UNCHARGED for c in children.values()
                          for r in transport.receipts(c))
    assert charged() == 1
    before = receipts(children)
    assert coordinator.run(path, interval=.01, heartbeat=.02)['status'] == 'censored'
    assert receipts(children) == before and charged() == 1


@pytest.mark.parametrize('status', ['DRAFT','PAUSE','PAUSE-ON-ITERATE','PAUSE-ON-REVISE'])
def test_research_terminal_completion_needs_no_edit(tmp_path, status):
    c = make(tmp_path)
    c.thread_dir('Q1P1').mkdir(parents=True)
    thread._set(c, 'Q1P1', status=status)
    assert runner.pair_complete(c, 'Q1P1', ('research',))
    assert not runner.pair_complete(c, 'Q1P1', ('research','edit'))
