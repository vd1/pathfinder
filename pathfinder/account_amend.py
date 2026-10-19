"""Explicit fixed-candidate account review, with separate immutable acceptance."""
import copy
import json
import re
from pathlib import Path
from . import account_release, paper, pce, pce_recovery, presentation, provenance, research, runner, health


def _read(path):
    return json.loads(path.read_text())


def _root(campaign, pair_id, identity):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', identity or ''):
        raise pce.Changed('invalid account amendment ID')
    return campaign.thread_dir(pair_id) / 'edited' / 'account-amendments' / identity


def _hashes(root):
    return {k: v for k, v in pce_recovery.hashes(root).items() if k != 'acceptance.json'}


def selected(campaign, pair_id, note, bib, original):
    pointer = campaign.thread_dir(pair_id) / 'edited' / 'account-amendment.json'
    if not pointer.exists():
        return note, bib, original
    root = _root(campaign, pair_id, _read(pointer)['id'])
    accepted = root / 'acceptance.json'
    if not accepted.exists():
        raise pce.Changed('account amendment is awaiting acceptance; resume account-amend or review its findings')
    record = _read(accepted)
    if (record['original_acceptance'] != original or record['baseline_sha256'] != pce._sha(note)
            or record['files_sha256'] != _hashes(root)
            or record['bibliography_sha256'] != pce._sha(bib)):
        raise pce.Changed('account amendment or its original acceptance changed')
    return (root / 'candidate.tex').read_text(), bib, record


def prepare(campaign, pair_id, *, identity, packet, evidence_root, reason):
    routes = pce_recovery.preflight(campaign, presentation=True)
    root = _root(campaign, pair_id, identity)
    if not reason or not reason.strip():
        raise pce.Changed('record the explicit amendment authority and reason')
    note, bib, acceptance = account_release.source(campaign, pair_id)
    packet, evidence_root = Path(packet), Path(evidence_root).resolve()
    changes = _read(packet / 'changes.json')
    evidence = _read(packet / 'evidence.json')
    candidate = (packet / 'account-candidate.tex').read_bytes().decode('utf-8')
    if changes['baseline_sha256'] != pce._sha(note) or changes['candidate_sha256'] != pce._sha(candidate):
        raise pce.Changed('candidate or baseline does not match packet hashes')
    revised = note
    replacements = changes.get('changes')
    if not isinstance(replacements, list) or not replacements or len(replacements) > 20:
        raise pce.Changed('provide 1-20 explicit bounded replacements')
    for change in replacements:
        before, after = change['before'], change['after']
        if not before or revised.count(before) != 1 or not after or before == after:
            raise pce.Changed('each declared replacement must identify exactly one changed passage')
        revised = revised.replace(before, after, 1)
    if revised != candidate:
        raise pce.Changed('candidate contains undeclared changes')
    # Retain raw evidence privately. Only scientific branch evidence enters reviewer scopes;
    # the historical accepted body is editorial context, never independent evidence.
    snapshots, approved = {}, {}
    thread = campaign.thread_dir(pair_id).resolve()
    for i, item in enumerate(evidence['source_files']):
        path = (evidence_root / item['path']).resolve()
        if not path.is_relative_to(thread):
            raise pce.Changed('amendment evidence must be retained within this thread')
        text = path.read_bytes().decode('utf-8')
        if pce._sha(text) != item['sha256']:
            raise pce.Changed('amendment evidence hash differs: ' + item['path'])
        snapshots[str(path.relative_to(thread))] = text
        if path.is_relative_to(thread / 'branches'):
            approved[f'sources/external/amendment-{i:02d}-{path.name}'] = text
    if not approved:
        raise pce.Changed('amendment needs retained scientific branch evidence')
    request = dict(id=identity, reason=reason.strip(), changes=changes, evidence=evidence,
                   original_acceptance=acceptance, candidate_sha256=pce._sha(candidate),
                   bibliography_sha256=pce._sha(bib), evidence_sha256=pce._sha(pce._json(snapshots)))
    ed = thread / 'edited'
    pointer = ed / 'account-amendment.json'
    if pointer.exists() and _read(pointer)['id'] != identity:
        raise pce.Changed('another amendment is selected; do not replace its review implicitly')
    if (root / 'request.json').exists():
        if _read(root / 'request.json') != request:
            raise pce.Changed('amendment ID already binds different inputs or authority')
    else:
        parent = account_release.view(campaign, pair_id, original=True)
        if presentation.state(parent, pair_id).get('state') != 'RETURNED':
            raise pce.Changed('explicit account amendment requires a RETURNED presentation')
        findings = _read(presentation.folder(parent, pair_id) / 'amend-findings.json')
        finding_ids = {f['id'] for f in findings['findings']}
        if {x['finding'] for x in replacements} != finding_ids:
            raise pce.Changed('packet replacements must address exactly the returned findings')
        pce._write(root, 'returned-findings.json', pce._json(findings), immutable=True)
    pce._write(root, 'request.json', pce._json(request), immutable=True)
    pce._write(root, 'candidate.tex', candidate, immutable=True)
    pce._write(root, 'evidence-snapshots.json', pce._json(snapshots), immutable=True)
    # sources() expects references.bib; imported accounts may use prose references.
    # Build its read-only source context with the normal corpus and clean supplement directly.
    files = {'brief.md': pce.BOUNDARY + '\nReview this fixed candidate as a complete account. '
             'Require explicit definitions, supported numbers and unchanged scientific limitations. '
             'No new research, source fetching or text revision is authorized. '
             'sources/external/amendment-* are retained campaign derivations and checks, '
             'research record evidence, not independent literature or prior editorial verdicts.\n',
             pce.BASELINE: candidate, 'references.bib': bib,
             'sources/internal/changes.json': pce._json(changes),
             'sources/internal/original.tex': note,
             'state.json': pce._json({'risk': 'high', 'max_passes': 1,
                 'acceptance_policy': 'Every claim supported, both gates pass, explicit editor acceptance. No evidence change.'}),
             pce.SUPPLEMENT: pce._supplement(campaign, pair_id, pce.settings(campaign)['supplement_chars'], reviewers=True),
             **approved}
    for path in sorted((thread / 'inputs').glob('*')):
        if path.stem in ('Q', 'P') and path.suffix != '.json' and path.is_file():
            files['sources/external/' + path.name] = path.read_text(errors='replace')
    settings = {**pce.settings(campaign), 'passes': 1, 'fact_checks': 1}
    settings['critic'] = {k: v for k, v in settings['critic'].items() if k != 'pass_score'}
    grant = {'fixed_candidate': True, 'routes': {k: v for k, v in routes.items() if k.startswith('edit/')},
             'settings': settings, 'inputs_sha256': pce._sha(pce._json(files))}
    pce._write(root / 'review', 'frozen-inputs.json', pce._json(files), immutable=True)
    pce._write(root / 'review', 'grant.json', pce._json(grant), immutable=True)
    pce._write(ed, 'account-amendment.json', pce._json({'id': identity}))
    return root, request, bib


def apply(campaign, pair_id, *, identity, packet, evidence_root, reason, resume=False, accept_change=None):
    with health.owner(campaign, nested=True), runner.Lock(campaign.thread_dir(pair_id)):
        if (_root(campaign, pair_id, identity) / 'review-active.json').exists():
            raise pce.Changed('use account-amend-review to resume the evidence-repair grant')
        root, request, bib = prepare(campaign, pair_id, identity=identity, packet=packet,
                                    evidence_root=evidence_root, reason=reason)
        if (root / 'acceptance.json').exists():
            selected(campaign, pair_id, *account_release.source(campaign, pair_id))
            return 'accepted; run present PAIR --edited'
        if not resume:
            return 'amendment prepared; no calls; repeat with --apply to review the fixed candidate'
        if runner.stopped(campaign) or not runner.guard_ok(campaign, inflight=1):
            return 'stopped: amendment retained'
        with provenance.run_context(campaign, accept_change):
            c = copy.copy(campaign)
            c._pce_workflow = root / 'review'
            result = pce.run(c, pair_id, stop=lambda: runner.stopped(campaign))
        return finish(campaign, pair_id, root, root / 'review', request, bib, result)


def finish(campaign, pair_id, root, review, request, bib, result):
    if result['status'] != 'accepted':
        return 'review_required: ' + result.get('reason', '')
    candidate = (root / 'candidate.tex').read_text()
    if (review / pce.DRAFT).read_text() != candidate:
        raise pce.Changed('review did not accept the exact candidate')
    build = root / 'build'
    pce._write(build, 'paper.tex', candidate, immutable=True)
    pce._write(build, 'references.bib', bib, immutable=True)
    ok, log = paper.build(build)
    pce._write(build, 'build-log.txt', log)
    if not ok:
        return 'review accepted but candidate build failed; no installation'
    record = {'kind': 'bounded account amendment PCE acceptance',
              'workflow': str(review.relative_to(campaign.thread_dir(pair_id))),
              'accepted_at': research._now(), 'original_acceptance': request['original_acceptance'],
              'baseline_sha256': request['changes']['baseline_sha256'],
              'candidate_sha256': pce._sha(candidate), 'bibliography_sha256': pce._sha(bib),
              'files_sha256': _hashes(root)}
    pce._write(root, 'acceptance.json', pce._json(record), immutable=True)
    return 'accepted; run present PAIR --edited for fresh presentation before release'
