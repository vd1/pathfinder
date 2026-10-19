"""Explicit revised fixed candidates beneath an existing, unsuccessful amendment ID."""
import copy
import json
import re
from pathlib import Path
from . import account_amend, account_release, account_review, health, pce, pce_recovery, provenance, runner


def _apply(text, changes):
    if not isinstance(changes,list) or not 1<=len(changes)<=20:
        raise pce.Changed('revision requires 1-20 explicit replacements')
    for change in changes:
        before,after=change['before'],change['after']
        if not before or text.count(before)!=1 or not after or before==after:
            raise pce.Changed('revision replacement is ambiguous or empty')
        text=text.replace(before,after,1)
    return text


def _history(root):
    return {k:v for k,v in pce_recovery.hashes(root).items() if not k.startswith('revisions/')}


def prepare(campaign,pair,*,identity,revision,packet,reason):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',revision or '') or not reason.strip():
        raise pce.Changed('revision needs an explicit ID and authority')
    routes=pce_recovery.preflight(campaign,presentation=True)
    thread=campaign.thread_dir(pair)
    base=account_amend._base(campaign,pair,identity)
    root=base/'revisions'/revision
    packet=Path(packet)
    changes=json.loads((packet/'changes.json').read_text())
    delta=json.loads((packet/'revision.json').read_text())
    candidate=(packet/'account-candidate.tex').read_text()
    binding={'id':identity,'revision':revision,'reason':reason,'changes':changes,'revision_changes':delta,
             'candidate_sha256':pce._sha(candidate)}
    pointer=thread/'edited/account-amendment.json'
    selected=json.loads(pointer.read_text())
    if selected['id']!=identity:raise pce.Changed('revise only the selected amendment')
    if (root/'revision.json').exists():
        grant=json.loads((root/'revision.json').read_text())
        if grant['binding']!=binding:
            raise pce.Changed('revision identity binds different inputs')
        if (selected.get('revision')!=revision
            and str(account_amend._root(campaign,pair,identity).relative_to(thread))!=grant['parent']):
            raise pce.Changed('revision was superseded')
        parent=thread/grant['parent']
        if _history(parent)!=grant['parent_sha256']:
            raise pce.Changed('previous amendment history changed')
        request,_,bib=account_review.custody(campaign,pair,root)
        pce._write(pointer.parent,pointer.name,pce._json({'id':identity,'revision':revision}))
        return root,request,bib
    parent=account_amend._root(campaign,pair,identity)
    if (parent/'acceptance.json').exists():raise pce.Changed('cannot revise an accepted amendment with this path')
    review=account_review.workflow(parent)
    old_result=json.loads((review/'result.json').read_text()) if (review/'result.json').exists() else {}
    if old_result.get('status')!='review_required':raise pce.Changed('previous review must be terminal review_required')
    old_request,old_candidate,bib=account_review.custody(campaign,pair,parent)
    original,_,_=account_release.source(campaign,pair)
    if (delta['parent_candidate_sha256']!=pce._sha(old_candidate)
        or changes['baseline_sha256']!=pce._sha(original)
        or changes['candidate_sha256']!=pce._sha(candidate)
        or _apply(old_candidate,delta['changes'])!=candidate
        or _apply(original,changes['changes'])!=candidate):
        raise pce.Changed('candidate must match both original-baseline and previous-candidate exact changes')
    findings=delta.get('findings',[])
    if not findings or len(findings)>20:raise pce.Changed('bind the terminal reviewer findings explicitly')
    ids=set()
    for finding in findings:
        rel=Path(finding['path']);path=review/rel
        if (rel.is_absolute() or '..' in rel.parts or not str(rel).startswith('reviews/current/')
            or not path.resolve().is_relative_to(review.resolve()) or path.is_symlink()):
            raise pce.Changed('revision findings must come from the terminal current review')
        text=path.read_text()
        if pce._sha(text)!=finding['sha256'] or not finding['quote'] or text.count(finding['quote'])!=1:
            raise pce.Changed('review finding hash or exact quote differs')
        ids.add(finding['id'])
    if {x['finding'] for x in delta['changes']}!=ids:
        raise pce.Changed('each revision replacement must bind the approved reviewer findings')
    if not {x['finding'] for x in old_request['changes']['changes']} <= {x['finding'] for x in changes['changes']}:
        raise pce.Changed('retain the original mandatory amendment findings')
    files=json.loads((review/'frozen-inputs.json').read_text())
    files[pce.BASELINE]=candidate
    files['sources/internal/changes.json']=pce._json(changes)
    settings=json.loads((review/'grant.json').read_text())
    settings['routes']={k:v for k,v in routes.items() if k.startswith('edit/')}
    settings['inputs_sha256']=pce._sha(pce._json(files))
    settings['settings']['passes']=1;settings['settings']['fact_checks']=1
    request={**old_request,'reason':reason,'changes':changes,'candidate_sha256':pce._sha(candidate)}
    record={'binding':binding,'parent':str(parent.relative_to(thread)),'parent_sha256':_history(parent)}
    target=root
    root=root.with_name('.'+revision+'.preparing')
    pce._write(root,'revision.json',pce._json(record),immutable=True)
    for name,text in [('request.json',pce._json(request)),('candidate.tex',candidate),
                      ('evidence-snapshots.json',(parent/'evidence-snapshots.json').read_text()),
                      ('returned-findings.json',(parent/'returned-findings.json').read_text())]:
        pce._write(root,name,text,immutable=True)
    pce._write(root/'review','frozen-inputs.json',pce._json(files),immutable=True)
    pce._write(root/'review','grant.json',pce._json(settings),immutable=True)
    root.rename(target)
    pce._write(pointer.parent,pointer.name,pce._json({'id':identity,'revision':revision}))
    return target,request,bib


def run(campaign,pair,*,apply=False,accept_change=None,**kwargs):
    with health.owner(campaign,nested=True),runner.Lock(campaign.thread_dir(pair)):
        root,request,bib=prepare(campaign,pair,**kwargs)
        if (root/'acceptance.json').exists():
            account_amend.selected(campaign,pair,*account_release.source(campaign,pair))
            return 'accepted; run present PAIR --edited'
        if not apply:return 'revision prepared; no calls; repeat with --apply for one fixed-candidate review'
        if runner.stopped(campaign) or not runner.guard_ok(campaign,inflight=1):return 'stopped: revision retained'
        with provenance.run_context(campaign,accept_change):
            c=copy.copy(campaign);c._pce_workflow=root/'review'
            result=pce.run(c,pair,stop=lambda:runner.stopped(campaign))
        prepare(campaign,pair,**kwargs)
        return account_amend.finish(campaign,pair,root,root/'review',request,bib,result)
