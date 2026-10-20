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


def _operator_framing(campaign, pair, delta):
    """A separate operator scope may delete only complete internal-status sentences."""
    scope=delta.get('operator_framing')
    if scope is None:return set()
    import hashlib
    if (scope.get('kind')!='operator-framing-v1' or not isinstance(scope.get('authority'),str)
        or not scope['authority'].strip() or scope.get('parent_candidate_sha256')!=delta['parent_candidate_sha256']
        or scope.get('scientific_status_sha256')!=hashlib.sha256((campaign.thread_dir(pair)/'status.json').read_bytes()).hexdigest()):
        raise pce.Changed('operator framing authority, candidate or scientific status binding differs')
    changes=scope.get('changes')
    if not isinstance(changes,list) or not 1<=len(changes)<=4:
        raise pce.Changed('operator framing requires 1-4 exact status-sentence removals')
    ids=set()
    for change in changes:
        removed=change.get('remove','')
        if (not re.fullmatch(r'operator-framing-[a-zA-Z0-9_-]+',change['finding'])
            or not re.fullmatch(r'The thread ended at (?:PAUSE|DRAFT)(?:, as specified (?:in|by) the brief)?\. ',removed)
            or change['before'].count(removed)!=1 or change['after']!=change['before'].replace(removed,'',1)
            or not change['after']):
            raise pce.Changed('operator framing may only remove an exact internal-status sentence')
        ids.add(change['finding'])
    if [c for c in delta['changes'] if c['finding'] in ids]!=changes:
        raise pce.Changed('operator framing changes differ from the declared exact delta')
    return ids


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
    operator_ids=_operator_framing(campaign,pair,delta)
    binding={'id':identity,'revision':revision,'reason':reason,'changes':changes,'revision_changes':delta,
             'candidate_sha256':pce._sha(candidate)}
    pointer=thread/'edited/account-amendment.json'
    selected=json.loads(pointer.read_text())
    successor_pointer=thread/'edited/account-successor.json'
    pending=json.loads(successor_pointer.read_text()) if successor_pointer.exists() else {}
    successor_mode=selected['id']!=identity and pending.get('id')==identity
    if selected['id']!=identity and not successor_mode:
        raise pce.Changed('revise only the selected amendment or its pending successor')
    if successor_mode:
        record=json.loads((base/'successor.json').read_text())
        if selected!=record['parent_pointer']:
            raise pce.Changed('pending successor predecessor was superseded')
        import hashlib
        for name,digest in record['history'].items():
            path=thread/name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise pce.Changed('successor predecessor history changed')
    def select_revision():
        destination=successor_pointer if successor_mode else pointer
        pce._write(destination.parent,destination.name,pce._json({'id':identity,'revision':revision}))
    def current_root():
        if not successor_mode:return account_amend._root(campaign,pair,identity)
        previous=pending.get('revision')
        if previous is not None and not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',previous):
            raise pce.Changed('invalid pending successor revision')
        return base/'revisions'/previous if previous else base

    if (root/'revision.json').exists():
        grant=json.loads((root/'revision.json').read_text())
        if grant['binding']!=binding:
            raise pce.Changed('revision identity binds different inputs')
        if operator_ids and json.loads((root/'operator-framing.json').read_text())!=delta['operator_framing']:
            raise pce.Changed('recorded operator framing scope changed')
        active=pending if successor_mode else selected
        if (active.get('revision')!=revision
            and str(current_root().relative_to(thread))!=grant['parent']):
            raise pce.Changed('revision was superseded')
        parent=thread/grant['parent']
        if _history(parent)!=grant['parent_sha256']:
            raise pce.Changed('previous amendment history changed')
        request,_,bib=account_review.custody(campaign,pair,root)
        select_revision()
        return root,request,bib
    parent=current_root()
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
    if (not findings and not operator_ids) or len(findings)>20:raise pce.Changed('bind terminal reviewer findings or explicit operator framing')
    ids=set()
    for finding in findings:
        rel=Path(finding['path']);path=review/rel
        passes=old_result.get('passes')
        latest_editor=f"reviews/history/pass-{passes:02d}-editor.json" if type(passes) is int and passes>0 else None
        terminal_editor=(str(rel)==latest_editor and str(rel) in old_result.get('history',[]))
        if (rel.is_absolute() or '..' in rel.parts or not (str(rel).startswith('reviews/current/') or terminal_editor)
            or not path.resolve().is_relative_to(review.resolve()) or path.is_symlink()):
            raise pce.Changed('revision findings must come from the terminal current review')
        text=path.read_text()
        if terminal_editor and json.loads(text).get('decision')!='revise':
            raise pce.Changed('terminal editor feedback must request revision')
        if finding['id'] in ids or finding['id'] in operator_ids:raise pce.Changed('duplicate or mixed finding authority')
        if pce._sha(text)!=finding['sha256'] or not finding['quote'] or text.count(finding['quote'])!=1:
            raise pce.Changed('review finding hash or exact quote differs')
        ids.add(finding['id'])
    if {x['finding'] for x in delta['changes']}!=ids|operator_ids:
        raise pce.Changed('each replacement must bind reviewer findings or its separate operator framing scope')
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
    from . import account_register
    account_register.attach(root/'review',settings,files,original,changes['changes'],candidate)
    pce._write(root,'revision.json',pce._json(record),immutable=True)
    if operator_ids:pce._write(root,'operator-framing.json',pce._json(delta['operator_framing']),immutable=True)
    for name,text in [('request.json',pce._json(request)),('candidate.tex',candidate),
                      ('evidence-snapshots.json',(parent/'evidence-snapshots.json').read_text()),
                      ('returned-findings.json',(parent/'returned-findings.json').read_text())]:
        pce._write(root,name,text,immutable=True)
    pce._write(root/'review','frozen-inputs.json',pce._json(files),immutable=True)
    pce._write(root/'review','grant.json',pce._json(settings),immutable=True)
    root.rename(target)
    select_revision()
    return target,request,bib


def run(campaign,pair,*,apply=False,accept_change=None,**kwargs):
    with health.owner(campaign,nested=True),runner.Lock(campaign.thread_dir(pair)):
        root,request,bib=prepare(campaign,pair,**kwargs)
        if (root/'acceptance.json').exists():
            _install_successor_revision(campaign,pair,kwargs)
            account_amend.selected(campaign,pair,*account_release.source(campaign,pair))
            return 'accepted; run present PAIR --edited'
        if account_review.workflow(root) != root/'review':
            raise pce.Changed('resume the explicit account review/register repair grant')
        if not apply:return 'revision prepared; no calls; repeat with --apply for one fixed-candidate review'
        if runner.stopped(campaign) or not runner.guard_ok(campaign,inflight=1):return 'stopped: revision retained'
        with provenance.run_context(campaign,accept_change):
            c=copy.copy(campaign);c._pce_workflow=root/'review'
            result=pce.run(c,pair,stop=lambda:runner.stopped(campaign))
        prepare(campaign,pair,**kwargs)
        outcome=account_amend.finish(campaign,pair,root,root/'review',request,bib,result)
        if (root/'acceptance.json').exists():_install_successor_revision(campaign,pair,kwargs)
        return outcome


def _install_successor_revision(campaign,pair,args):
    ed=campaign.thread_dir(pair)/'edited'
    pending=ed/'account-successor.json'
    expected={'id':args['identity'],'revision':args['revision']}
    if pending.exists() and json.loads(pending.read_text())==expected:
        pce._write(ed,'account-amendment.json',pce._json(expected))
