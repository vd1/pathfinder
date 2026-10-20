"""Explicit single-cycle continuations for paused account presentation."""
import hashlib
import json
import re
from pathlib import Path
from . import account_release, health, paper, pce, pce_recovery, presentation, provenance, runner


def _context(campaign, pair_id, pd, path):
    context = json.loads(Path(path).read_text())
    if context.get("version") == 2:
        from . import notation_continuation
        return notation_continuation.validate(pd, context)
    thread = campaign.thread_dir(pair_id).resolve()
    if set(context) == {'version', 'contexts'} and context['version'] == 1:
        entries = context['contexts']
        if not isinstance(entries, list) or not 1 <= len(entries) <= 20:
            raise pce.Changed('provide 1-20 retained context quotations')
        hashes, locations = {}, set()
        for entry in entries:
            if (not isinstance(entry, dict) or set(entry) != {'source', 'sha256', 'quote', 'where'}
                    or not all(isinstance(v, str) and v.strip() for v in entry.values())):
                raise pce.Changed('retained context needs source, sha256, exact quote and finding location')
            from pathlib import PurePosixPath
            rel = PurePosixPath(entry['source'])
            parts = rel.parts
            source = thread / rel
            scientific = (len(parts) >= 2 and parts[0] in (*campaign.peers, 'inputs')) or (
                len(parts) >= 4 and parts[0] == 'branches' and parts[1].startswith('branch-')
                and parts[2] in campaign.peers)
            if (not scientific or rel.is_absolute() or '..' in parts
                    or any(p in ('edited', 'reviews', 'dispatch', 'operator-log') for p in parts)
                    or not source.resolve().is_relative_to(thread)
                    or any((thread / Path(*parts[:i])).is_symlink() for i in range(1, len(parts)+1))):
                raise pce.Changed('context must be a retained scientific or input file')
            try:
                raw = source.read_bytes()
                evidence = raw.decode('utf-8')
            except (OSError, UnicodeDecodeError) as exc:
                raise pce.Changed('context source is unavailable UTF-8 text') from exc
            if hashlib.sha256(raw).hexdigest() != entry['sha256'] or evidence.count(entry['quote']) != 1:
                raise pce.Changed('retained context hash or exact quote differs')
            hashes[entry['source']] = entry['sha256']
            locations.add(entry['where'])
        if len(pce._json(context)) > 40_000:
            raise pce.Changed('retained presentation context exceeds bounded quote allowance')
        return context, hashes, locations
    if set(context) != {'source', 'quote', 'where'} or not all(isinstance(v, str) and v.strip() for v in context.values()):
        raise pce.Changed('context must identify a retained source, exact quote and finding location')
    acceptance = json.loads((pd / 'acceptance.json').read_text())
    workflow = (thread / acceptance['workflow']).resolve()
    if not workflow.is_relative_to(thread):
        raise pce.Changed('invalid account acceptance workflow')
    frozen = json.loads((workflow / 'frozen-inputs.json').read_text())
    evidence = json.loads(frozen[pce.SUPPLEMENT])['files'].get(context['source'])
    if not isinstance(evidence, str) or evidence.count(context['quote']) != 1:
        raise pce.Changed('context quote must occur exactly once in the accepted scientific evidence')
    return context, pce._sha(evidence), {context['where']}


def _completed_notation_pause(pd, state):
    """Recognise the bounded notation check's terminal pause from its saved evidence."""
    if not state.get('reason', '').startswith('reviewed notation cycle not cleared:'):
        return False
    try:
        identity = json.loads((pd / 'presentation-continuation.json').read_text())['id']
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', identity):
            return False
        root = pd / 'presentation-continuations' / identity
        grant = json.loads((root / 'grant.json').read_text())
        result = json.loads((root / 'result.json').read_text())
        context = grant['request']['context']
        if (context.get('version') != 2 or result.get('state') != 'PAUSE-ON-PRESENT'
                or result.get('presentation') != state
                or state.get('stage') != f"correct-{grant['cycle_limit']}"):
            return False
        from . import notation_continuation
        notation_continuation.validate(pd, context)
        source = pd / 'presentation' / state['stage'] / 'paper.tex'
        return hashlib.sha256(source.read_bytes()).hexdigest() == context['target_sha256']
    except (OSError, ValueError, KeyError, TypeError, pce.Changed):
        return False


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
        context, source_hashes, locations = _context(campaign, pair_id, pd, context_path)
        request = {'id': identity, 'reason': reason.strip(), 'context': context,
                   'source_sha256': source_hashes, 'acceptance_sha256': pce._sha((pd / 'acceptance.json').read_text()),
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
            if context.get("version") == 2:
                if (hashlib.sha256((d / "state.json").read_bytes()).hexdigest() != context["state_sha256"]
                        or state.get("stage") != context["stage"]):
                    raise pce.Changed("notation paused state changed")
            if pointer.exists():
                old = pd / 'presentation-continuations' / json.loads(pointer.read_text())['id']
                if not (old / 'result.json').exists():
                    raise pce.Changed('resume the existing presentation continuation first')
            if (paper.status(c, pair_id).get('status') != 'ACCEPTED' or
                    state.get('state') != 'PAUSE-ON-PRESENT' or
                    not (state.get('reason', '').startswith(('not cleared at the cycle limit:', 'correction refused by the guard:'))
                         or _completed_notation_pause(pd, state))):
                raise pce.Changed('a presentation continuation requires a cycle-limit or guarded correction pause')
            stage = state['stage']
            checked = json.loads((d / stage / 'check.json').read_text())
            findings = checked.get('findings', [])
            if (not findings or any(f.get('kind') not in ('unclear', 'notation', 'background') for f in findings)
                    or not locations <= {f.get('where') for f in findings}
                    or any(f.get('kind') == 'background' and f.get('where') not in locations for f in findings)):
                raise pce.Changed('bounded clarity continuation requires unclear/notation findings or source-covered background definitions and matching locations')
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
        if context.get("version") == 2:
            c._presentation_notation = context
        # The recorded paused state remains immutable in grant.json. Resume its last stage.
        with provenance.run_context(campaign, accept_change):
            c.run_id = campaign.run_id
            presentation._save(c, pair_id, state='running', reason=None)
            result = presentation.run(c, pair_id)
        if result in presentation.TERMINAL:
            pce._write(root, 'result.json', pce._json({'state': result, 'presentation': presentation.state(c, pair_id)}), immutable=True)
        return result
