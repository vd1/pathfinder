import json, shutil
from pathlib import Path
from pathfinder import config, account_release, account_present, pce_recovery, presentation, paper, alerts
from test_presentation import _script, check, manuscript
PACK=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-19-reader-sequence')
PAIR='Q010-P011'
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
 for entry in json.loads((PACK/'q011-context.json').read_text())['contexts']:
  p=dt/entry['source'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copy(st/entry['source'],p)
 c=config.load(dst);c.backend='stub';c.model='stub';c.raw.update(backend='stub',model='stub',routes={},refusal_fallback=None)
 before=pce_recovery.hashes(dt/'edited');science=(dt/'status.json').read_bytes()
 v=account_release.view(c,PAIR);pd=paper.folder(v,PAIR);d=presentation.folder(v,PAIR)
 original=(d/'correct-2/paper.tex').read_text()
 def correct(req):
  tex=manuscript(req.prompt)
  sentence='Their layers contain ZZ and Z cost rotations, X mixer rotations and, for DCQAOA, an additional local Y layer.'
  assert tex.count(sentence)==1
  tex=tex.replace(sentence,sentence+' Here X, Y and Z denote single-qubit Pauli operators; ZZ denotes the product of Z operators on two qubits, which generates the corresponding two-qubit rotation.')
  sentence='On their training set, Morado and colleagues report a hydration root mean square error (RMSE) of 1.63 kcal/mol for patched EMLE, compared with 0.80 kcal/mol for OpenFF/TIP3P.'
  assert tex.count(sentence)==1
  tex=tex.replace(sentence,sentence+' Patching here means fitting EMLE parameters directly to the static and induction energy terms of the reference QM/MM electrostatic interaction. This parameter fitting is distinct from the subsequent empirical attenuation of induction.')
  assert not presentation.guard(original,tex,(pd/'paper.tex').read_text(),'')
  return '===PAPER===\n'+tex+'\n===REPORT===\n'+json.dumps(dict(changelog=['Define Pauli notation at first use and distinguish patch fitting from attenuation.'],title=None,findings=[],escalations=[]))
 calls=_script(monkeypatch,{'present/corrector':[correct],'present_check/checker':[check()]})
 args=dict(identity='pauli-patch-copy',context_path=PACK/'q011-context.json',reason='Bounded copied-fixture definition continuation')
 assert 'no calls' in account_present.apply(c,PAIR,**args)
 assert account_present.apply(c,PAIR,**args,resume=True)=='CLEARED'
 assert [(r.stage,r.actor) for r in calls]==[('present','corrector'),('present_check','checker')]
 after=pce_recovery.hashes(dt/'edited')
 mutable={k for k in before if k.endswith('/presentation/state.json') or (k.startswith('publication/') and (k.endswith('/paper.json') or k.endswith('/presentation-continuation.json')))}
 assert all(after[k]==h for k,h in before.items() if k not in mutable)
 assert (dt/'status.json').read_bytes()==science
 print('Historical files preserved',len(before),'stub calls',len(calls))
