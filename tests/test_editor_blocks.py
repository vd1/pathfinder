import json
import pytest
from pathfinder import editor_blocks as eb, editor_packet as ep


def specimen():
    chunks = [('claim %s: α😀 e\u0301 \\"\\r\\n ' % i) * 30 for i in range(5)]
    return {'claims/current.json': 'HEAD\r\n' + '\r\nFIRST\r\n'.join(chunks) + 'TAIL',
            'reviews/current/fact-check.json': 'OTHER\n' + '\nSECOND\n'.join(chunks) + 'END',
            'revisions/history/evidence-diff.json': 'PREFIX' + '\r\nTHIRD\r\n'.join(chunks),
            'sources/external/untouched.json': json.dumps(chunks),
            'state.json': '{"status":"historical"}', 'empty': ''}


def test_exact_escaped_json_unicode_crlf_and_raw_root_only():
    files = specimen()
    payload, header, stats = eb.encode(files)
    assert ep.decode_spans(payload) == files
    assert eb.encode(dict(reversed(list(files.items()))))[0] == payload
    raw_roots = set()
    copies = 0
    for row in header['files']:
        if len(row['segments']) == 1 and 'chars' in row['segments'][0]:
            raw_roots.add(row['path'])
        for segment in row['segments']:
            if 'copy' in segment:
                copies += 1
                assert segment['copy'] in raw_roots and segment['copy'] != row['path']
    assert copies >= 8
    ext = next(r for r in header['files'] if r['path'].startswith('sources/external'))
    assert len(ext['segments']) == 1 and 'chars' in ext['segments'][0]
    assert stats['comparisons'] <= eb.MAX_COMPARISONS and stats['probes'] <= eb.MAX_PROBES


@pytest.mark.parametrize('budget,value', [('MAX_PROBES', 2), ('MAX_COMPARISONS', 7),
    ('MAX_INDEX', 3), ('MAX_SEGMENTS', 2), ('MAX_FILE', 10)])
def test_budget_exhaustion_preserves_every_literal(monkeypatch, budget, value):
    monkeypatch.setattr(eb, budget, value)
    files = specimen(); payload, _, stats = eb.encode(files)
    assert ep.decode_spans(payload) == files
    assert stats['comparisons'] <= eb.MAX_COMPARISONS
    assert stats['probes'] <= eb.MAX_PROBES
    assert stats['indexed'] <= eb.MAX_INDEX


def test_path_order_aliases_overlap_and_nonmatching_normalisation():
    base = 'abc😀\r\n' * 1000
    files = {'claims/a.json': base, 'reviews/b.md': base[9:4000] + base[2:3500],
             'reviews/c.md': base[9:4000] + base[2:3500],
             'claims/normal.json': 'é\r\n'*1000, 'reviews/normal.md': 'e\u0301\n'*1000}
    payload, h, _ = eb.encode(files)
    assert ep.decode_spans(payload) == files
    assert h['aliases']['reviews/c.md'] == 'reviews/b.md'
    row = next(r for r in h['files'] if r['path'] == 'reviews/normal.md')
    assert len(row['segments']) == 1 and 'chars' in row['segments'][0]


def test_repetitive_input_cpu_operation_bounds():
    files = {'claims/a.json': ('a'*1000+'x')*500,
             'reviews/b.json': ('a'*1000+'y')*500}
    payload, _, stats = eb.encode(files)
    assert ep.decode_spans(payload) == files
    assert stats['comparisons'] <= 8_000_000
    assert stats['probes'] <= 2_000_000
    assert stats['indexed'] <= 65_536


def test_legacy_selection_never_larger(monkeypatch):
    files = specimen()
    block, _, _ = eb.encode(files)
    monkeypatch.setattr(eb, 'encode', lambda f: (ep.SPAN_MAGIC+'x'*10_000_000, {}, {}))
    legacy, _ = ep.encode_spans(files)
    monkeypatch.undo()
    selected, _ = ep.encode_spans(files)
    assert len(selected) == min(len(legacy),len(block))
    assert ep.decode_spans(selected) == files
