"""Classic verifier reassessment or retained-response restoration on an exact follow-up copy."""
import copy
import hashlib
import json
import shutil
from pathlib import Path
from . import config, context, contracts, health, pce, pce_recovery, provenance, research, resources, routing, runner, transport
from .context import Section
from .ledger import Ledger


def prepare(campaign, pair, origin, reason, receipt=None):
    origin = config.load(Path(origin))
    d = campaign.thread_dir(pair); old = origin.thread_dir(pair)
    root = d / 'reassessment'
    if not reason.strip() or campaign.root.resolve() == origin.root.resolve():
        raise pce.Changed('reassessment requires a distinct follow-up copy and an explicit reason')
    if campaign.raw != origin.raw or campaign.raw.get('research_scheme') or campaign.raw.get('research_bundles'):
        raise pce.Changed('classic replay requires unchanged campaign configuration and no research scheme')
    if root.exists():
        request = json.loads((root/'request.json').read_text())
        if (request['origin'] != str(origin.root) or request['reason'] != reason
                or request.get('restore_receipt') != receipt):
            raise pce.Changed('this copy already binds another reassessment')
        return request
    if runner.Lock.holder(old) or any(health.alive(x.get('pid')) or health.alive(x.get('child_pid'))
        for x in (health.read(p) or {} for p in origin.path('active-calls').glob('*.json')) if x.get('thread')==pair):
        raise pce.Changed('original thread still active; copy only an idle terminal snapshot')
    status = research.status(origin,pair)
    if status.get('status') not in ('PAUSE','PAUSE-ON-ITERATE','PAUSE-ON-REVISE','DRAFT'):
        raise pce.Changed('original must be a finished classic thread')
    hashes = pce_recovery.hashes(old)
    copied = pce_recovery.hashes(d)
    # The destination thread lock is an engine transient, not research evidence.
    hashes = {k:v for k,v in hashes.items() if k != 'lock'}
    copied = {k:v for k,v in copied.items() if k != 'lock'}
    if (hashes != copied or any(p.is_symlink() for p in d.rglob('*'))
            or any((d/name).samefile(old/name) for name in hashes)):
        raise pce.Changed('follow-up thread is not an exact independent copy of the original')
    request = {'origin':str(origin.root),'pair':pair,'reason':reason,'source_files_sha256':hashes,
               'source_status':status,'config':campaign.raw,'prompts':resources.prompt_digests(campaign),
               'engine':provenance.engine(), 'original_run':health.read(origin.path('run.json'))}
    if receipt is not None:
        from . import verifier_receipt
        restored = verifier_receipt.inspect(origin, pair, receipt)
        request.update(restore_receipt=receipt, retained_response=restored)
    # Verify the source was stable during snapshot inspection, without writing a lock there.
    if {k:v for k,v in pce_recovery.hashes(old).items() if k!='lock'} != hashes:
        raise pce.Changed('original changed during inspection; take a new copy')
    pce._write(root,'request.json',pce._json(request),immutable=True)
    archive=root/'prior';archive.mkdir()
    for name in ('status.json','ledger.jsonl',f'{pair}.tex',f'{pair}.verdict.json','pathfinder-meta.tex'):
        if (d/name).exists():shutil.copy2(d/name,archive/name)
    for name in ('verify-pending.json','verify-unreadable.txt','edited','paper','actionability.json','significance'):
        if (d/name).exists():shutil.move(str(d/name),str(archive/name))
    pce._write(root,'prepared.json',pce._json({'ready':True}),immutable=True)
    return request


def run(campaign,pair,*,origin=None,reason=None,apply=False,accept_change=None,receipt=None):
    with health.owner(campaign,nested=True),runner.Lock(campaign.thread_dir(pair)):
        d=campaign.thread_dir(pair);root=d/'reassessment'
        if origin is not None:
            prepare(campaign,pair,origin,reason or '',receipt)
        elif receipt is not None:
            raise pce.Changed('select the retained receipt with the original campaign during preparation')
        if not (root/'prepared.json').exists():
            raise pce.Changed('prepare an exact follow-up copy first')
        grant=json.loads((root/'request.json').read_text())
        if (root/'installed.json').exists():return json.loads((root/'result.json').read_text())
        if campaign.raw != grant['config'] or resources.prompt_digests(campaign)!=grant['prompts']:
            raise pce.Changed('reassessment configuration or prompt changed after preparation')
        # Neither new research nor an older editorial product can enter the replay.
        allowed={'verify-pending.json','verify-unreadable.txt','edited','paper','actionability.json','significance'}
        for name,digest in grant['source_files_sha256'].items():
            if Path(name).parts[0] in allowed:continue
            if (root/'commit.json').exists() and name in ('status.json','ledger.jsonl',f'{pair}.verdict.json','pathfinder-meta.tex'):continue
            if not (d/name).is_file() or hashlib.sha256((d/name).read_bytes()).hexdigest()!=digest:
                raise pce.Changed('reassessment input changed: '+name)
        if not apply:return {'status':'prepared','calls':'none; restore retained verdict' if grant.get('restore_receipt')
                             else 'one verifier response; malformed output stops for inspection'}
        if runner.stopped(campaign) or not runner.guard_ok(campaign,inflight=1):return {'status':'stopped'}
        with provenance.run_context(campaign,accept_change):
            if (root/'commit.json').exists():return _install(campaign,pair,root)
            c=copy.copy(campaign)
            if grant.get('restore_receipt'):
                retained = grant['retained_response']
                raw = retained['original_receipt']
                text = transport._parse(c, raw['model'], raw['raw_events'])[0]
                if text != retained['text']:
                    raise pce.Changed('retained response differs from original receipt')
                verdict = contracts.parse('verify', text)
                if verdict != retained['verdict']:
                    raise pce.Changed('retained verdict differs from its response')
                pce._write(root,'verdict.json',pce._json(verdict),immutable=True)
            else:
                if (c.raw.get('refusal_fallback') or {}).get('backend') not in (None,'codex','stub'):
                    raise pce.Changed('reassessment fallback must stay OpenAI-only')
                inp=research._inputs(d)
                task=research._prompt(c,'verify',Q_INPUT=f"inputs/{inp['Q']}",P_INPUT=f"inputs/{inp['P']}",NOTE=f'{pair}.tex')
                task+='\n\n'+research.evidence_pointer(c)+' Do not modify any file.\n'
                prompt=context.build(c,'verify',research.judge_sections(d,inp,f'{pair}.tex')+[Section('',text='## your task\n\n'+task,keep=True)],tools=True,cwd=d,unit=pair)
                if (root/'prompt.txt').exists():prompt=(root/'prompt.txt').read_text()
                req=research._stage_request(c,pair,'verify',prompt,True,c.allowances['verify_seconds'])
                routed,_=routing.apply(c,req)
                if routed.backend not in ('codex','stub'):
                    raise pce.Changed('reassessment verifier must stay OpenAI-only')
                pce._write(root,'prompt.txt',prompt,immutable=True)
                if not (root/'verdict.json').exists():
                    if not (root/'raw.json').exists():
                        if (root/'dispatch.json').exists():raise pce.Changed('uncertain verifier dispatch; inspect receipts, do not repeat')
                        pce._write(root,'dispatch.json',pce._json({'run_id':c.run_id,'prompt_sha256':pce._sha(prompt)}),immutable=True)
                        raw=transport.execute(c,req)
                        pce._write(root,'raw.json',pce._json(raw),immutable=True)
                    raw=json.loads((root/'raw.json').read_text())
                    if raw.get('error') or raw.get('failure'):raise pce.Changed('verifier failed; raw retained; no automatic new call')
                    # A malformed response stops for inspection rather than spending a new verdict.
                    verdict=contracts.parse('verify',raw.get('text',''))
                    pce._write(root,'verdict.json',pce._json(verdict),immutable=True)
            verdict=json.loads((root/'verdict.json').read_text())
            if not (root/'commit.json').exists():
                old=grant['source_status'];dec=verdict['decision'];now=research._now()
                status={**old,'reason':verdict.get('reason'),'updated':now,'failure':None}
                ledger=(root/'prior/ledger.jsonl').read_text()
                if dec=='ITERATE' and old['round']<campaign.rounds:
                    status.update(status='stopped',stage='peers',round=old['round']+1)
                elif dec=='REVISE' and old.get('repairs',0)<campaign.raw.get('repairs',1):
                    status.update(status='stopped',stage='consolidate',repairs=old.get('repairs',0)+1,repair=verdict)
                else:status.update(status={'ITERATE':'PAUSE-ON-ITERATE','REVISE':'PAUSE-ON-REVISE'}.get(dec,dec),stage='done')
                if dec in ('ITERATE','REVISE'):
                    rows=[json.loads(x) for x in ledger.splitlines() if x.strip()]
                    ledger+=json.dumps({'seq':len(rows)+1,'at':now,'actor':'verifier','kind':'review',
                         'text':f"{dec}: {verdict.get('reason')} Action: {verdict.get('action')}",'supersedes':None,'seen':None})+'\n'
                oldv=root/'prior'/f'{pair}.verdict.json';history=json.loads(oldv.read_text()) if oldv.exists() else []
                history.append({'round':old['round'],'at':now,'note_sha256':grant['source_files_sha256'][f'{pair}.tex'],
                                'reassessment':True,**({'restored_receipt':grant['restore_receipt']}
                                    if grant.get('restore_receipt') else {}),**verdict})
                targets={'ledger.jsonl':ledger,f'{pair}.verdict.json':json.dumps(history,indent=1),
                         'status.json':json.dumps(status,indent=1)}
                pce._write(root,'commit.json',pce._json(targets),immutable=True)
                pce._write(root,'result.json',pce._json({'verdict':verdict,'status':status,'origin':grant['origin']}),immutable=True)
            return _install(campaign,pair,root)


def _install(campaign,pair,root):
    d=campaign.thread_dir(pair)
    for name,text in json.loads((root/'commit.json').read_text()).items():
        current=(d/name).read_text() if (d/name).exists() else None
        prior=(root/'prior'/name).read_text() if (root/'prior'/name).exists() else None
        if current not in (prior,text):raise pce.Changed('follow-up advanced while installing verifier verdict')
        pce._write(d,name,text)
    research.write_meta(campaign,pair,d)
    pce._write(root,'installed.json',pce._json({'installed':True}),immutable=True)
    return json.loads((root/'result.json').read_text())
