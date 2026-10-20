"""Offline proposal validation. No new canonical grant semantics are simulated."""
import importlib.util
import json
from pathlib import Path

import pytest
from pathfinder import account_register, account_revision, paper, pce

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('proposal', HERE / 'prepare_proposal.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def read(name):
    return json.loads((HERE / name).read_text())


def test_exact_live_bindings_and_unapproved_contract():
    for path, sha in read('bindings.json').items():
        assert p.digest(Path(path).read_bytes()) == sha
    proposal = read('proposal.json')
    assert proposal['apply_authorized'] is False
    assert proposal['live_argv'] is None
    assert proposal['history_contract']['exact_total'] == 23
    for name, sha in proposal['artifacts'].items():
        assert p.digest((HERE / name).read_bytes()) == sha
    assert proposal['review_contract']['passes'] == 1
    assert proposal['review_contract']['fact_checks'] == 1
    assert len(proposal['review_contract']['fresh_roles']) == 5


def test_original_history_and_all_mandates_preserved():
    old = json.loads((p.PARENT / 'request.json').read_text())['changes']
    history = read('cumulative-changes.json')
    delta = read('successor-delta.json')['changes']
    assert history['changes'][:20] == old['changes']
    assert history['changes'][20:] == delta
    assert {d['finding'] for d in delta} == {'P1', 'P2', 'P3'}
    candidate = (HERE / 'account-candidate.tex').read_text()
    assert account_revision._apply((p.PARENT / 'candidate.tex').read_text(), delta) == candidate
    original = json.loads((p.PARENT / 'review/replacement-history.json').read_text())['baseline']
    register = account_register.build(original, history['changes'], candidate)
    assert len(register['records']) == 23
    assert [r['id'] for r in register['records']] == [f'amendment-{i}' for i in range(1,24)]
    assert all(r['status'] == 'surviving' for r in register['records'][-3:])
    with pytest.raises(pce.Changed, match='1-20'):
        account_revision._apply(original, history['changes'])


def test_exact_selected_values_and_exhaustive_omissions():
    raw = (p.THREAD / 'ada/adapt_qsci/result.json').read_bytes()
    data = json.loads(raw)
    selected, omitted = p.projection(data)
    assert read('selected-result.json')['selected'] == selected
    assert read('visibility-manifest.json')['omitted_subtrees'] == omitted
    assert len(data['runs']) == 60
    assert {(r['R'], r['seed'], r['field']) for r in data['runs']} == {
        (R, seed, field) for R in (16,32) for seed in range(10) for field in (0,0.5,1)}
    for run in data['runs']:
        assert len(run['counts']) == 225
        assert all(isinstance(n, int) and n >= 0 for n in run['counts'])
        assert sum(run['counts']) == run['history'][-1]['accepted_shots'] > 0
    # Every leaf appears under exactly one selected or omitted subtree.
    cover = list(selected) + [r['pointer'] for r in omitted if 'pointer' in r]
    for row in omitted:
        if 'array_pointer' in row:
            cover += [row['array_pointer'] + '/' + str(i)
                      for i in range(row['start'], row['end_exclusive'])]
    def check(value, pointer=''):
        matches = [s for s in cover if pointer == s or pointer.startswith(s + '/')]
        if matches:
            assert len(matches) == 1
            return
        assert isinstance(value, (dict, list)) and value
        for k,v in (enumerate(value) if isinstance(value,list) else value.items()):
            check(v, pointer + '/' + str(k).replace('~','~0').replace('/','~1'))
    check(data)
    frozen = json.loads((p.PARENT / 'review/frozen-inputs.json').read_text())
    assert read('visibility-manifest.json')['old_external'] == {
        k:p.digest(v.encode()) for k,v in frozen.items() if k.startswith('sources/external/')}


def test_projection_handles_unicode_escaping_arrays_and_empty_values():
    data = {'runs': [{'field':0,'R':16,'seed':0,'counts':[0,2],
                     'history':[{'accepted_shots':2,'x':'α\r\n'}]}],
            'script_sha256':'x','a/b~c': {'empty':[],'text':'α\r\n'}}
    selected, omitted = p.projection(data)
    assert '/runs/0/counts' in selected
    assert any(x.get('pointer') == '/a~1b~0c' for x in omitted)
    changed = json.loads(json.dumps(data))
    changed['runs'][0]['counts'][1] = 3
    assert p.projection(changed)[0] != selected
    changed = json.loads(json.dumps(data))
    changed['a/b~c']['text'] = 'α\n'
    assert p.projection(changed)[1] != omitted


def test_candidate_real_build(tmp_path):
    (tmp_path / 'paper.tex').write_bytes((HERE / 'account-candidate.tex').read_bytes())
    for bib in (p.PARENT / 'build').glob('*.bib'):
        (tmp_path / bib.name).write_bytes(bib.read_bytes())
    ok, log = paper.build(tmp_path)
    assert ok, log
    assert (tmp_path / 'paper.pdf').stat().st_size > 1000
