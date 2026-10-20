import json
from pathfinder import pce


def test_alias_is_lossless_deterministic_and_keeps_distinct_bytes():
    files = {'sources/z': 'same\r\n', 'draft': 'same\r\n', 'other': 'same\n', 'empty': '', 'empty2': ''}
    prompt, manifest = pce.editor_alias_packet('Allowed input files:\n', files)
    packet = json.loads(prompt.split('Allowed input files:\n')[1])
    restored = {**packet['contents'], **{n: packet['contents'][v] for n, v in packet['aliases'].items()}}
    assert restored == files
    assert manifest['aliases'] == {'empty2': 'empty', 'sources/z': 'draft'}
    assert manifest['expanded_files_sha256'] == {n: pce._sha(t) for n, t in files.items()}
    assert pce.editor_alias_packet('Allowed input files:\n', dict(reversed(list(files.items())))) == (prompt, manifest)
    assert 'not independent evidence' in prompt


def test_alias_does_not_extract_substrings_or_json_subobjects():
    files = {'a': 'contained', 'b': 'prefix contained suffix', 'c': '{"a":"contained"}'}
    _, manifest = pce.editor_alias_packet('head', files)
    assert manifest['aliases'] == {}
    assert set(manifest['contents_sha256']) == set(files)
