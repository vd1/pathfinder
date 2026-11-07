"""Final-candidate mandatory claims, with separate exact sequential replacement custody."""
import copy
import json
import re
from . import account_amend, account_release, account_review, health, pce, pce_recovery, provenance, runner


def build(baseline, changes, candidate):
    text, owners = baseline, [0] * len(baseline)
    for i, change in enumerate(changes, 1):
        before, after = change['before'], change['after']
        if not before or text.count(before) != 1 or not after or before == after:
            raise pce.Changed('replacement history is ambiguous or empty')
        start = text.index(before); end = start + len(before)
        text = text[:start] + after + text[end:]
        owners[start:end] = [i] * len(after)
    if text != candidate:
        raise pce.Changed('replacement history does not reproduce the final candidate')
    records, claims = [], []
    for i, change in enumerate(changes, 1):
        spans = []
        for match in re.finditer(r'\S(?:[^\n]|\n(?!\s*\n))*', candidate):
            # Paragraph context is taken only from the final manuscript, including partially replaced passages.
            a, b = match.span()
            if any(owner == i and not candidate[k].isspace() for k, owner in enumerate(owners[a:b], a)):
                spans.append([a, b])
        positions = [k for k, owner in enumerate(owners) if owner == i]
        complete = bool(positions) and len(positions) == len(change['after']) and positions[-1]-positions[0]+1 == len(positions)
        if complete:
            quote = candidate[positions[0]:positions[-1]+1]
            assert quote == change['after']
            spans = [[positions[0], positions[-1]+1]]
        else:
            quote = '\n\n'.join(candidate[a:b] for a,b in spans)
        identity = f'amendment-{i}'
        records.append({'id':identity, 'finding':change['finding'], 'after_sha256':pce._sha(change['after']),
                        'status':'surviving' if complete else 'partially-superseded' if spans else 'superseded',
                        'final_spans':spans, 'claim':quote})
        if quote.strip():
            claims.append({'id':identity,'text':quote,'kind':'definition',
                           'location':'final-candidate replacement '+change['finding'],'status':'needs-review'})
    return {'policy':'final-candidate-v1','baseline_sha256':pce._sha(baseline),
            'candidate_sha256':pce._sha(candidate),'history_sha256':pce._sha(pce._json(changes)),
            'records':records,'claims':claims}


def attach(root, grant, files, baseline, changes, candidate):
    register = build(baseline, changes, candidate)
    history = {'baseline':baseline,'changes':changes}
    pce._write(root,'replacement-history.json',pce._json(history),immutable=True)
    pce._write(root,'replacement-register.json',pce._json(register),immutable=True)
    grant['replacement_register'] = {'policy':'final-candidate-v1','history_sha256':pce._sha(pce._json(history)),
                                     'register_sha256':pce._sha(pce._json(register))}
    files['sources/internal/changes.json'] = pce._json({'changes':[
        {'finding':r['finding'],'after':r['claim']} for r in register['records'] if r['claim'].strip()]})
    grant['inputs_sha256'] = pce._sha(pce._json(files))
    return register


def claims(root, grant, candidate):
    binding = grant['replacement_register']
    history = account_amend._read(root/'replacement-history.json')
    register = account_amend._read(root/'replacement-register.json')
    if (binding.get('policy') != 'final-candidate-v1'
        or pce._sha(pce._json(history)) != binding['history_sha256']
        or pce._sha(pce._json(register)) != binding['register_sha256']
        or build(history['baseline'],history['changes'],candidate) != register):
        raise pce.Changed('final-candidate register custody changed')
    visible = account_amend._read(root/'frozen-inputs.json')
    expected = pce._json({'changes':[
        {'finding':r['finding'],'after':r['claim']} for r in register['records'] if r['claim'].strip()]})
    if visible.get('sources/internal/changes.json') != expected:
        raise pce.Changed('visible replacement register differs from final-candidate custody')
    return copy.deepcopy(register['claims'])


def repair(campaign,pair,*,identity,revision=None,grant_id='final-candidate-register-v1',reason,apply=False,accept_change=None):
    from . import account_revision
    with health.owner(campaign,nested=True),runner.Lock(campaign.thread_dir(pair)):
        routes=pce_recovery.preflight(campaign,presentation=True)
        if not revision:raise pce.Changed('register recovery requires an explicit existing child revision')
        if not reason.strip() or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',grant_id):
            raise pce.Changed('register repair needs an explicit reason and grant identifier')
        ed=campaign.thread_dir(pair)/'edited'
        expected={'id':identity,**({'revision':revision} if revision else {})}
        if not any(p.exists() and account_amend._read(p)==expected for p in [ed/'account-amendment.json',ed/'account-successor.json']):
            raise pce.Changed('repair only the current amendment child or pending successor child')
        root=account_amend._base(campaign,pair,identity)
        if (root/'successor.json').exists():
            predecessor=account_amend._read(root/'successor.json')
            if account_amend._read(ed/'account-amendment.json') not in (predecessor['parent_pointer'],expected):
                raise pce.Changed('register repair predecessor was superseded')
            import hashlib
            for name,digest in predecessor['history'].items():
                path=campaign.thread_dir(pair)/name
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                    raise pce.Changed('register repair predecessor history changed')
        if revision:
            if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',revision):raise pce.Changed('invalid child identifier')
            root=root/'revisions'/revision
        target=root/'review-grants'/grant_id
        if (root/'acceptance.json').exists():
            if not (target/'repair.json').exists():raise pce.Changed('cannot repair an accepted review')
            account_revision._install_successor_revision(campaign,pair,dict(identity=identity,revision=revision))
            return 'accepted; run present PAIR --edited'
        request,candidate,bib=account_review.custody(campaign,pair,root)
        saved=account_amend._read(target/'repair.json') if (target/'repair.json').exists() else None
        previous=root/saved['previous'] if saved else account_review.workflow(root)
        if account_review.workflow(root) not in (previous,target):raise pce.Changed('register repair was superseded')
        if account_amend._read(previous/'result.json')['status']!='review_required':
            raise pce.Changed('register repair requires a terminal failed round')
        original,_,_=account_release.source(campaign,pair)
        files=account_amend._read(previous/'frozen-inputs.json')
        old_files=copy.deepcopy(files)
        grant=account_amend._read(previous/'grant.json')
        binding={'previous':str(previous.relative_to(root)),'previous_sha256':pce_recovery.hashes(previous),
                 'reason':reason.strip(),'candidate_sha256':pce._sha(candidate),
                 'request_sha256':pce._sha(pce._json(request)),
                 'routes':{k:v for k,v in routes.items() if k.startswith('edit/')}}
        if saved and saved!=binding:raise pce.Changed('register repair history or authority changed')
        register=build(original,request['changes']['changes'],candidate)
        if not any(r['status']!='surviving' for r in register['records']):
            raise pce.Changed('no superseded mandatory replacement to repair')
        grant['routes']=binding['routes'];grant['settings']['passes']=1;grant['settings']['fact_checks']=1
        grant['strict_evidence']=True
        attach(target,grant,files,original,request['changes']['changes'],candidate)
        assert all(files[n]==t for n,t in old_files.items() if n!='sources/internal/changes.json')
        for name,value in [('repair.json',binding),('frozen-inputs.json',files),('grant.json',grant)]:
            pce._write(target,name,pce._json(value),immutable=True)
        pce._write(root,'review-active.json',pce._json({'grant':grant_id}))
        if not apply:return 'register repair prepared; same candidate and evidence; no calls; one fresh fixed-candidate review'
        if runner.stopped(campaign) or not runner.guard_ok(campaign,inflight=1):return 'stopped: register repair retained'
        with provenance.run_context(campaign,accept_change):
            c=copy.copy(campaign);c._pce_workflow=target
            result=pce.run(c,pair,stop=lambda:runner.stopped(campaign))
        account_review.custody(campaign,pair,root)
        if pce_recovery.hashes(previous)!=binding['previous_sha256']:raise pce.Changed('prior failed round changed')
        outcome=account_amend.finish(campaign,pair,root,target,request,bib,result)
        if (root/'acceptance.json').exists():
            account_revision._install_successor_revision(campaign,pair,dict(identity=identity,revision=revision))
        return outcome
