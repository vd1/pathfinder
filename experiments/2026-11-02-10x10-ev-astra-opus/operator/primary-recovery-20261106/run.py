import os,sys,json,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'engine'))
os.environ['PATH']='/Users/v/.local/bin:/opt/homebrew/bin:/Library/TeX/texbin:'+os.environ.get('PATH','')
os.environ['PATHFINDER_CODEX']='/Users/v/Code_2026/nobel/pilot-question/runtime-codex-0.163.0-bazel/bin/codex'
from pathfinder import config,provenance,paper,presentation
state={'status':'waiting for existing editorial pass','pid':os.getpid(),'pairs':{}}
def save():
 (OP/'status.json').write_text(json.dumps(state,indent=2));print(state,flush=True)
save()
try:
 previous=ROOT/'operator/editorial-papers-20261106/status.json'
 while json.loads(previous.read_text()).get('status')=='running':
  time.sleep(30)
 c=config.load(ROOT)
 with provenance.run_context(c,accept_change='User authorized primary-source recovery and substantive editorial comparison; no PCE; keep Nobel presentation pass'):
  state['status']='running';save()
  for pid in ['Q7P1','Q1P1']:
   state['pairs'][pid]='author/review on recovered primary sources';save()
   try:
    result=paper.amend(c,pid,OP/(pid+'-findings.json'))
    state['pairs'][pid]=result;save()
    if result=='ACCEPTED':
     state['pairs'][pid]='notation/presentation';save()
     state['pairs'][pid]=presentation.run(c,pid,restart=True);save()
   except Exception as exc:
    state['pairs'][pid]={'error':str(exc)};save();traceback.print_exc()
 state['status']='finished';save()
except Exception as exc:
 state['status']='failed';state['error']=str(exc);save();raise
