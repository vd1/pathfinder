"""Evidence repair is explicit, complete and confined to a new review round."""
import json
import pytest
from pathfinder import cli, pce, pce_recovery, transport
from test_pce_recovery import prepare
from test_pce import script


def packet(tmp_path, c):
    d = c.thread_dir('Q1P1')
    ledger = d / 'ledger.jsonl'
    with ledger.open('a') as f:
        f.write(json.dumps({'seq': 999, 'kind': 'finding', 'actor': 'ada',
                            'text': 'PRIVATE_EDITORIAL_STYLE_RESULTS'}) + '\n')
    support = d / 'ada' / 'rule.txt'
    support.parent.mkdir(exist_ok=True)
    support.write_text('RETAINED_MODEL_SPECIFICATION')
    data = {'version': 1, 'exclude': [{'ledger': 'ledger.jsonl', 'seq': 999,
            'sha256': pce._sha(ledger.read_text()), 'reason': 'editorial build report, no scientific evidence'}],
            'include': [{'path': 'ada/rule.txt', 'sha256': pce._sha(support.read_text()),
                         'purpose': 'existing model specification'}]}
    path = tmp_path / 'projection.json'
    path.write_text(json.dumps(data))
    return path, data


def test_projection_fresh_scope_history_and_idempotent_cli(tmp_path, monkeypatch, capsys):
    c, _ = prepare(tmp_path, monkeypatch)
    path, data = packet(tmp_path, c)
    old = pce.workflow(c, 'Q1P1')
    before = pce_recovery.hashes(old)
    ledger = (c.thread_dir('Q1P1') / 'ledger.jsonl').read_bytes()
    args = ['--root', str(c.root), 'reconcile', 'Q1P1', '--pce-grant', 'clean', '--passes', '1',
            '--fact-checks', '1', '--reason', 'approved evidence repair', '--pce-evidence', str(path), '--repair-only']
    cli.main(args)
    assert 'no calls' in capsys.readouterr().out
    root = pce.workflow(c, 'Q1P1')
    frozen = pce_recovery.hashes(root)
    cli.main(args)
    assert pce_recovery.hashes(root) == frozen
    calls = script(monkeypatch, c)
    assert pce.run(c, 'Q1P1')['status'] == 'accepted'
    for call in calls:
        if call['role'] in ('fact-checker', 'critic'):
            assert 'PRIVATE_EDITORIAL_STYLE_RESULTS' not in call['prompt']
            assert 'RETAINED_MODEL_SPECIFICATION' in call['prompt']
    assert len(list((root / 'visibility').glob('*.json'))) == 5
    assert all(not json.loads(p.read_text())['truncated'] for p in (root / 'visibility').glob('*.json'))
    assert pce_recovery.hashes(old) == before
    assert (c.thread_dir('Q1P1') / 'ledger.jsonl').read_bytes() == ledger
    data['exclude'][0]['reason'] = 'changed authority'
    path.write_text(json.dumps(data))
    with pytest.raises(pce.Changed, match='different parameters'):
        cli.main(args)


@pytest.mark.parametrize('bad', ['hash', 'escape', 'symlink', 'review', 'missing', 'duplicate', 'size', 'truncation'])
def test_invalid_projection_fails_before_new_round(tmp_path, monkeypatch, bad):
    c, _ = prepare(tmp_path, monkeypatch)
    path, data = packet(tmp_path, c)
    d = c.thread_dir('Q1P1')
    if bad == 'hash': data['include'][0]['sha256'] = '0' * 64
    if bad == 'escape': data['include'][0]['path'] = 'ada/../../outside'
    if bad == 'symlink':
        (d / 'ada/link.txt').symlink_to(d / 'ada/rule.txt')
        data['include'][0]['path'] = 'ada/link.txt'
    if bad == 'review': data['include'][0]['path'] = 'ada/reviews/verdict.json'
    if bad == 'missing': data['exclude'][0]['seq'] = 1001
    if bad == 'duplicate': data['include'].append(data['include'][0])
    if bad == 'size': monkeypatch.setattr(transport, 'max_prompt_chars', lambda c: 100)
    if bad == 'truncation': c.raw['pce']['supplement_chars'] = 1
    path.write_text(json.dumps(data))
    before = pce_recovery.hashes(d / 'edited')
    with pytest.raises(pce.Changed):
        pce_recovery.grant(c, 'Q1P1', 'bad', 1, 1, 'repair', evidence=path)
    assert pce_recovery.hashes(d / 'edited') == before


def test_accepted_build_failure_uses_exact_draft_and_still_requires_clearance(tmp_path, monkeypatch):
    from pathfinder import account_release, edit, paper, presentation
    from test_pce_recovery import accepted
    from test_presentation import _script, edited, check
    c = accepted(tmp_path, monkeypatch)
    c.raw['release'] = {'disclosure': 'disclosure.tex'}
    (c.root / 'disclosure.tex').write_text('Prepared with Pathfinder.')
    ed = c.thread_dir('Q1P1') / 'edited'
    accepted_text = (pce.workflow(c, 'Q1P1') / pce.DRAFT).read_text()
    (ed / 'note.tex').write_text('old baseline')
    edit._set(c, 'Q1P1', accepted_note=False, presentation_error='Illegal parameter number',
              pce=str(pce.workflow(c, 'Q1P1').relative_to(c.thread_dir('Q1P1'))))
    before = pce_recovery.hashes(ed)
    view = account_release.view(c, 'Q1P1', create=True)
    assert (paper.folder(view, 'Q1P1') / 'paper.tex').read_text() == accepted_text
    assert json.loads((paper.folder(view, 'Q1P1') / 'acceptance.json').read_text())['installation_pending']
    with pytest.raises(SystemExit, match='not CLEARED'):
        account_release.release(c, 'Q1P1')
    monkeypatch.setattr(paper, '_arxiv_titles', lambda ids: {})
    calls = _script(monkeypatch, {'present/editor': [edited()], 'present_check/checker': [check()]})
    assert account_release.present(c, 'Q1P1') == 'CLEARED'
    assert 'Illegal parameter number' in calls[0].prompt
    assert account_release.release(c, 'Q1P1')['status'] == 'RELEASED'
    after = pce_recovery.hashes(ed)
    assert all(after[k] == v for k, v in before.items())
