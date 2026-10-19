import json
import pytest
from pathfinder import account_present, account_release, account_amend, paper, pce, pce_recovery, presentation
from test_account_present import paused, BEFORE, AFTER, FINDING
from test_presentation import _script, edited, check
from test_pce import script


def retained_context(tmp_path, monkeypatch, *, guarded=False):
    c, args = paused(tmp_path, monkeypatch)
    v = account_release.view(c, 'Q1P1'); d = presentation.folder(v, 'Q1P1')
    # Imported EVA2 accounts need not have native frozen-inputs.json.
    (c.thread_dir('Q1P1') / 'edited/eva2-pce/frozen-inputs.json').unlink()
    source = c.thread_dir('Q1P1') / 'inputs/definition.txt'
    source.write_text('No experimental results are supplied.')
    args['context_path'].write_text(json.dumps({'version': 1, 'contexts': [{
        'source': 'inputs/definition.txt', 'sha256': pce._sha(source.read_text()),
        'quote': source.read_text(), 'where': FINDING['where']}]}))
    if guarded:
        refused = d / 'correct-1-refused'; refused.mkdir()
        (refused / 'guard.json').write_text('["inserted number"]')
        presentation._save(v, 'Q1P1', cycles=1, reason='correction refused by the guard: inserted number')
    return c, args, d


@pytest.mark.parametrize('guarded', [False, True])
def test_retained_context_with_imported_account_preserves_pause_history(tmp_path, monkeypatch, guarded):
    c, args, d = retained_context(tmp_path, monkeypatch, guarded=guarded)
    prior = pce_recovery.hashes(d)
    calls = _script(monkeypatch, {'present/corrector': [edited((BEFORE, AFTER))],
                                  'present_check/checker': [check()]})
    assert account_present.apply(c, 'Q1P1', **args, resume=True) == 'CLEARED'
    assert len(calls) == 2
    assert 'Do not restore unrelated source locators' in calls[0].prompt
    assert all(pce_recovery.hashes(d)[k] == v for k, v in prior.items() if k != 'state.json')
    assert (d / ('correct-2' if guarded else 'correct-1') / 'check.json').exists()


def test_notation_finding_can_continue_without_relaxing_guard(tmp_path, monkeypatch):
    c, args, d = retained_context(tmp_path, monkeypatch)
    checked = json.loads((d / 'pass/check.json').read_text())
    checked['findings'][0]['kind'] = 'notation'
    (d / 'pass/check.json').write_text(json.dumps(checked))
    _script(monkeypatch, {'present/corrector': [edited((BEFORE, BEFORE + ' New numerical result 987654.'))]})
    assert account_present.apply(c, 'Q1P1', **args, resume=True) == 'PAUSE-ON-PRESENT'
    assert 'guard' in json.loads((d / 'state.json').read_text())['reason']
    assert account_present.apply(c, 'Q1P1', **args, resume=True) == 'PAUSE-ON-PRESENT'


@pytest.mark.parametrize('bad', ['hash', 'escape', 'operational', 'quote', 'substantive'])
def test_bad_retained_context_fails_before_grant(tmp_path, monkeypatch, bad):
    c, args, d = retained_context(tmp_path, monkeypatch)
    data = json.loads(args['context_path'].read_text()); entry = data['contexts'][0]
    if bad == 'hash': entry['sha256'] = '0' * 64
    if bad == 'escape': entry['source'] = 'inputs/../../../secret'
    if bad == 'operational': entry['source'] = 'ada/reviews/result.json'
    if bad == 'quote': entry['quote'] = 'Unretained claim.'
    if bad == 'substantive':
        checked = json.loads((d / 'pass/check.json').read_text())
        checked['findings'][0]['kind'] = 'claim'
        (d / 'pass/check.json').write_text(json.dumps(checked))
    args['context_path'].write_text(json.dumps(data))
    before = pce_recovery.hashes(d.parent)
    with pytest.raises(pce.Changed):
        account_present.apply(c, 'Q1P1', **args)
    assert before == pce_recovery.hashes(d.parent)


def test_first_amendment_review_transports_joint_support_and_checks_hash(tmp_path, monkeypatch):
    from test_account_amend import packet
    c, ed, candidate, args = packet(tmp_path)
    source = c.thread_dir('Q1P1') / 'ada/model.json'
    source.parent.mkdir(exist_ok=True); source.write_text('{"definition": "retained joint evidence", "review": "PRIVATE_OLD_REVIEW"}')
    projection = {'version': 1, 'exclude': [], 'include': [{'path': 'ada/model.json',
        'sha256': '0' * 64, 'purpose': 'whole-account scientific coverage', 'json_fields': ['definition']}]}
    path = args['packet'] / 'evidence-projection.json'; path.write_text(json.dumps(projection))
    before = pce_recovery.hashes(ed)
    with pytest.raises(pce.Changed, match='hash differs'):
        account_amend.apply(c, 'Q1P1', **args)
    assert before == pce_recovery.hashes(ed)
    projection['include'][0]['sha256'] = pce._sha(source.read_text()); path.write_text(json.dumps(projection))
    calls = script(monkeypatch, c)
    assert 'accepted;' in account_amend.apply(c, 'Q1P1', **args, resume=True)
    for call in calls:
        if call['role'] in ('critic', 'fact-checker'):
            assert 'retained joint evidence' in call['prompt']
            assert 'PRIVATE_OLD_REVIEW' not in call['prompt']
    assert all(pce_recovery.hashes(ed)[k] == v for k, v in before.items())
    assert len(list((ed / 'account-amendments/definitions/review/visibility').glob('*.json'))) == 5
