import json, hashlib
from pathlib import Path
from pathfinder import presentation
ROOT=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2/threads/Q027-P030/edited/publication/67ae68ff643b4f8735346a65826f87d733058822cf4386d6fe00e494dec9676b')
PACK=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-20-residual-notation')
def test_consistent_rename_is_refused():
 d=ROOT/'presentation'
 old=(d/'correct-2/paper.tex').read_text();new=old
 for change in json.loads((PACK/'guard-result.json').read_text())['changes']:
  assert change['before'] in new
  new=new.replace(change['before'],change['after'])
 findings=json.loads((d/'correct-2/check.json').read_text())['findings']
 phrases=[q for f in findings for q in presentation.quoted(f['where'])]
 refused=presentation.guard(old,new,(ROOT/'paper.tex').read_text(),(ROOT/'references.bib').read_text(),phrases)
 assert len(refused)==1 and refused[0].startswith('changes accepted wording: The comparison must assess')
 assert r'-RT\log(K_{D,M}/K_{D,W})' in new
 assert r'\(R+C\)' not in new
 assert json.loads((d/'state.json').read_text())['state']=='PAUSE-ON-PRESENT'
 assert not (d/'amend-findings.json').exists()
 print('Ordinary guard refusal reproduced; PAUSE has no RETURNED amendment precondition; no writes or calls')
