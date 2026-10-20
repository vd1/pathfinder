"""Exact legacy strict-grant prompt/receipt comparison to pre-change frozen engine."""
import os
import subprocess
import sys
import json
from pathlib import Path
import pytest

def test_legacy_frozen_prompts_and_receipts_identical(tmp_path):
 old=Path('/private/tmp/pathfinder-selector-9aaf946')
 if not old.exists():pytest.skip('historical frozen runtime absent')
 from pathfinder import pce
 current=Path(__file__).resolve().parents[1]
 current_runtime=Path(pce.__file__).resolve().parents[1]
 script=tmp_path/'compare.py'
 script.write_text('''import json,sys,shutil
from pathlib import Path
from test_pce import ready
from pathfinder import pce,pce_recovery,stub,config
base=Path(sys.argv[1])
if base.exists():
 c=config.load(base);shutil.rmtree(pce.workflow(c,'Q1P1'))
else:
 base.mkdir();c=ready(base)
root=pce.workflow(c,'Q1P1');root.mkdir(parents=True,exist_ok=True)
files=pce.sources(c,'Q1P1');files['sources/internal/changes.json']=pce._json({'changes':[]});grant=dict(settings=pce.settings(c),routes={},inputs_sha256=pce._sha(pce._json(files)),strict_evidence=True,fixed_candidate=True)
(root/'frozen-inputs.json').write_text(pce._json(files));(root/'grant.json').write_text(pce._json(grant))
pce_recovery.preflight=lambda *a,**kw:{}
calls=[]
def dispatch(c,pair,role,prompt,seconds=None):
 calls.append(dict(role=role,prompt=prompt));return dict(role=role,outcome='completed',text=stub.pce_reply(c,role,prompt))
pce._dispatch=dispatch
result=pce.run(c,'Q1P1')
assert result['status']=='accepted' and len(calls)==5
artifacts={str(p.relative_to(root)):p.read_text() for folder in ['dispatch','visibility'] for p in (root/folder).glob('*.json')}
Path(sys.argv[2]).write_text(json.dumps(dict(calls=calls,artifacts=artifacts),sort_keys=True))
''')
 outputs=[]
 for name,runtime in [('old',old),('new',current_runtime)]:
  output=tmp_path/(name+'.json');env=dict(os.environ,PYTHONPATH=str(runtime)+':'+str(current/'tests'))
  proc=subprocess.run([sys.executable,'-P',str(script),str(tmp_path/'same-campaign'),str(output)],env=env,capture_output=True,text=True)
  assert proc.returncode==0,proc.stderr
  outputs.append(json.loads(output.read_text()))
 assert outputs[0]==outputs[1]
