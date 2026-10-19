"""Explicit single-cycle continuations for paused account presentation."""
import hashlib
import json
import re
from pathlib import Path
from . import account_release, health, paper, pce, pce_recovery, presentation, provenance, runner


def apply(campaign, pair_id, *, identity, context_path, reason, resume=False, accept_change=None):
    pce_recovery.preflight(campaign, presentation=True)
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', identity or '') or not reason.strip():
        raise pce.Changed('provide a presentation continuation ID and reason')
    with health.owner(campaign, nested=True), runner.Lock(campaign.thread_dir(pair_id)):
        c = account_release.view(campaign, pair_id)
        pd = paper.folder(c, pair_id)
        root = pd / 'presentation-continuations' / identity
        d = presentation.folder(c, pair_id)
        state = presentation.state(c, pair_id)
        context = json.loads(Path(context_path).read_text())
        if set(context) != {'source', 'quote', 'where'} or not all(isinstance(v, str) and v.strip() for v in context.values()):
            raise pce.Changed('context must identify a retained source, exact quote and finding location')
        acceptance = json.loads((pd / 'acceptance.json').read_text())
        workflow = (campaign.thread_dir(pair_id) / acceptance['workflow']).resolve()
        if not workflow.is_relative_to(campaign.thread_dir(pair_id).resolve()):
            raise pce.Changed('invalid account acceptance workflow')
        frozen = json.loads((workflow / 'frozen-inputs.json').read_text())
        supplement = json.loads(frozen[pce.SUPPLEMENT])
        evidence = supplement['files'].get(context['source'])
        if not isinstance(evidence, str) or evidence.count(context['quote']) != 1:
            raise pce.Changed('context quote must occur exactly once in the accepted scientific evidence')
        request = {'id': identity, 'reason': reason.strip(), 'context': context,
                   'source_sha256': pce._sha(evidence), 'acceptance_sha256': pce._sha((pd / 'acceptance.json').read_text()),
                   'accepted_sha256': pce._sha((pd / 'paper.tex').read_text()),
                   'routes': pce_recovery.preflight(campaign, presentation=True)}
        grant_file = root / 'grant.json'
        pointer = pd / 'presentation-continuation.json'
        if grant_file.exists():
            grant = json.loads(grant_file.read_text())
            if grant['request'] != request:
                raise pce.Changed('presentation grant identity binds different context, authority or routes')
            if pointer.exists() and json.loads(pointer.read_text())['id'] != identity:
                raise pce.Changed('presentation continuation was superseded')
        else:
            if pointer.exists():
                old = pd / 'presentation-continuations' / json.loads(pointer.read_text())['id']
                if not (old / 'result.json').exists():
                    raise pce.Changed('resume the existing presentation continuation first')
            if (paper.status(c, pair_id).get('status') != 'ACCEPTED' or
                    state.get('state') != 'PAUSE-ON-PRESENT' or
                    not state.get('reason', '').startswith('not cleared at the cycle limit:')):
                raise pce.Changed('a presentation continuation requires a pause at the correction-cycle limit')
            stage = state['stage']
            checked = json.loads((d / stage / 'check.json').read_text())
            findings = checked.get('findings', [])
            if (not findings or any(f.get('kind') != 'unclear' for f in findings)
                    or context['where'] not in [f.get('where') for f in findings]):
                raise pce.Changed('bounded clarity continuation requires only unclear findings and a matching location')
            grant = {'request': request, 'prior_state': state, 'prior_publication': paper.status(c, pair_id),
                     'prior_files_sha256': pce_recovery.hashes(d), 'cycle_limit': state['cycles'] + 1,
                     'policy': 'one guarded correction cycle and fresh check; no research or PCE rerun'}
            pce._write(root, 'grant.json', pce._json(grant), immutable=True)
        # Only state.json is mutable; all existing stage artifacts must remain exactly as granted.
        for name, digest in grant['prior_files_sha256'].items():
            path = d / name
            if name != 'state.json' and (not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
                raise pce.Changed('presentation history changed: ' + name)
        if (root / 'result.json').exists():
            return json.loads((root / 'result.json').read_text())['state']
        pce._write(pd, 'presentation-continuation.json', pce._json({'id': identity}))
        if not resume:
            return 'presentation continuation prepared; no calls; repeat with --apply for one correction cycle'
        if runner.stopped(campaign) or not runner.guard_ok(campaign, inflight=1):
            return 'stopped: presentation continuation retained'
        c._presentation_cycle_limit = grant['cycle_limit']
        c._preserve_presentation_history = True
        c._presentation_context = context
        # The recorded paused state remains immutable in grant.json. Resume its last stage.
        with provenance.run_context(campaign, accept_change):
            c.run_id = campaign.run_id
            presentation._save(c, pair_id, state='running', reason=None)
            result = presentation.run(c, pair_id)
        if result in presentation.TERMINAL:
            pce._write(root, 'result.json', pce._json({'state': result, 'presentation': presentation.state(c, pair_id)}), immutable=True)
        return result
