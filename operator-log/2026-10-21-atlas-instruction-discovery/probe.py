import os,sys,json,tempfile,subprocess
from pathlib import Path
sys.path.insert(0,'/private/tmp/pathfinder-research-only-b18d4dd')
from pathfinder import sandbox
exe='/Users/v/Code_2026/nobel/pilot-question/runtime-codex-0.163.0-bazel/bin/codex'
base=Path('/private/tmp/pathfinder-atlas-instruction-probe')
work=base/'project/child';work.mkdir(parents=True,exist_ok=True)
(work.parent/'AGENTS.md').write_text('ANCESTOR_SENTINEL_DO_NOT_IMPORT\n')
home=base/'codex-home';home.mkdir(exist_ok=True)
(home/'AGENTS.md').write_text('HOME_SENTINEL_DO_NOT_IMPORT\n')
rows=[]
for disabled in (False,True):
 cmd=[exe,'--cd',str(work),'-c','approval_policy="never"']
 cmd+=sandbox.args(work,True,{'read':['/opt/homebrew',str(Path(exe).parents[1])]},False,None)
 cmd+=['-c','features.shell_snapshot=false','-c','features.apps=false']
 if disabled:cmd+=['-c','project_doc_max_bytes=0','-c','features.skip_host_skill_discovery=true']
 cmd+=['debug','prompt-input','OFFLINE_CONTEXT_PROBE']
 env={**os.environ,'CODEX_HOME':str(home)}
 r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30)
 (base/f'output-{disabled}.json').write_text(r.stdout)
 (base/f'stderr-{disabled}.txt').write_text(r.stderr)
 rows.append({'disabled':disabled,'returncode':r.returncode,'stdout_chars':len(r.stdout),'stderr':r.stderr[-1500:],
              'ancestor_imported':'ANCESTOR_SENTINEL_DO_NOT_IMPORT' in r.stdout,'home_imported':'HOME_SENTINEL_DO_NOT_IMPORT' in r.stdout})
print(json.dumps(rows,indent=2))
(base/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
