import json, shutil
from pathlib import Path
from pathfinder import config, account_release, account_present, pce_recovery, presentation, paper, alerts
from test_presentation import _script, check, manuscript
PACK=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-19-normalisation')
PAIR='Q010-P072'
SRC=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-1')/PAIR

def test_copy(tmp_path,monkeypatch):
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
 sentence=r'For dimensionless normalised operators, $\lambda=0.1$ and quadrature standard error 0.01 give $10^8$ sufficient worst-case shots for one time and geometry.'
 assert original.count(sentence)==1
 additions=[
  ('The quantities are dimensionless oscillator units.', ''),
 ]
 def correct(req):
  tex=manuscript(req.prompt)
  tex=tex.replace(sentence,sentence+' The retained audit does not specify the operator norm or the corresponding normalisation convention; these definitions remain unresolved. The stated count is conditional on the normalised-operator assumption and the independent bounded amplitude measurements, not a calibrated molecular measurement budget.')
  anchor='Synthetic controls illustrate why representation error need not require strong nonlinearity.'
  assert anchor in tex
  definition='\n\nThe retained oscillator has three Cartesian spatial dimensions. The squared quantities $p^2$ and $r^2$ are sums of squared Cartesian momentum and position components. The unperturbed longitudinal mode contributes the same ground energy at both endpoints and cancels in the induction difference, as does a coupling-independent additive energy offset.\n\n'
  tex=tex.replace(anchor,anchor+definition)
  anchor='That figure is not a comparison with Morado'
  assert anchor in tex
  tex=tex.replace(anchor,'PAD denotes the retained classical response comparator using atomic external fields to reproduce reference QM/MM hydration free energies for small molecules. Its acronym expansion is not supplied in the retained description. '+anchor)
  assert sentence in tex
  assert not presentation.guard(original,tex,(pd/'paper.tex').read_text(),'')
  refused=(d/'correct-1-refused/paper.tex').read_text()
  assert any('changes accepted wording' in x for x in presentation.guard(original,refused,(pd/'paper.tex').read_text(),''))
  assert presentation.guard(original,tex.replace('$10^8$ sufficient','$10^9$ sufficient'),(pd/'paper.tex').read_text(),'')
  return '===PAPER===\n'+tex+'\n===REPORT===\n'+json.dumps(dict(changelog=['Add retained definitions and explicit unresolved norm qualification.'],title=None,findings=[],escalations=[]))
 calls=_script(monkeypatch,{'present/corrector':[correct],'present_check/checker':[check()]})
 args=dict(identity='normalisation-copy',context_path=PACK/'context.json',reason='Bounded copied-fixture definition continuation')
 assert 'no calls' in account_present.apply(c,PAIR,**args)
 assert account_present.apply(c,PAIR,**args,resume=True)=='CLEARED'
 assert [(r.stage,r.actor) for r in calls]==[('review','claims'),('present','corrector'),('present_check','checker')]
 after=pce_recovery.hashes(dt/'edited')
 mutable={k for k in before if k.endswith('/presentation/state.json') or (k.startswith('publication/') and (k.endswith('/paper.json') or k.endswith('/presentation-continuation.json')))}
 assert all(after[k]==h for k,h in before.items() if k not in mutable)
 assert (dt/'status.json').read_bytes()==science
 print('Historical files preserved',len(before),'stub calls',len(calls))
