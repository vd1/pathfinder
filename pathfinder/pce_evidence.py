"""Explicit projections of retained evidence, without rewriting research history."""
import hashlib
import json
from pathlib import Path, PurePosixPath
from . import pce


def read(path):
    try:
        packet = json.loads(Path(path).read_text())
        if (not isinstance(packet, dict) or set(packet) != {'version', 'exclude', 'include'}
                or packet['version'] != 1 or not isinstance(packet['exclude'], list)
                or not isinstance(packet['include'], list)):
            raise ValueError('expected version 1, exclude and include lists')
        return packet
    except (ValueError, OSError) as exc:
        raise pce.Changed('invalid evidence projection: ' + str(exc)) from exc


def validate(campaign, pair_id, packet):
    if packet is None:
        return set(), {}
    root = campaign.thread_dir(pair_id).resolve()

    def source(name, expected):
        rel = PurePosixPath(name)
        path = root / rel
        if (rel.is_absolute() or '..' in rel.parts or not rel.parts
                or not path.resolve().is_relative_to(root) or not path.is_file()
                or any((root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts) + 1))):
            raise pce.Changed('unsafe evidence path: ' + name)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise pce.Changed('retained evidence hash differs: ' + name)
        try:
            return raw.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise pce.Changed('evidence must be retained UTF-8 text') from exc

    excluded, additions = set(), {}
    for row in packet['exclude']:
        if (not isinstance(row, dict) or set(row) != {'ledger', 'sha256', 'seq', 'reason'}
                or type(row['seq']) is not int or not isinstance(row['reason'], str) or not row['reason'].strip()):
            raise pce.Changed('exclusion needs ledger hash, sequence and editorial reason')
        name = row['ledger']
        parts = PurePosixPath(name).parts
        if not (name == 'ledger.jsonl' or (len(parts) == 3 and parts[0] == 'branches'
                                         and parts[1].startswith('branch-') and parts[2] == 'ledger.jsonl')):
            raise pce.Changed('exclusion must name a retained joint or frozen branch ledger')
        rows = [json.loads(line) for line in source(name, row['sha256']).splitlines() if line.strip()]
        matches = [r for r in rows if r.get('seq') == row['seq']]
        if (len(matches) != 1 or matches[0].get('kind') not in ('finding', 'editorial')
                or matches[0].get('supersedes') is not None):
            raise pce.Changed('only an explicitly identified editorial finding may be excluded')
        key = (name, row['seq'])
        if key in excluded:
            raise pce.Changed('duplicate evidence exclusion')
        excluded.add(key)
    for row in packet['include']:
        if (not isinstance(row, dict) or set(row) != {'path', 'sha256', 'purpose'}
                or not isinstance(row['purpose'], str) or not row['purpose'].strip()):
            raise pce.Changed('addition needs retained path, hash and scientific purpose')
        name = row['path']
        parts = PurePosixPath(name).parts
        scientific = (len(parts) >= 2 and parts[0] in campaign.peers) or (
            len(parts) >= 4 and parts[0] == 'branches' and parts[1].startswith('branch-')
            and parts[2] in campaign.peers)
        if (not scientific or any(p in ('reviews', 'dispatch', 'edited', 'operator-log') for p in parts)
                or parts[-1] == 'ledger.jsonl' or name in additions):
            raise pce.Changed('addition must be a distinct retained scientific support file: ' + name)
        additions[name] = source(name, row['sha256'])
    return excluded, additions
