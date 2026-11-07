"""Bounded exact backward reuse for editor review transport, without parsing content."""
import json

ANCHOR = 32
MIN_COPY = 256
MAX_FILE = 1_000_000
MAX_PROBES = 2_000_000
MAX_COMPARISONS = 8_000_000
MAX_INDEX = 65_536
MAX_BUCKET = 4
MAX_SEGMENTS = 256


def _eligible(name):
    return (name.startswith(('claims/', 'reviews/', 'revisions/'))
            and name.endswith(('.json', '.md', '.tex'))) or name in (
                'drafts/current.tex', 'sources/internal/original.tex', 'sources/internal/baseline.tex')


def encode(files):
    """Copy only from earlier *raw* full bodies; every unmatched code point stays literal.

    Fixed-stride anchors index exact strings, not semantic fields or hashes. Probe and
    character-comparison budgets apply to the entire packet. Exhaustion leaves the
    remainder literal. No self/forward references or copy-of-copy chains are emitted.
    """
    from .editor_packet import SPAN_MAGIC, digest, decode_spans
    canonical, bodies, aliases = {}, {}, {}
    for name, text in sorted(files.items()):
        if text in canonical:
            aliases[name] = canonical[text]
        else:
            canonical[text] = name
            bodies[name] = text
    records, literals, index, roots = [], [], {}, {}
    comparisons = probes = indexed = 0
    for name, text in bodies.items():
        segments, raw = [], []
        cursor = literal_start = 0
        # Preserve the current manuscript as a full raw root for historical versions.
        if _eligible(name) and name != 'drafts/current.tex' and len(text) <= MAX_FILE:
            while (cursor + ANCHOR <= len(text) and probes < MAX_PROBES
                   and comparisons < MAX_COMPARISONS and len(segments) < MAX_SEGMENTS):
                probes += 1
                best = None
                for source, start in index.get(text[cursor:cursor + ANCHOR], ()):
                    base = roots[source]
                    length = ANCHOR
                    while (cursor + length < len(text) and start + length < len(base)
                           and comparisons < MAX_COMPARISONS):
                        comparisons += 1
                        if text[cursor + length] != base[start + length]:
                            break
                        length += 1
                    if length >= MIN_COPY and (best is None or length > best[2]):
                        best = (source, start, length)
                if best:
                    if cursor > literal_start:
                        value = text[literal_start:cursor]
                        raw.append(value)
                        segments.append({'chars': len(value), 'sha256': digest(value)})
                    source, start, length = best
                    segments.append({'copy': source, 'start': start, 'end': start + length})
                    cursor += length
                    literal_start = cursor
                else:
                    cursor += 1
        if literal_start < len(text) or not segments:
            value = text[literal_start:]
            raw.append(value)
            segments.append({'chars': len(value), 'sha256': digest(value)})
        # Index only earlier complete raw bodies, never aliases or reconstructed files.
        if (_eligible(name) and len(segments) == 1 and 'chars' in segments[0]
                and len(text) <= MAX_FILE):
            roots[name] = text
            for pos in range(0, max(0, len(text) - ANCHOR + 1), ANCHOR):
                if indexed >= MAX_INDEX:
                    break
                key = text[pos:pos + ANCHOR]
                bucket = index.setdefault(key, [])
                if len(bucket) < MAX_BUCKET:
                    bucket.append((name, pos))
                    indexed += 1
        records.append({'path': name, 'chars': len(text), 'sha256': digest(text), 'segments': segments})
        literals.extend(raw)
    header = {'files': records, 'aliases': aliases}
    payload = SPAN_MAGIC + json.dumps(header, ensure_ascii=False, separators=(',', ':')) + '\n'
    payload += ''.join(value + '\n' for value in literals)
    if decode_spans(payload) != files:
        raise ValueError('editor exact-block framing failed reconstruction')
    return payload, header, {'probes': probes, 'comparisons': comparisons, 'indexed': indexed}
