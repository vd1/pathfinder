"""Bounded evidence-repair rounds for an unchanged account amendment."""
import copy
import json
import re
from pathlib import Path, PurePosixPath
from . import account_amend, account_release, health, pce, pce_recovery, provenance, runner, transport


def workflow(root):
    pointer = root / 'review-active.json'
    if not pointer.exists():
        return root / 'review'
    identity = account_amend._read(pointer)['grant']
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', identity):
        raise pce.Changed('invalid account review grant')
    return root / 'review-grants' / identity


def custody(campaign, pair_id, root):
    request = account_amend._read(root / 'request.json')
    note, bib, accepted = account_release.source(campaign, pair_id)
    candidate = (root / 'candidate.tex').read_text()
    if (accepted != request['original_acceptance'] or pce._sha(note) != request['changes']['baseline_sha256']
            or pce._sha(candidate) != request['candidate_sha256'] or pce._sha(bib) != request['bibliography_sha256']):
        raise pce.Changed('amendment custody or original acceptance changed')
    revised = note
    for change in request['changes']['changes']:
        if not change['before'] or revised.count(change['before']) != 1:
            raise pce.Changed('ambiguous original amendment replacement')
        revised = revised.replace(change['before'], change['after'], 1)
    if revised != candidate:
        raise pce.Changed('candidate contains undeclared changes')
    snapshots = account_amend._read(root / 'evidence-snapshots.json')
    if pce._sha(pce._json(snapshots)) != request['evidence_sha256']:
        raise pce.Changed('original evidence snapshots changed')
    thread = campaign.thread_dir(pair_id).resolve()
    for name, text in snapshots.items():
        path = (thread / name).resolve()
        if not path.is_relative_to(thread) or path.read_text() != text:
            raise pce.Changed('original amendment evidence changed')
    return request, candidate, bib


def external_packet(path, expected_sha, previous):
    raw = Path(path).read_bytes().decode('utf-8')
    if pce._sha(raw) != expected_sha:
        raise pce.Changed('historical evidence packet hash differs')
    data = json.loads(raw)
    external = data['external']
    if set(external) != {'P.txt', 'Q.txt', 'research-supplement.md'}:
        raise pce.Changed('historical packet needs exactly P, Q and scientific supplement')
    for name in ('P.txt', 'Q.txt'):
        if external[name] != previous['sources/external/' + name]:
            raise pce.Changed('evidence repair cannot change the paper texts')
    supplement = json.loads(external['research-supplement.md'])
    permitted = {'coverage_contract', 'coverage_limit', 'files', 'omitted_scientific_bytes',
                 'omitted_scientific_file_count', 'omitted_support', 'path_aliases', 'policy',
                 'purpose', 'source_metadata', 'unresolved_reference_count'}
    if set(supplement) - permitted or not isinstance(supplement.get('files'), dict):
        raise pce.Changed('unrecognised historical scientific packet schema')
    removed = []
    for name, text in list(supplement['files'].items()):
        parts = PurePosixPath(name).parts
        if (not parts or PurePosixPath(name).is_absolute() or '..' in parts
                or parts[0] not in ('ada', 'emmy', 'branches', 'ledger.jsonl')
                or any(p in ('reviews', 'dispatch', 'edited', 'operator-log') for p in parts)
                or not isinstance(text, str)):
            raise pce.Changed('non-scientific file in historical external packet: ' + name)
        if 'style-check' in parts[-1] or parts[-1] in ('local-checks.json', 'review-evidence-sha256.json'):
            removed.append(name)
            del supplement['files'][name]
            continue
        if parts[-1] == 'ledger.jsonl':
            for line in text.splitlines():
                if json.loads(line).get('kind') not in ('finding', 'idea', 'correction', 'objection'):
                    raise pce.Changed('historical ledger includes review or operational rows')
    if not supplement['files']:
        raise pce.Changed('empty historical scientific file mapping')
    # The whole pack is archived privately. Fresh roles see only this external projection.
    return raw, {**external, 'research-supplement.md': pce._json(supplement)}, removed


def prepare(campaign, pair_id, *, identity, grant_id, inputs, inputs_sha256, reason):
    routes = pce_recovery.preflight(campaign, presentation=True)
    root = account_amend._root(campaign, pair_id, identity)
    selected = account_amend._read(root.parent.parent / 'account-amendment.json')
    if selected['id'] != identity or (root / 'acceptance.json').exists():
        raise pce.Changed('evidence repair requires the selected, unaccepted amendment')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', grant_id or '') or not reason.strip():
        raise pce.Changed('provide an explicit review grant ID and reason')
    request, candidate, bib = custody(campaign, pair_id, root)
    target = root / 'review-grants' / grant_id
    current = workflow(root)
    saved = account_amend._read(target / 'repair.json') if (target / 'repair.json').exists() else None
    previous = root / saved['previous'] if saved else current
    if saved and current not in (target, previous):
        raise pce.Changed('review grant was superseded')
    if account_amend._read(previous / 'result.json')['status'] != 'review_required':
        raise pce.Changed('evidence repair requires a terminal failed review')
    old_inputs = account_amend._read(previous / 'frozen-inputs.json')
    raw, external, removed = external_packet(inputs, inputs_sha256, old_inputs)
    repair = {'grant': grant_id, 'reason': reason.strip(), 'packet_sha256': inputs_sha256,
              'previous': str(previous.relative_to(root)), 'previous_sha256': pce_recovery.hashes(previous),
              'candidate_sha256': pce._sha(candidate), 'request_sha256': pce._sha(pce._json(request)),
              'removed_operational_files': removed, 'maximum_calls': 5}
    if saved and saved != repair:
        raise pce.Changed('review grant inputs, parent round or authority changed')
    files = {k: v for k, v in old_inputs.items() if not k.startswith('sources/external/')}
    # No old author feedback or full change-packet metadata in any new role context.
    files = {k: v for k, v in files.items() if k in ('brief.md', 'references.bib', pce.BASELINE, 'state.json')}
    files[pce.BASELINE] = candidate
    files['sources/internal/changes.json'] = pce._json({'changes': [
        {'finding': x['finding'], 'after': x['after']} for x in request['changes']['changes']]})
    files.update({'sources/external/' + k: v for k, v in external.items()})
    files['brief.md'] = (
        'Review the unchanged candidate as a complete scientific account. No new research or text revision. '
        'The supplement is an explicitly approved generated scientific file mapping, not independent literature. '
        'Visibility and hashes do not prove correctness or completeness. Preserve its omissions, objections, '
        'corrections and limitations. Judge branch results by supplied derivations and actual attribution; '
        'absence of a numbered joint-ledger citation is not evidence of rejection or non-adoption. '
        'Do not infer universal branch adoption. Extract only manuscript claims, never administrative '
        'packet metadata, hashes, preservation assertions or review instructions. Host custody checks are '
        'separate from scientific evidence. Each material manuscript claim and replacement must be supported.\n')
    settings = {**pce.settings(campaign), 'passes': 1, 'fact_checks': 1}
    settings['critic'] = {k: v for k, v in settings['critic'].items() if k != 'pass_score'}
    grant = {'fixed_candidate': True, 'strict_evidence': True,
             'routes': {k: v for k, v in routes.items() if k.startswith('edit/')},
             'settings': settings, 'inputs_sha256': pce._sha(pce._json(files))}
    # Reserve room for generated claims/reviews; every individual call also enforces full visibility.
    if len(pce._json(files)) + 100_000 > transport.max_prompt_chars(campaign):
        raise pce.Changed('complete evidence packet exceeds prompt allowance; no truncation is allowed')
    manifest = {'external_sha256': {k: pce._sha(v) for k, v in files.items() if k.startswith('sources/external/')},
                'embedded_sha256': {k: pce._sha(v) for k, v in json.loads(external['research-supplement.md'])['files'].items()},
                'custody': {'candidate_sha256': pce._sha(candidate), 'baseline_sha256': request['changes']['baseline_sha256'],
                            'exact_replacements_verified': True, 'original_acceptance_verified': True}}
    for name, text in [('repair.json', pce._json(repair)), ('historical-packet.json', raw),
                       ('evidence-manifest.json', pce._json(manifest)), ('frozen-inputs.json', pce._json(files)),
                       ('grant.json', pce._json(grant))]:
        pce._write(target, name, text, immutable=True)
    pce._write(root, 'review-active.json', pce._json({'grant': grant_id}))
    return root, target, request, bib


def apply(campaign, pair_id, *, resume=False, accept_change=None, **kwargs):
    with health.owner(campaign, nested=True), runner.Lock(campaign.thread_dir(pair_id)):
        root = account_amend._root(campaign, pair_id, kwargs['identity'])
        if (root / 'acceptance.json').exists():
            account_amend.selected(campaign, pair_id, *account_release.source(campaign, pair_id))
            return 'accepted; run present PAIR --edited'
        root, target, request, bib = prepare(campaign, pair_id, **kwargs)
        if not resume:
            return 'evidence repair prepared; no calls; repeat with --apply for one fresh review'
        if runner.stopped(campaign) or not runner.guard_ok(campaign, inflight=1):
            return 'stopped: evidence repair retained'
        with provenance.run_context(campaign, accept_change):
            c = copy.copy(campaign)
            c._pce_workflow = target
            result = pce.run(c, pair_id, stop=lambda: runner.stopped(campaign))
        # Recheck original custody, parent hashes and immutable inputs before installation.
        prepare(campaign, pair_id, **kwargs)
        return account_amend.finish(campaign, pair_id, root, target, request, bib, result)
