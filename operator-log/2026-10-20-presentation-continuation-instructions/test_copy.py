import json, shutil
import pytest
from pathlib import Path
from pathfinder import config, account_release, account_present, pce_recovery, presentation, paper, alerts
from test_presentation import _script, check, manuscript
PACK=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-20-presentation-continuation-instructions')
PAIR='Q024-P022'
SRC=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2')

@pytest.mark.parametrize('decision',['preserve','delete'])
def test_copy(tmp_path,monkeypatch,decision):
 import os
 assert Path(account_present.__file__).resolve().is_relative_to(Path(os.environ.get('PATHFINDER_TEST_RUNTIME','/Users/v/Code_2026/pathfinder')))
 monkeypatch.setenv('PATHFINDER_ACCOUNTS',str(tmp_path/'accounts'))
 monkeypatch.setenv('PATHFINDER_SOURCE_CACHE',str(tmp_path/'pool'))
 monkeypatch.setenv('PATHFINDER_OFFLINE','1')
 monkeypatch.setattr(alerts,'_desktop',lambda *a:'suppressed')
 monkeypatch.setattr(paper,'_arxiv_titles',lambda ids:{})
 dst=tmp_path/'campaign';dst.mkdir()
 for name in ['campaign.json','import.json','Q.jsonl','P.jsonl','shortlist.json']:
  if (SRC/name).exists():shutil.copy(SRC/name,dst/name)
 st=SRC/'threads'/PAIR;dt=dst/'threads'/PAIR;dt.mkdir(parents=True)
 for p in st.iterdir():
  if p.is_file() and p.suffix in ('.json','.jsonl','.tex'):shutil.copy(p,dt/p.name)
 shutil.copytree(st/'edited',dt/'edited');shutil.copytree(st/'inputs',dt/'inputs')
 for entry in json.loads((PACK/'context.json').read_text())['contexts']:
  p=dt/entry['source'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy(st/entry['source'],p)
 c=config.load(dst);c.backend='stub';c.model='stub';c.raw.update(backend='stub',model='stub',routes={},refusal_fallback=None)
 before=pce_recovery.hashes(dt/'edited');science=(dt/'status.json').read_bytes()
 v=account_release.view(c,PAIR);pd=paper.folder(v,PAIR);d=presentation.folder(v,PAIR)
 original=(d/'pass/paper.tex').read_text()
 def correct(req):
  tex=manuscript(req.prompt)
  change=json.loads((PACK/'proposed-change.json').read_text())
  for item in change:
   assert tex.count(item['before'])==1
   tex=tex.replace(item['before'],item['after'])
  assert 'The audit also distinguishes full-graph prose summary components from saved-figure components.' in tex
  assert not presentation.guard(original,tex,(pd/'paper.tex').read_text(),'')
  assert reason in req.prompt
  assert 'correction refused by the guard: deletes accepted text:' in req.prompt
  if decision=='delete':tex=(d/'correct-2-refused/paper.tex').read_text()
  return '===PAPER===\n'+tex+'\n===REPORT===\n'+json.dumps(dict(changelog=['Define coefficient budgets and statistical summary referents; preserve all limitations.'],title=None,findings=[],escalations=[]))
 action=json.loads((PACK/'action.json').read_text())['prepare_argv'];reason=action[action.index('--reason')+1]
 calls=_script(monkeypatch,{'present/corrector':[correct],'present_check/checker':[check()]})
 args=dict(identity='instruction-contract-copy',context_path=PACK/'context.json',reason=reason)
 assert 'no calls' in account_present.apply(c,PAIR,**args)
 result=account_present.apply(c,PAIR,**args,resume=True)
 assert result==('PAUSE-ON-PRESENT' if decision=='delete' else 'CLEARED')
 assert [(r.stage,r.actor) for r in calls]==([('present','corrector')] if decision=='delete' else [('present','corrector'),('present_check','checker')])
 after=pce_recovery.hashes(dt/'edited')
 mutable={k for k in before if k.endswith('/presentation/state.json') or (k.startswith('publication/') and (k.endswith('/paper.json') or k.endswith('/presentation-continuation.json')))}
 assert all(after[k]==h for k,h in before.items() if k not in mutable)
 assert (dt/'status.json').read_bytes()==science
 if decision=='delete':
  print('Repeated deletion is still refused; prior files preserved',len(before))
  return
 final=(d/'correct-3/paper.tex').read_text()
 for item in reversed(json.loads((PACK/'proposed-change.json').read_text())):
  assert final.count(item['after'])==1
  final=final.replace(item['after'],item['before'])
 assert final==original
 assert presentation.guard(original,original.replace('The audit also distinguishes full-graph prose summary components from saved-figure components.',''),(pd/'paper.tex').read_text(),'')
 build=tmp_path/'build';build.mkdir()
 shutil.copy(d/'correct-3/paper.tex',build/'paper.tex')
 for f in pd.glob('*.bib'):shutil.copy(f,build/f.name)
 ok,log=paper.build(build);assert ok,log
 print('Historical files preserved',len(before),'stub calls',len(calls))
