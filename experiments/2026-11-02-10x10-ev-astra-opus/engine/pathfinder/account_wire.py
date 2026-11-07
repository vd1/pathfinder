"""One immutable transport-readability repair of an exhausted fixed-candidate review."""
import copy
import re
from . import account_amend, account_review, health, pce, pce_recovery, provenance, runner, transport, whole_bodies


def validate(root, grant, files, cap, campaign):
    binding = grant.get('whole_body_repair')
    path = root / 'repair.json'
    if not binding or not path.exists() or account_amend._read(path) != binding:
        raise pce.Changed('whole-body repair binding changed')
    if root.parent.name != 'review-grants' or not re.fullmatch(r'review(?:-grants/[a-zA-Z0-9_-]+)?', binding['previous']):
        raise pce.Changed('invalid previous review location')
    previous = root.parent.parent / binding['previous']
    if (binding.get('policy') != 'whole-body-repair-v1'
        or pce._sha(pce._json(binding['previous_sha256'])) != binding['failed_round_sha256']
        or pce_recovery.hashes(previous) != binding['previous_sha256']):
        raise pce.Changed('failed round, receipts or consumed allowance changed')
    if (binding['maximum_calls'] != 5 or grant['settings']['passes'] != 1
        or grant['settings']['fact_checks'] != 1 or 'pass_score' in grant['settings']['critic']
        or not grant.get('fixed_candidate') or not grant.get('strict_evidence')):
        raise pce.Changed('whole-body repair must retain one strict bounded review')
    if files != account_amend._read(previous / 'frozen-inputs.json'):
        raise pce.Changed('wire repair changed scientific inputs or replacement register')
    expected = whole_bodies.declaration(files, cap, campaign)
    if grant.get('review_wire') != expected or account_amend._read(root / 'wire-declaration.json') != expected:
        raise pce.Changed('whole-body codec, scope, cap or packet binding changed')


def repair(campaign, pair, *, identity, grant_id, failed_round_sha256, reason, apply=False, accept_change=None):
    with health.owner(campaign, nested=True), runner.Lock(campaign.thread_dir(pair)):
        routes = pce_recovery.preflight(campaign, presentation=True)
        root, expected = account_review._review_root(campaign, pair, identity)
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', grant_id or '') or not reason.strip():
            raise pce.Changed('explicit wire-repair identity and authority required')
        target = root / 'review-grants' / grant_id
        saved = account_amend._read(target / 'repair.json') if (target / 'repair.json').exists() else None
        if saved and (saved['reason'] != reason.strip() or saved['failed_round_sha256'] != failed_round_sha256):
            raise pce.Changed('repair authority changed')
        if (root / 'acceptance.json').exists():
            if not saved: raise pce.Changed('cannot repair an accepted review')
            files = account_amend._read(target / 'frozen-inputs.json')
            validate(target, account_amend._read(target / 'grant.json'), files, transport.max_prompt_chars(campaign), campaign)
            account_review._install(campaign, pair, expected)
            return 'accepted; run present PAIR --edited'
        request, candidate, bib = account_review.custody(campaign, pair, root)
        previous = root / saved['previous'] if saved else account_review.workflow(root)
        if account_review.workflow(root) not in (previous, target):
            raise pce.Changed('wire repair was superseded')
        for path in (root / 'review-grants').glob('*/repair.json'):
            if path.parent != target and account_amend._read(path).get('policy') == 'whole-body-repair-v1':
                raise pce.Changed('only one bounded readability repair is allowed')
        hashes = pce_recovery.hashes(previous)
        if pce._sha(pce._json(hashes)) != failed_round_sha256:
            raise pce.Changed('failed-round binding differs')
        old = account_amend._read(previous / 'grant.json')
        result = account_amend._read(previous / 'result.json')
        if result.get('status') != 'review_required' or old.get('review_wire', {}).get('version') != 'raw-literal-v1':
            raise pce.Changed('repair requires a terminal raw-literal-v1 review')
        files = account_amend._read(previous / 'frozen-inputs.json')
        if not old.get('strict_evidence') or not old.get('fixed_candidate') or files[pce.BASELINE] != candidate:
            raise pce.Changed('repair requires the unchanged strict fixed candidate')
        binding = dict(policy='whole-body-repair-v1', previous=str(previous.relative_to(root)),
            previous_sha256=hashes, failed_round_sha256=failed_round_sha256, reason=reason.strip(),
            candidate_sha256=pce._sha(candidate), request_sha256=pce._sha(pce._json(request)),
            maximum_calls=5, routes={k:v for k,v in routes.items() if k.startswith('edit/')})
        if saved and saved != binding: raise pce.Changed('repair authority or custody changed')
        grant = copy.deepcopy(old)
        grant['routes'] = binding['routes']
        grant['settings']['passes'] = grant['settings']['fact_checks'] = 1
        grant['settings']['critic'].pop('pass_score', None)
        grant['whole_body_repair'] = binding
        # The failed verdicts/receipts are host custody only, never fresh scientific evidence.
        wire = whole_bodies.declaration(files, transport.max_prompt_chars(campaign), campaign)
        grant['review_wire'] = wire
        for name in ('replacement-history.json', 'replacement-register.json'):
            pce._write(target, name, (previous / name).read_bytes().decode('utf-8'), immutable=True)
        for name, value in [('repair.json', binding), ('frozen-inputs.json', files),
                            ('wire-declaration.json', wire), ('grant.json', grant)]:
            pce._write(target, name, pce._json(value), immutable=True)
        validate(target, grant, files, transport.max_prompt_chars(campaign), campaign)
        pce._write(root, 'review-active.json', pce._json({'grant': grant_id}))
        if not apply: return 'whole-body repair prepared; unchanged candidate and evidence; one fresh five-role review'
        if runner.stopped(campaign) or not runner.guard_ok(campaign, inflight=1): return 'stopped: wire repair retained'
        with provenance.run_context(campaign, accept_change):
            c = copy.copy(campaign); c._pce_workflow = target
            result = pce.run(c, pair, stop=lambda: runner.stopped(campaign))
        account_review.custody(campaign, pair, root)
        validate(target, grant, files, transport.max_prompt_chars(campaign), campaign)
        outcome = account_amend.finish(campaign, pair, root, target, request, bib, result)
        if (root / 'acceptance.json').exists(): account_review._install(campaign, pair, expected)
        return outcome
