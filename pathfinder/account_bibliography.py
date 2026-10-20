"""Metadata-only bibliography revisions, independent of scientific account acceptance."""
import hashlib
import json
import re
from pathlib import Path
from . import account_release, health, paper, pce, pce_recovery, presentation, runner


def _hash(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def transform(bib, operations, evidence):
    entries=paper.bib_entries(bib);out=bib;used=set()
    if not isinstance(operations,list) or not 1<=len(operations)<=20:raise pce.Changed('provide bounded metadata operations')
    for op in operations:
        key=op['key']
        if key in used or key not in entries:raise pce.Changed('metadata key is missing or repeated')
        used.add(key);entry=entries[key]
        if op['doi']!=entry.get('doi'):raise pce.Changed('metadata operation must preserve the cited DOI')
        proof=evidence[op['evidence']]
        text=json.dumps(json.loads(proof['text']),ensure_ascii=False)
        if not op['quote'] or op['quote'] not in text or op['doi'] not in text:
            raise pce.Changed('metadata quotation/DOI absent from frozen evidence')
        match=re.search(r'@\w+\s*\{\s*'+re.escape(key)+r'\s*,',out)
        start=match.start();i=match.end();depth=1
        while i<len(out) and depth:
            depth+={'{':1,'}':-1}.get(out[i],0);i+=1
        block=out[start:i];new=block
        if op['operation']=='supply-missing-title':
            if entry.get('title') or any(c in op['quote'] for c in '\n\r{}\\'):
                raise pce.Changed('only a missing title may be supplied as plain bibliographic text')
            offset=match.end()-start
            new=block[:offset]+'\n title = {'+op['quote']+'},'+block[offset:]
        elif op['operation']=='registry-year':
            registry=json.loads(proof['text'])
            message=registry.get('message',{})
            if registry.get('status')!='ok' or message.get('DOI','').lower()!=op['doi'].lower():
                raise pce.Changed('Crossref success and exact DOI required')
            parts=message.get('published',{}).get('date-parts',[])
            if len(parts)!=1 or len(parts[0])!=3 or not all(type(v) is int for v in parts[0]):
                raise pce.Changed('registry must supply an explicit publication date')
            year,month,day=parts[0]
            from datetime import date
            date(year,month,day)
            if op['quote'] not in message.get('title',[]):raise pce.Changed('registry title does not match quoted title')
            if re.sub(r'[^a-z0-9]','',entry.get('title','').lower())!=re.sub(r'[^a-z0-9]','',op['quote'].lower()):
                raise pce.Changed('registry title does not match cited title')
            new,n=re.subn(r'(?m)^(\s*year\s*=\s*)\{[^\n{}]*\}',lambda m:m[1]+'{'+str(year)+'}',new)
            if n!=1:raise pce.Changed('year field must be a unique braced line')
            # Remove only the obsolete date qualification, with its exact old text bound.
            if op.get('old_note')!=entry.get('note'):raise pce.Changed('date qualification must be bound exactly')
            new,n=re.subn(r'(?m)^\s*note\s*=\s*\{[^\n{}]*\},?\s*\n','',new)
            if n!=1:raise pce.Changed('date qualification must be a unique braced line')
        else:raise pce.Changed('unsupported metadata operation')
        out=out[:start]+new+out[i:]
    revised=paper.bib_entries(out)
    if set(entries)!=set(revised):raise pce.Changed('bibliography keys changed')
    for key in entries:
        allowed={'title'} if next((x['operation'] for x in operations if x['key']==key),None)=='supply-missing-title' else {'year','note'} if key in used else set()
        if any(entries[key].get(f)!=revised[key].get(f) for f in set(entries[key])|set(revised[key]) if f not in allowed):
            raise pce.Changed('non-metadata bibliography field changed')
    return out


def selected(campaign,pair,note,bib,acceptance):
    ed=campaign.thread_dir(pair)/'edited';pointer=ed/'bibliography-revision.json'
    if not pointer.exists():return bib,None
    identity=json.loads(pointer.read_text())['id']
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',identity):raise pce.Changed('invalid bibliography revision')
    root=ed/'bibliography-revisions'/identity;record=json.loads((root/'record.json').read_text())
    request=record['request']
    if (request['note_sha256']!=pce._sha(note) or request['bibliography_sha256']!=pce._sha(bib)
        or request['acceptance_sha256']!=pce._sha(pce._json(acceptance))):
        raise pce.Changed('bibliography revision belongs to another accepted account')
    for name,digest in record['files_sha256'].items():
        if _hash(root/name)!=digest:raise pce.Changed('bibliography revision content changed')
    parent=ed/'publication'/request['parent_publication']
    for name,digest in request['parent_files_sha256'].items():
        if _hash(parent/name)!=digest:raise pce.Changed('bibliography parent presentation changed')
    corrected=(root/'references.bib').read_text()
    if transform(bib,request['operations'],record['evidence'])!=corrected:
        raise pce.Changed('bibliography revision contains undeclared changes')
    return corrected,{'id':identity,'record_sha256':_hash(root/'record.json'),
                      'scope':'Bibliographic metadata only; original scientific acceptance and manuscript unchanged.',
                      'operations':request['operations'],'evidence':{k:{f:v for f,v in row.items() if f!='text'} for k,row in record['evidence'].items()}}


def run(campaign,pair,*,identity,packet,reason,apply=False):
    pce_recovery.preflight(campaign,presentation=True)
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',identity) or not reason.strip():
        raise pce.Changed('bibliography revision needs an ID and explicit authority')
    with health.owner(campaign,nested=True),runner.Lock(campaign.thread_dir(pair)):
        if runner.stopped(campaign):return 'stopped: bibliography revision not installed'
        view=account_release.view(campaign,pair,bibliography=False);parent=paper.folder(view,pair)
        note=(parent/'paper.tex').read_text();bib=(parent/'references.bib').read_text()
        acceptance=json.loads((parent/'acceptance.json').read_text())
        spec=json.loads((Path(packet)/'metadata.json').read_text());evidence={}
        for name,item in spec['evidence'].items():
            path=Path(item['path']);raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise pce.Changed('metadata evidence changed')
            evidence[name]={**item,'text':raw.decode('utf-8')}
        findings=parent/'presentation/amend-findings.json'
        if (presentation.state(view,pair).get('state')!='RETURNED' or _hash(findings)!=spec['findings_sha256']
            or pce._sha(note)!=spec['note_sha256'] or pce._sha(bib)!=spec['bibliography_sha256']
            or pce._sha(pce._json(acceptance))!=spec['acceptance_sha256']):
            raise pce.Changed('metadata packet does not bind this returned accepted publication')
        if {x['finding'] for x in spec['operations']}!={x['id'] for x in json.loads(findings.read_text())['findings']}:
            raise pce.Changed('metadata operations must address exactly the returned findings')
        corrected=transform(bib,spec['operations'],evidence)
        if corrected!=(Path(packet)/'references.bib').read_text():raise pce.Changed('bibliography candidate differs from exact metadata operations')
        ed=campaign.thread_dir(pair)/'edited';root=ed/'bibliography-revisions'/identity
        request={**spec,'id':identity,'reason':reason.strip(),'parent_publication':parent.name,
                 'parent_files_sha256':pce_recovery.hashes(parent)}
        pce._write(root,'request.json',pce._json(request),immutable=True)
        pce._write(root,'evidence.json',pce._json(evidence),immutable=True)
        pce._write(root,'references.bib',corrected,immutable=True)
        pointer=ed/'bibliography-revision.json'
        if pointer.exists() and json.loads(pointer.read_text())!={'id':identity}:raise pce.Changed('another bibliography revision is selected')
        if (root/'record.json').exists():
            selected(campaign,pair,note,bib,acceptance) if pointer.exists() else None
        elif not apply:return 'bibliography revision prepared; no calls; repeat with --apply for build and metadata selection'
        else:
            build=root/'build';pce._write(build,'paper.tex',note,immutable=True);pce._write(build,'references.bib',corrected,immutable=True)
            ok,log=paper.build(build);pce._write(build,'build-log.txt',log)
            if not ok:return 'bibliography build failed; original selection and acceptance unchanged'
            pce._write(root,'record.json',pce._json({'request':request,'evidence':evidence,
                       'files_sha256':pce_recovery.hashes(root)}),immutable=True)
        if not apply:return 'bibliography revision already built; no calls'
        pce._write(ed,'bibliography-revision.json',pce._json({'id':identity}))
        account_release.view(campaign,pair,create=True)
        return 'bibliography revision installed; manuscript and scientific acceptance unchanged; run present PAIR --edited'
