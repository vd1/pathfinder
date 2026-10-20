"""Reversible raw framing for complete editor inputs, with whole-file aliases."""
import hashlib
import json

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
