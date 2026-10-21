import os,sys,json,subprocess
from pathlib import Path
sys.path.insert(0,'/private/tmp/pathfinder-research-only-b18d4dd')
from pathfinder import config,sandbox,library
root=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-2/runs/pair-1')
work=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-2/operator/runtime-smoke/work')
c=config.load(root)
exe='/Users/v/Code_2026/nobel/pilot-question/runtime-codex-0.163.0-bazel/bin/codex'
out=Path('/private/tmp/pathfinder-atlas-instruction-probe')
home=out/'exact-home';home.mkdir(exist_ok=True)
(home/'AGENTS.md').write_bytes(Path('/Users/v/.codex/AGENTS.md').read_bytes())
rows=[]
for mode in ('exact','no-project-discovery','explicit-agent-file'):
 settings=c.raw['codex']['filesystem_profile'].copy()
 if mode=='explicit-agent-file': settings['read']=[*settings['read'],'/Users/v/Code_2026/qap-atlas/AGENTS.md']
 cmd=[exe,'--cd',str(work),'-c','approval_policy="never"']
 cmd+=sandbox.args(work,True,settings,True,library.cache(c))
 if mode=='no-project-discovery':cmd+=['-c','project_doc_max_bytes=0','-c','features.skip_host_skill_discovery=true']
 cmd+=['debug','prompt-input','OFFLINE_EXACT_ATLAS_PROBE']
 env={**os.environ,'CODEX_HOME':str(home)}
 r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=30)
 (out/f'exact-{mode}-stdout.json').write_text(r.stdout)
 rows.append({'mode':mode,'argv':cmd,'exit':r.returncode,'stderr':r.stderr,'stdout_chars':len(r.stdout)})
print(json.dumps([{k:v for k,v in r.items() if k!='argv'} for r in rows],indent=2))
(out/'exact-results.json').write_text(json.dumps(rows,indent=2)+'\n')
