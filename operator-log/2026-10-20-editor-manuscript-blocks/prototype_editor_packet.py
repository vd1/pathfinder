"""Reversible raw framing for complete editor inputs, with whole-file aliases."""
import hashlib
import json
import difflib
import re

MAGIC = "PATHFINDER-EDITOR-FILES-V1\n"


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def encode(files):
    canonical, contents, aliases = {}, {}, {}
    for name, text in sorted(files.items()):
        if text in canonical:
            aliases[name] = canonical[text]
        else:
            canonical[text] = name
            contents[name] = text
    header = {
        "files": [{"path": n, "chars": len(t), "sha256": digest(t)} for n, t in contents.items()],
        "aliases": aliases,
    }
    payload = MAGIC + json.dumps(header, ensure_ascii=False, separators=(",", ":")) + "\n"
    payload += "".join(text + "\n" for text in contents.values())
    if decode(payload) != files:
        raise ValueError("editor framing failed exact reconstruction")
    return payload, header


def decode(payload):
    """Consume declared Unicode-code-point lengths, never delimiter-search file bodies."""
    if not payload.startswith(MAGIC):
        raise ValueError("invalid editor framing version")
    line, separator, body = payload[len(MAGIC):].partition("\n")
    if not separator:
        raise ValueError("missing editor framing header")
    header = json.loads(line)
    if (not isinstance(header, dict) or set(header) != {"files", "aliases"}
            or not isinstance(header["files"], list) or not isinstance(header["aliases"], dict)):
        raise ValueError("invalid editor framing header")
    contents, offset = {}, 0
    for record in header["files"]:
        if not isinstance(record, dict) or set(record) != {"path", "chars", "sha256"}:
            raise ValueError("invalid editor file record")
        name, count = record["path"], record["chars"]
        if (not isinstance(name, str) or name in contents or type(count) is not int or count < 0):
            raise ValueError("invalid editor file identity or length")
        text = body[offset:offset + count]
        if (len(text) != count or body[offset + count:offset + count + 1] != "\n"
                or digest(text) != record["sha256"]):
            raise ValueError("editor file length or hash differs")
        contents[name] = text
        offset += count + 1
    if offset != len(body):
        raise ValueError("unexpected trailing editor framing content")
    expanded = dict(contents)
    for name, target in header["aliases"].items():
        if not isinstance(name, str) or not isinstance(target, str) or name in expanded or target not in contents:
            raise ValueError("invalid editor file alias")
        expanded[name] = contents[target]
    return expanded


def packet(head, shown, alias_chars):
    from . import pce
    payload, header = encode(shown)
    instruction = (
        "\nLossless raw-file transport v1. After 'Allowed input files:' comes "
        "PATHFINDER-EDITOR-FILES-V1, then a single JSON index, then the complete raw file bodies "
        "in index order. Each index record gives path, Unicode-code-point length and UTF-8 SHA-256. "
        "Exactly one framing newline follows each body; embedded newlines and marker-like text "
        "belong to that body. Read the raw text directly, without JSON-unescaping it. "
        "Aliases have exactly their named canonical file's full contents; retain each path's "
        "provenance/status, and do not treat duplicates as independent evidence. "
        "All scoped files are present, with no truncation, summaries, fetches or tools needed. "
        "Required outputs and scientific scope are unchanged.\n")
    framed_transport = pce.TRANSPORT.replace("The JSON mapping", "The indexed raw-file packet")
    framed_head = head.replace(pce.TRANSPORT, framed_transport, 1)
    return instruction + framed_head + payload, {
        "encoding": "raw-length-file-alias-v1",
        "aliases": header["aliases"],
        "file_frames": header["files"],
        "contents_sha256": {r["path"]: r["sha256"] for r in header["files"]},
        "expanded_files_sha256": {n: digest(t) for n, t in sorted(shown.items())},
        "expanded_json_sha256": digest(pce._json(shown)),
        "original_prompt_sha256": digest(head + pce._json(shown)),
        "original_prompt_chars": len(head + pce._json(shown)),
        "json_alias_prompt_chars": alias_chars,
        "raw_unique_chars": sum(r["chars"] for r in header["files"]),
        "payload_sha256": digest(payload),
    }


SPAN_MAGIC = "PATHFINDER-EDITOR-SPANS-V1\n"


def _manuscript_path(name):
    return name in ("drafts/current.tex", "sources/internal/baseline.tex",
                    "sources/internal/original.tex") or bool(
        re.fullmatch(r"revisions/history/[^/]+-draft\.tex", name))


def _manuscript_blocks(source, base, text):
    """Bounded exact line matches, with original Unicode/CRLF offsets retained."""
    if max(len(base), len(text)) > 200_000:
        return None
    a, b = base.splitlines(keepends=True), text.splitlines(keepends=True)
    if max(len(a), len(b)) > 2048:
        return None
    starts_a, starts_b = [0], [0]
    for line in a:
        starts_a.append(starts_a[-1] + len(line))
    for line in b:
        starts_b.append(starts_b[-1] + len(line))
    matches = []
    for i, j, count in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        start, end = starts_b[j], starts_b[j + count]
        if end - start >= 256:
            matches.append((starts_a[i], start, end))
    if not matches or len(matches) > 64:
        return None
    segments, literals, cursor = [], [], 0
    for source_start, start, end in matches:
        if cursor < start:
            value = text[cursor:start]
            segments.append({'chars': len(value), 'sha256': digest(value)})
            literals.append(value)
        assert base[source_start:source_start + end - start] == text[start:end]
        segments.append({'copy': source, 'start': source_start,
                         'end': source_start + end - start})
        cursor = end
    if cursor < len(text):
        value = text[cursor:]
        segments.append({'chars': len(value), 'sha256': digest(value)})
        literals.append(value)
    return segments, literals


def _segment_cost(segments, literals):
    return len(json.dumps(segments, ensure_ascii=False, separators=(',', ':'))) + sum(
        len(value) + 1 for value in literals)


def encode_spans(files):
    """Reuse exact spans of earlier files; multi-block matching is manuscript-only."""
    canonical, bodies, aliases = {}, {}, {}
    for name, text in sorted(files.items()):
        if text in canonical:
            aliases[name] = canonical[text]
        else:
            canonical[text] = name
            bodies[name] = text
    records, literals, previous = [], [], {}
    for name, text in bodies.items():
        best = None
        for source, base in previous.items():
            prefix = 0
            for a, b in zip(text, base):
                if a != b:
                    break
                prefix += 1
            suffix = 0
            limit = min(len(text), len(base)) - prefix
            while suffix < limit and text[len(text)-1-suffix] == base[len(base)-1-suffix]:
                suffix += 1
            # Avoid reference overhead for small shared punctuation or labels.
            if prefix + suffix > 512 and (best is None or prefix + suffix > best[0]):
                best = (prefix + suffix, source, base, prefix, suffix)
        segments, file_literals = [], []
        if best:
            _, source, base, prefix, suffix = best
            if prefix:
                segments.append({'copy': source, 'start': 0, 'end': prefix})
            middle = text[prefix:len(text)-suffix if suffix else len(text)]
        else:
            middle = text
        if middle or not best:
            segments.append({'chars': len(middle), 'sha256': digest(middle)})
            file_literals.append(middle)
        if best and suffix:
            segments.append({'copy': source, 'start': len(base)-suffix, 'end': len(base)})
        if _manuscript_path(name):
            for source, base in previous.items():
                if not _manuscript_path(source):
                    continue
                candidate = _manuscript_blocks(source, base, text)
                if candidate and _segment_cost(*candidate) < _segment_cost(segments, file_literals):
                    segments, file_literals = candidate
        literals.extend(file_literals)
        records.append({'path': name, 'chars': len(text), 'sha256': digest(text), 'segments': segments})
        previous[name] = text
    header = {'files': records, 'aliases': aliases}
    payload = SPAN_MAGIC + json.dumps(header, ensure_ascii=False, separators=(',', ':')) + '\n'
    payload += ''.join(text + '\n' for text in literals)
    if decode_spans(payload) != files:
        raise ValueError('editor span framing failed exact reconstruction')
    return payload, header


def decode_spans(payload):
    """Expand backward-only, half-open Unicode spans and verify every complete file."""
    if not payload.startswith(SPAN_MAGIC):
        raise ValueError('invalid editor span version')
    line, separator, body = payload[len(SPAN_MAGIC):].partition('\n')
    if not separator:
        raise ValueError('missing editor span index')
    header = json.loads(line)
    if (not isinstance(header, dict) or set(header) != {'files', 'aliases'}
            or not isinstance(header['files'], list) or not isinstance(header['aliases'], dict)):
        raise ValueError('invalid editor span index')
    contents, offset = {}, 0
    for record in header['files']:
        if not isinstance(record, dict) or set(record) != {'path', 'chars', 'sha256', 'segments'}:
            raise ValueError('invalid editor span file')
        name, count = record['path'], record['chars']
        if (not isinstance(name, str) or name in contents or type(count) is not int or count < 0
                or not isinstance(record['segments'], list) or not record['segments']):
            raise ValueError('invalid editor span identity')
        parts = []
        for segment in record['segments']:
            if not isinstance(segment, dict):
                raise ValueError('invalid editor span segment')
            if set(segment) == {'copy', 'start', 'end'}:
                source, start, end = segment['copy'], segment['start'], segment['end']
                if (not isinstance(source, str) or source not in contents
                        or type(start) is not int or type(end) is not int
                        or not 0 <= start < end <= len(contents[source])):
                    raise ValueError('invalid editor backward span')
                parts.append(contents[source][start:end])
            elif set(segment) == {'chars', 'sha256'}:
                length = segment['chars']
                if type(length) is not int or length < 0:
                    raise ValueError('invalid editor literal length')
                value = body[offset:offset+length]
                if (len(value) != length or body[offset+length:offset+length+1] != '\n'
                        or digest(value) != segment['sha256']):
                    raise ValueError('editor literal length or hash differs')
                parts.append(value)
                offset += length + 1
            else:
                raise ValueError('unknown editor span segment')
        text = ''.join(parts)
        if len(text) != count or digest(text) != record['sha256']:
            raise ValueError('expanded editor file length or hash differs')
        contents[name] = text
    if offset != len(body):
        raise ValueError('unexpected trailing editor span content')
    expanded = dict(contents)
    for name, source in header['aliases'].items():
        if not isinstance(name, str) or not isinstance(source, str) or name in expanded or source not in contents:
            raise ValueError('invalid editor span alias')
        expanded[name] = contents[source]
    return expanded


def span_packet(head, shown, alias_chars, raw_chars):
    from . import pce
    payload, header = encode_spans(shown)
    instruction = (
        "\nLossless shared-span transport v1. After 'Allowed input files:' comes "
        "PATHFINDER-EDITOR-SPANS-V1, one JSON index, then raw literal segments in index order. "
        "Reconstruct each file by concatenating its listed segments: a copy segment names an earlier "
        "file and its zero-based, half-open Unicode-code-point [start,end) range; a literal segment "
        "consumes exactly chars code points followed by one framing newline. Literal text is readable "
        "raw text, not JSON-escaped. Every complete file has its own length and UTF-8 SHA-256. "
        "An alias has exactly its canonical file's complete content. Shared spans are exact text, "
        "not summaries or scientific equivalences. Preserve each file path's provenance/status; "
        "a historical manuscript remains historical even when it shares current-draft text. "
        "All scoped content is present; no tools, fetches or omitted sources. Output contracts unchanged.\n")
    framed = head.replace(pce.TRANSPORT, pce.TRANSPORT.replace('The JSON mapping', 'The indexed shared-span packet'), 1)
    return instruction + framed + payload, {
        'encoding': 'raw-length-shared-span-v1', 'aliases': header['aliases'], 'file_frames': header['files'],
        'expanded_files_sha256': {n: digest(t) for n, t in sorted(shown.items())},
        'expanded_json_sha256': digest(pce._json(shown)),
        'original_prompt_sha256': digest(head+pce._json(shown)),
        'original_prompt_chars': len(head+pce._json(shown)), 'json_alias_prompt_chars': alias_chars,
        'whole_file_raw_prompt_chars': raw_chars, 'raw_unique_chars': sum(len(v) for v in set(shown.values())),
        'literal_chars': sum(s['chars'] for r in header['files'] for s in r['segments'] if 'chars' in s),
        'payload_sha256': digest(payload),
    }
