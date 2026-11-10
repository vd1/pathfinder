"""An admitted local source stays authoritative without changing shared pool provenance."""
import hashlib
import json
import os
import shlex
import subprocess

import pytest
from pathfinder import config, library, paper_source
from stubcampaign import make

AID = '2206.08401v6'


def fixture(tmp_path):
    source = tmp_path / 'admitted.txt'
    source.write_text('Selected PDF text. arXiv:2401.00001\n')
    record = {'path': 'admitted.txt', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'reason': 'TeX exceeds the deployment flattening limit'}
    c = make(tmp_path, local_sources={AID: record}, prefetch_limit=10)
    pool = library.cache(c)
    pool.mkdir(exist_ok=True)
    (pool / f'{AID}.tex').write_text('Unselected pooled source')
    return c, source


def forbidden(*a, **kw):
    raise AssertionError('retrieval not permitted for the selected source')


def test_local_authority_precedes_pool_and_ignores_unbound_reference_sidecars(tmp_path, monkeypatch):
    c, source = fixture(tmp_path)
    monkeypatch.setattr(paper_source, 'get', forbidden)
    monkeypatch.setattr(paper_source, 'references', forbidden)
    source.with_suffix('.refs.json').write_text('["2401.99999"]')
    assert library.paper_text(c, {'id': AID, 'text': 'absent.txt'}) == source
    assert library.get(c, AID) == source
    assert library.get(c, f'https://arxiv.org/pdf/{AID}.pdf') == source
    assert [r['id'] for r in library.wanted(c, 'Q1P1', [{'id': AID}])] == ['2401.00001']
    assert not source.with_suffix('.source.json').exists()
    assert 'does not assert LaTeX is unavailable' in library.local_rule(c)


def test_other_versions_and_default_still_use_the_pool(tmp_path):
    c, source = fixture(tmp_path)
    c.raw.pop('local_sources')
    assert library.paper_text(c, {'id': AID, 'text': 'admitted.txt'}).suffix == '.tex'
    c, source = fixture(tmp_path)
    other = library.cache(c) / '2206.08401v5.tex'
    other.write_text('Another version')
    assert library.get(c, '2206.08401v5') == other


@pytest.mark.parametrize('damage', ['mutated', 'missing', 'empty'])
def test_bad_selected_file_fails_closed_despite_available_pool(tmp_path, damage):
    c, source = fixture(tmp_path)
    if damage == 'missing':
        source.unlink()
    else:
        source.write_text('Changed' if damage == 'mutated' else '')
    with pytest.raises((ValueError, FileNotFoundError)):
        library.paper_text(c, {'id': AID})
    with pytest.raises((ValueError, FileNotFoundError)):
        library.get(c, AID)


@pytest.mark.parametrize('records', [None, [], {'arXiv:2206.08401v6': {}},
    {AID: {'path': 'x', 'sha256': 'short', 'reason': 'x'}},
    {AID: {'path': 'x', 'sha256': '0'*64, 'reason': ''}}])
def test_bad_configuration_rejected(tmp_path, records):
    with pytest.raises(ValueError):
        make(tmp_path, local_sources=records)


def test_installed_standalone_helper_and_manifest_tampering(tmp_path):
    c, source = fixture(tmp_path)
    d = tmp_path / 'thread'
    args = shlex.split(library.install(c, d))
    env = {**os.environ, 'PATHFINDER_OFFLINE': '1'}
    r = subprocess.run([*args, AID], capture_output=True, text=True, env=env)
    assert r.returncode == 0 and str(source) in r.stdout
    manifest = d / '.pathfinder/local-sources.json'
    manifest.write_text(manifest.read_text() + ' ')
    r = subprocess.run([*args, AID], capture_output=True, text=True, env=env)
    assert r.returncode != 0 and 'manifest changed' in r.stderr


def test_reference_prefetch_fetches_others_only_and_respects_ten(tmp_path, monkeypatch):
    c, source = fixture(tmp_path)
    source.write_text('\n'.join(f'arXiv:2401.{n:05d}' for n in range(20)))
    c.raw['local_sources'][AID]['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    calls = []
    def get(aid, cache, *a, **kw):
        assert aid != AID
        calls.append(aid)
        return source
    monkeypatch.setattr(paper_source, 'get', get)
    monkeypatch.setattr(paper_source, '_fetch', forbidden)
    assert len(library.build(c, 'Q1P1', [{'id': AID}])) == 10
    assert len(calls) == 10


def test_research_and_edit_keep_selected_source(tmp_path, monkeypatch):
    from pathfinder import edit, research
    c, source = fixture(tmp_path)
    (tmp_path / 'Q.jsonl').write_text(json.dumps({'id': AID, 'title': 'Admitted paper',
                                               'abstract': 'Abstract', 'text': 'admitted.txt'}) + '\n')
    monkeypatch.setattr(paper_source, '_fetch', forbidden)
    research.run_thread(c, 'Q1P1')
    d = c.thread_dir('Q1P1')
    assert (d / 'inputs/Q.txt').read_bytes() == source.read_bytes()
    assert not (d / 'inputs/Q.tex').exists()
    assert edit.run(c, 'Q1P1') == 'done'
    assert (d / 'edited/note.pdf').is_file()


def test_known_alias_respects_exact_local_authority(tmp_path, monkeypatch):
    c, source = fixture(tmp_path)
    paper_source._record(library.cache(c), 'doi:10.1234/example', arxiv=AID, found=True)
    monkeypatch.setattr(paper_source, 'get', forbidden)
    assert library.get(c, 'doi:10.1234/example') == source


def test_local_policy_cannot_override_restricted_collection(tmp_path):
    c, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match='restricted collection'):
        library.validate({**c.raw, 'restricted_collection': {}})
