import os,sys,json,hashlib,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'engine'))
os.environ['PATHFINDER_CODEX']='/Users/v/Code_2026/nobel/pilot-question/runtime-codex-0.163.0-bazel/bin/codex'
os.environ['PATH']='/opt/homebrew/bin:/Library/TeX/texbin:'+os.environ.get('PATH','')
from pathfinder import config,edit,transport,provenance
from pathfinder.paper import build,check_references
D=ROOT/'threads/Q1P1'; ED=D/'edited'
def state(**kw):
    (OP/'status.json').write_text(json.dumps(kw,indent=2)+'\n')
    print(kw,flush=True)
def parse(text):
    text=text.strip()
    if text.startswith('```'): text=text.split('\n',1)[1].rsplit('```',1)[0]
    return json.loads(text)
import time
state(status='queued', waiting_for='Q7P1 editorial pass', pid=os.getpid())
while True:
    prior=json.loads((ROOT/'operator/q7p1-editorial-20261106/status.json').read_text())
    if prior.get('status') in ('done','failed','review_required'):
        time.sleep(3)
        break
    time.sleep(10)
try:
    c=config.load(ROOT)
    with provenance.run_context(c,accept_change='User requested editorial processing of November Q1P1 with Nobel notation module and no PCE'):
        assert c.raw['edit_scheme']=='single'
        state(status='editing',pid=os.getpid())
        result=edit.run(c,'Q1P1')
        if result!='done': raise RuntimeError('Editor ended: '+result)
        prompt=(OP/'checker-source.md').read_text().replace('Referees have accepted its\nmathematics; do not re-check proofs or literature.','This is a research account, not an accepted paper; do not re-check proofs or literature.').replace('the open minor findings the referees left with their acceptance','the editor\'s unresolved findings')
        for cycle in range(2):
            state(status='notation-check',cycle=cycle+1,pid=os.getpid())
            manuscript=(ED/'note.tex').read_text()
            log=(ED/'change-log.md').read_text() if (ED/'change-log.md').exists() else 'No change log supplied.'
            unresolved=(ED/'unresolved.md').read_text() if (ED/'unresolved.md').exists() else 'No separate unresolved file supplied.'
            r=transport.call(prompt+'\nMANUSCRIPT\n'+manuscript+'\nCHANGE LOG\n'+log+'\nUNRESOLVED\n'+unresolved,campaign=c,model=c.model,tools=False,search=False,cwd=D,timeout=900,thread='Q1P1',stage='edit',actor='notation-check')
            if r['transport_failed']: raise RuntimeError('Notation checker transport failure')
            (OP/f'check-{cycle+1}.raw.txt').write_text(r['text'])
            finding=parse(r['text']); finding['manuscript_sha256']=hashlib.sha256(manuscript.encode()).hexdigest()
            (OP/f'check-{cycle+1}.json').write_text(json.dumps(finding,indent=2))
            if finding.get('clear') and not finding.get('findings'): break
            if cycle==1 or any(f.get('kind') in ('meaning','claim') for f in finding.get('findings',[])):
                state(status='review_required',findings=finding,pid=os.getpid()); sys.exit(0)
            state(status='notation-correction',pid=os.getpid())
            correction='Apply the attached Nobel notation findings to edited/note.tex. Read edited/change-log.md and edited/unresolved.md. Make only unambiguous definitions and wording repairs; preserve mathematical claims, assumptions and bibliography. Do not invent definitions, constants or cited claims. Record any unresolved ambiguity instead. Update the change log. Build the PDF using latexmk in edited/. Do not run PCE or change research files.\n'+json.dumps(finding)
            r=transport.call(correction,campaign=c,model=c.model,tools=True,search=False,cwd=D,timeout=900,thread='Q1P1',stage='edit',actor='notation-correct')
            (OP/'correction.txt').write_text(r.get('text') or '')
            if r['transport_failed']: raise RuntimeError('Notation correction transport failure')
        ok,log=build(ED,main='note.tex')
        checks=check_references((ED/'note.tex').read_text(),(ED/'references.bib').read_text())
        (OP/'final-build.log').write_text(log)
        state(status='done' if ok and not checks else 'review_required',build_ok=ok,reference_checks=checks,pid=os.getpid(),pdf=str(ED/'note.pdf'))
except Exception as exc:
    state(status='failed',error=str(exc),pid=os.getpid()); traceback.print_exc(); raise
