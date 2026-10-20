import importlib.util,json,hashlib
from pathlib import Path
import pytest
from pathfinder import account_successor,account_release,paper,pce,pce_recovery
ROOT=Path('/Users/v/Code_2026/pathfinder')
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def test_twenty_record_parent_refuses_successor_without_writes(tmp_path,monkeypatch):
 c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q010-P030','selector-definitions-20261020','model-decision-1')
 parent=t/'edited/account-amendments/selector-definitions-20261020/revisions/model-decision-1'
 assert len(json.loads((parent/'request.json').read_text())['changes']['changes'])==20
 v=account_release.view(c,'Q010-P030');pd=paper.folder(v,'Q010-P030');source=(parent/'candidate.tex').read_text()
 changes=[]
 # Private contract probe only, not a scientific candidate or proposed live action.
 for ident,anchor in [('P1','The comparison distinguishes original P outputs from the pooling extension.'),('P2','Thus the three fields enter with equal weight;'),('P3','Original endpoint calculations select their spaces independently:')]:
  assert source.count(anchor)==1
  replacement=anchor+'\n% Private contract probe '+ident+'\n';changes.append(dict(finding=ident,before=anchor,after=replacement));source=source.replace(anchor,replacement)
 packet=tmp_path/'packet';packet.mkdir();(packet/'account-candidate.tex').write_text(source)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 (packet/'successor.json').write_text(json.dumps(dict(parent_candidate_sha256=sha(parent/'candidate.tex'),parent_acceptance_sha256=sha(parent/'acceptance.json'),returned_findings_sha256=sha(pd/'presentation/amend-findings.json'),changes=changes)))
 before=pce_recovery.hashes(t)
 with pytest.raises(pce.Changed,match='1-20 explicit replacements'):
  account_successor.run(c,'Q010-P030',identity='pool-component-contract-copy',packet=packet,reason='Private capacity contract probe; no review')
 assert pce_recovery.hashes(t)==before
 print('Canonical accepted-successor refuses 23 cumulative records before writes/calls; parent 20 preserved')
