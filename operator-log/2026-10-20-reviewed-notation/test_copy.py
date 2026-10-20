import json, shutil
import pytest
from pathlib import Path
from pathfinder import config, account_release, account_present, pce_recovery, presentation, paper, alerts
from test_presentation import _script, check, manuscript
PACK=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-20-reviewed-notation')
PAIR='Q027-P030'
SRC=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2')

@pytest.mark.parametrize('mode',['clear','unrelated','interrupt','checker-fails'])
def test_copy(tmp_path,monkeypatch,mode):
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
 c=config.load(dst);c.backend='stub';c.model='stub';c.raw.update(backend='stub',model='stub',routes={},refusal_fallback=None)
 before=pce_recovery.hashes(dt/'edited');science=(dt/'status.json').read_bytes()
 v=account_release.view(c,PAIR);pd=paper.folder(v,PAIR);d=presentation.folder(v,PAIR)
 original=(d/'correct-2/paper.tex').read_text()
 def correct(req):
  tex=manuscript(req.prompt)
  assert tex==original
  tex=(PACK/'expected-correction.tex').read_text()
  assert 'exact symbol occurrences' in req.prompt
  if mode=='unrelated':tex=tex.replace('-RT\\log','+RT\\log')
  return '===PAPER===\n'+tex+'\n===REPORT===\n'+json.dumps(dict(changelog=['Consistent reviewed residual alpha-rename; gas constant unchanged.'],title=None,findings=[],escalations=[]))
 calls=_script(monkeypatch,{'present/corrector':[correct],'present_check/checker':[check({'kind':'meaning','where':'Residual','issue':'Synthetic checker concern','fix':'Stop for review'}) if mode=='checker-fails' else check()]})
 args=dict(identity='reviewed-residual-copy',context_path=PACK/'context.json',reason='Bounded copied-fixture definition continuation')
 assert 'no calls' in account_present.apply(c,PAIR,**args)
 if mode=='interrupt':
  real_check=presentation._check;failed=[]
  def interrupted(c,pair,stage,*args):
   if stage=='correct-3' and not failed:
    failed.append(True);raise RuntimeError('host interrupted before fresh check')
   return real_check(c,pair,stage,*args)
  monkeypatch.setattr(presentation,'_check',interrupted)
  with pytest.raises(RuntimeError,match='host interrupted'):
   account_present.apply(c,PAIR,**args,resume=True)
 expected='PAUSE-ON-PRESENT' if mode in ('unrelated','checker-fails') else 'CLEARED'
 assert account_present.apply(c,PAIR,**args,resume=True)==expected
 assert account_present.apply(c,PAIR,**args,resume=True)==expected
 assert [(r.stage,r.actor) for r in calls]==([('present','corrector')] if mode=='unrelated' else [('present','corrector'),('present_check','checker')])
 after=pce_recovery.hashes(dt/'edited')
 mutable={k for k in before if k.endswith('/presentation/state.json') or (k.startswith('publication/') and (k.endswith('/paper.json') or k.endswith('/presentation-continuation.json')))}
 assert all(after[k]==h for k,h in before.items() if k not in mutable)
 assert (dt/'status.json').read_bytes()==science
 if mode=='unrelated':
  assert (d/'correct-3-refused/guard.json').exists()
 else:
  assert (d/'correct-3/paper.tex').read_text()==(PACK/'expected-correction.tex').read_text()
  assert (d/'correct-3/references.bib').read_bytes()==(pd/'references.bib').read_bytes()
 print('Historical files preserved',len(before),'stub calls',len(calls))
