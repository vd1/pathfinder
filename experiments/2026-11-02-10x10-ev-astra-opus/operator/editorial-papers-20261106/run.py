import os,sys,json,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OP=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'engine'))
os.environ['PATH']='/Users/v/.local/bin:/opt/homebrew/bin:/Library/TeX/texbin:'+os.environ.get('PATH','')
os.environ['PATHFINDER_CODEX']='/Users/v/Code_2026/nobel/pilot-question/runtime-codex-0.163.0-bazel/bin/codex'
from pathfinder import config,provenance,paper,presentation
state={'status':'running','pid':os.getpid(),'pairs':{}}
def save():
    (OP/'status.json').write_text(json.dumps(state,indent=2));print(state,flush=True)
try:
    c=config.load(ROOT)
    with provenance.run_context(c,accept_change='User clarified full editorial novelty checkpoint for Q7P1 and Q1P1, no PCE; repaired missing Claude PATH; Nobel presentation module enabled'):
        assert c.raw['edit_scheme']=='single'
        for pid in ['Q7P1','Q1P1']:
            state['pairs'][pid]='author/review';save()
            try:
                result=paper.run(c,pid)
                state['pairs'][pid]=result;save()
                if result=='ACCEPTED':
                    state['pairs'][pid]='notation/presentation';save()
                    state['pairs'][pid]=presentation.run(c,pid);save()
            except Exception as exc:
                state['pairs'][pid]={'error':str(exc)};save();traceback.print_exc()
        state['status']='finished';save()
except Exception as exc:
    state['status']='failed';state['error']=str(exc);save();raise
