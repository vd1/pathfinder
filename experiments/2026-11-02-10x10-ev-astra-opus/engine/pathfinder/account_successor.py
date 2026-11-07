"""Explicit fixed-candidate successor to an accepted amendment returned by presentation."""
import copy
import hashlib
import json
from pathlib import Path
from . import (account_amend, account_release, account_review, account_revision,
               health, paper, pce, pce_evidence, pce_recovery, presentation, provenance, runner, transport)


def prepare(campaign, pair, *, identity, packet, reason, approval=None):
    routes = pce_recovery.preflight(campaign, presentation=True)
    if not reason.strip():
        raise pce.Changed('successor requires explicit scope and authority')
    thread = campaign.thread_dir(pair)
    root = account_amend._base(campaign, pair, identity)
    packet = Path(packet)
    delta = json.loads((packet / 'successor.json').read_text())
    candidate = (packet / 'account-candidate.tex').read_text()
    wire = delta.get('review_wire')
    if wire is not None:
        from . import raw_literals
        if wire != {'version': raw_literals.VERSION}:
            raise pce.Changed('unknown fresh successor wire declaration')
    from . import account_exception
    exception = account_exception.authorize(packet, approval, pair, identity, delta, candidate)
    projection = delta.get('evidence_projection')
    if projection is not None and (
            set(projection) != {'version', 'exclude', 'include'}
            or projection['version'] != 1 or projection['exclude']
            or not isinstance(projection['include'], list)
            or any('json_fields' in row for row in projection['include'])):
        raise pce.Changed('successor evidence permits only complete retained scientific file additions')
    _, additions = pce_evidence.validate(campaign, pair, projection)
    binding = dict(id=identity, reason=reason, delta=delta, candidate_sha256=pce._sha(candidate),
                   routes={k:v for k,v in routes.items() if k.startswith('edit/')})
    if exception is not None:
        if exception['contract']['version'] == 1 and projection is not None:
            raise pce.Changed('exception permits only its exact selected JSON addition')
        binding['history_exception'] = exception
    pointer = thread / 'edited/account-amendment.json'
    pending = thread / 'edited/account-successor.json'
    selected = json.loads(pointer.read_text())
    if pending.exists():
        active = json.loads(pending.read_text())
        if active.get('id') == identity and active.get('revision'):
            raise pce.Changed('resume the pending successor with account-amend-revise')
    if (root / 'successor.json').exists():
        record = json.loads((root / 'successor.json').read_text())
        if record['binding'] != binding:
            raise pce.Changed('successor identity binds different candidate, authority or routes')
        if selected not in (record['parent_pointer'], {'id': identity}):
            raise pce.Changed('successor was superseded')
        if selected == {'id': identity} and not (root / 'acceptance.json').exists():
            raise pce.Changed('unaccepted successor cannot be selected')
        for name, digest in record['history'].items():
            path = thread / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise pce.Changed('successor parent history changed: ' + name)
        request, _, bib = account_review.custody(campaign, pair, root)
        from . import raw_literals
        raw_literals.validate(root/'review', json.loads((root/'review/grant.json').read_text()),
                              json.loads((root/'review/frozen-inputs.json').read_text()), transport.max_prompt_chars(campaign), campaign)
    else:
        if root.exists():
            raise pce.Changed('successor ID already exists')
        if pending.exists():
            prior_pointer = json.loads(pending.read_text())
            if prior_pointer != selected:
                raise pce.Changed('finish the existing successor before preparing another')
            prior = account_amend._root(campaign, pair, prior_pointer['id'])
            if not (prior / 'acceptance.json').exists():
                raise pce.Changed('finish the existing successor before preparing another')
        original, bib, imported = account_release.source(campaign, pair)
        old_candidate, _, acceptance = account_amend.selected(campaign, pair, original, bib, imported)
        parent = account_amend._root(campaign, pair, selected['id'])
        if not (parent / 'acceptance.json').exists():
            raise pce.Changed('successor requires an accepted amendment')
        old_request, _, _ = account_review.custody(campaign, pair, parent)
        review = account_review.workflow(parent)
        if json.loads((review/'result.json').read_text()).get('status') != 'accepted':
            raise pce.Changed('parent review is not accepted')
        view = account_release.view(campaign, pair)
        publication = paper.folder(view, pair)
        pd = presentation.folder(view, pair)
        findings = json.loads((pd / 'amend-findings.json').read_text())
        if presentation.state(view, pair).get('state') != 'RETURNED':
            raise pce.Changed('accepted successor requires a RETURNED presentation')
        if (delta['parent_candidate_sha256'] != pce._sha(old_candidate)
                or delta['parent_acceptance_sha256'] != pce._sha((parent/'acceptance.json').read_text())
                or delta['returned_findings_sha256'] != pce._sha((pd/'amend-findings.json').read_text())
                or account_revision._apply(old_candidate, delta['changes']) != candidate):
            raise pce.Changed('successor candidate or returned finding binding differs')
        if {x['finding'] for x in delta['changes']} != {f['id'] for f in findings['findings']}:
            raise pce.Changed('successor must address exactly the returned findings')
        cumulative = {**old_request['changes'], 'candidate_sha256': pce._sha(candidate),
                      'changes': old_request['changes']['changes'] + delta['changes']}
        replayed = (account_exception.replay(exception, original, cumulative, parent, selected, review)
                    if exception is not None else account_revision._apply(original, cumulative['changes']))
        if replayed != candidate:
            raise pce.Changed('successor does not preserve original baseline custody')
        predecessor = dict(workflow=str(parent.relative_to(thread)), acceptance_sha256=delta['parent_acceptance_sha256'],
                           publication=str(publication.relative_to(thread)))
        request = {**old_request, 'id':identity, 'reason':reason, 'changes':cumulative,
                   'candidate_sha256':pce._sha(candidate), 'predecessor':predecessor}
        files = json.loads((review/'frozen-inputs.json').read_text())
        snapshots = json.loads((parent/'evidence-snapshots.json').read_text())
        if exception is not None:
            request['history_exception'] = exception
        if exception is not None and exception['contract']['version'] == 1:
            documents, custody = account_exception.selected_evidence(
                campaign, pair, exception['contract']['selected_json'])
            if any(name in files for name in documents):
                raise pce.Changed('selected JSON addition conflicts with inherited evidence')
            files.update(documents)
            files['brief.md'] += (
                '\nFor the evidence-basis taxonomy, sources/external/selected-json-* files are '
                'retained campaign research records, not independent papers. Classify support '
                'from them as research record, or both when combined with Q/P. Source hashes '
                'and visibility/custody metadata are provenance, not scientific claims.\n')
            request['selected_json_custody'] = custody
            request['history_exception'] = exception
        if additions:
            for name, text in additions.items():
                if name in snapshots and snapshots[name] != text:
                    raise pce.Changed('successor evidence conflicts with inherited snapshot')
            snapshots.update(additions)
            request['evidence_sha256'] = pce._sha(pce._json(snapshots))
            if wire is None and (exception is None or exception['contract']['version'] == 1):
                files[pce.SUPPLEMENT] += '\n\n## Additional retained scientific files\n\n' + pce._json(additions)
            else:
                for name, text in sorted(additions.items()):
                    key = 'sources/external/amendment-retained-' + pce._sha(name)[:16] + '.txt'
                    if key in files:raise pce.Changed('retained scientific source key conflict')
                    files[key] = ('Retained research record: ' + name + '\nRaw SHA-256: ' + pce._sha(text)
                                  + '\nComplete raw file, no omissions.\n\n' + text)
        files[pce.BASELINE] = candidate
        files['sources/internal/original.tex'] = old_candidate
        files['sources/internal/changes.json'] = pce._json(dict(
            baseline_sha256=pce._sha(old_candidate), candidate_sha256=pce._sha(candidate), changes=delta['changes']))
        grant = json.loads((review/'grant.json').read_text())
        if grant.get('review_wire') and wire is None:
            raise pce.Changed('fresh successor must explicitly declare inherited wire version')
        grant.pop('review_wire', None)
        grant['routes'] = binding['routes']
        grant['settings']['passes'] = 1
        grant['settings']['fact_checks'] = 1
        if exception is not None or wire is not None:
            grant['strict_evidence'] = True
            grant['settings']['critic'].pop('pass_score', None)
        grant['inputs_sha256'] = pce._sha(pce._json(files))
        if wire is not None:
            from . import account_register, raw_literals
            register = account_register.build(original, cumulative['changes'], candidate)
            files['sources/internal/changes.json'] = pce._json({'changes':[
                {'finding':r['finding'], 'after':r['claim']} for r in register['records'] if r['claim'].strip()]})
            grant['inputs_sha256'] = pce._sha(pce._json(files))
            grant['review_wire'] = raw_literals.declaration(files, transport.max_prompt_chars(campaign), campaign)
        elif len(pce._json(files)) + 100_000 > transport.max_prompt_chars(campaign):
            raise pce.Changed('complete successor evidence exceeds prompt allowance; no truncation')
        history = {}
        for source in (parent, publication):
            history.update({str(source.relative_to(thread)/name):digest
                            for name,digest in pce_recovery.hashes(source).items()})
        record = dict(binding=binding, parent_pointer=selected, history=history)
        stage = root.with_name('.'+identity+'.preparing')
        from . import account_register
        account_register.attach(stage/'review',grant,files,original,cumulative['changes'],candidate)
        if wire is not None:
            pce._write(stage/'review','wire-declaration.json',pce._json(grant['review_wire']),immutable=True)
        for name, text in [('successor.json',pce._json(record)), ('request.json',pce._json(request)),
                           ('candidate.tex',candidate), ('returned-findings.json',pce._json(findings)),
                           ('evidence-snapshots.json',pce._json(snapshots))]:
            pce._write(stage,name,text,immutable=True)
        pce._write(stage/'review','frozen-inputs.json',pce._json(files),immutable=True)
        pce._write(stage/'review','grant.json',pce._json(grant),immutable=True)
        stage.rename(root)
    pce._write(pending.parent,pending.name,pce._json({'id':identity}))
    return root, request, bib


def run(campaign, pair, *, apply=False, accept_change=None, **kwargs):
    with health.owner(campaign,nested=True), runner.Lock(campaign.thread_dir(pair)):
        root, request, bib = prepare(campaign,pair,**kwargs)
        if (root/'acceptance.json').exists():
            result = 'accepted; run present PAIR --edited'
        elif account_review.workflow(root) != root/'review':
            raise pce.Changed('resume the explicit account evidence review grant')
        elif not apply:
            return 'successor prepared; acceptance unchanged; no calls; repeat with --apply for one fixed-candidate review'
        else:
            if runner.stopped(campaign) or not runner.guard_ok(campaign,inflight=1):
                return 'stopped: successor retained; acceptance unchanged'
            with provenance.run_context(campaign,accept_change):
                c = copy.copy(campaign); c._pce_workflow = root/'review'
                reviewed = pce.run(c,pair,stop=lambda:runner.stopped(campaign))
            prepare(campaign,pair,**kwargs)
            result = account_amend.finish(campaign,pair,root,root/'review',request,bib,reviewed)
        if (root/'acceptance.json').exists():
            pce._write(campaign.thread_dir(pair)/'edited','account-amendment.json',pce._json({'id':kwargs['identity']}))
            account_amend.selected(campaign,pair,*account_release.source(campaign,pair))
        return result
