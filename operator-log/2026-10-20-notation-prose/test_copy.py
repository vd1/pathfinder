import json, shutil, pytest
from pathlib import Path
from pathfinder import config, account_release, account_present, pce_recovery, presentation, paper, alerts, pce
from test_presentation import _script, check, manuscript
PACK=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-20-notation-prose')
PAIR='Q027-P030'
SRC=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2')

@pytest.mark.parametrize('damage',[None,'missing-result','renamed-source','saved-state','provenance'])
def test_copy(tmp_path,monkeypatch,damage):
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
 original=(d/'correct-3/paper.tex').read_text()
 def correct(req):
  tex=manuscript(req.prompt)
  change=json.loads((PACK/'proposed-change.json').read_text())
  assert tex.count(change['before'])==1
  tex=tex.replace(change['before'],change['after'])
  import re
  assert re.findall(r"\\\[(.*?)\\\]",original,re.S)==re.findall(r"\\\[(.*?)\\\]",tex,re.S)
  assert tex==original.replace(change['before'],change['after'])
  assert not presentation.guard(original,tex,(pd/'paper.tex').read_text(),'')
  return '===PAPER===\n'+tex+'\n===REPORT===\n'+json.dumps(dict(changelog=['Remove only the stale explanatory clause.'],title=None,findings=[],escalations=[]))
 calls=_script(monkeypatch,{'present/corrector':[correct],'present_check/checker':[check()]})
 args=dict(identity='notation-prose-copy',context_path=PACK/'context.json',reason='Bounded copied-fixture definition continuation')
 if damage:
  old=pd/'presentation-continuations'/json.loads((pd/'presentation-continuation.json').read_text())['id']
  if damage=='missing-result': (old/'result.json').unlink()
  elif damage=='renamed-source': (d/'correct-3/paper.tex').write_text(original+'\nUnrelated change.')
  elif damage=='saved-state':
   result=json.loads((old/'result.json').read_text());result['presentation']['stage']='correct-9';(old/'result.json').write_text(json.dumps(result))
  else:
   grant=json.loads((old/'grant.json').read_text());grant['request']['context']['review_sha256']='wrong';(old/'grant.json').write_text(json.dumps(grant))
  with pytest.raises(pce.Changed): account_present.apply(c,PAIR,**args)
  assert not calls
  assert not (pd/'presentation-continuations'/'notation-prose-copy').exists()
  return
 assert 'no calls' in account_present.apply(c,PAIR,**args)
 assert account_present.apply(c,PAIR,**args,resume=True)=='CLEARED'
 assert [(r.stage,r.actor) for r in calls]==[('present','corrector'),('present_check','checker')]
 after=pce_recovery.hashes(dt/'edited')
 mutable={k for k in before if k.endswith('/presentation/state.json') or (k.startswith('publication/') and (k.endswith('/paper.json') or k.endswith('/presentation-continuation.json')))}
 assert all(after[k]==h for k,h in before.items() if k not in mutable)
 assert (dt/'status.json').read_bytes()==science
 print('Historical files preserved',len(before),'stub calls',len(calls))
