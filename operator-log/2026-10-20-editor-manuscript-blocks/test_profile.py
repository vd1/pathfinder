"""Offline full actual-report profile; no prior report is reused as live judgement."""
import importlib.util,json
from pathlib import Path
from pathfinder import account_successor,pce,editor_packet,pce_recovery
from test_pce import script
ROOT=Path('/Users/v/Code_2026/pathfinder');PACK=ROOT/'operator-log/2026-10-20-affinity-record-specifications'
spec=importlib.util.spec_from_file_location('helper',ROOT/'operator-log/2026-10-20-final-register/test_copy.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def test_profile(tmp_path,monkeypatch):
 assert Path(pce.__file__).resolve().is_relative_to(ROOT)
 pspec=importlib.util.spec_from_file_location('prototype',Path(__file__).with_name('prototype_editor_packet.py'))
 prototype=importlib.util.module_from_spec(pspec);pspec.loader.exec_module(prototype)
 monkeypatch.setattr(editor_packet,'encode_spans',prototype.encode_spans)
 c,t=helper.copied(tmp_path,monkeypatch,helper.BASE,'Q053-P011','scalar-allowance-definition-20261020')
 parent=t/'edited/account-amendments/scalar-allowance-definition-20261020/review'
 before=pce_recovery.hashes(parent)
 live=helper.BASE/'threads/Q053-P011/edited/account-amendments/scalar-allowance-definition-20261020/review'
 live_before=pce_recovery.hashes(live)
 calls=script(monkeypatch,c);real_alias=pce.editor_alias_packet
 class Measured(Exception):pass
 def measure(head,shown):
  profile=dict(shown);replaced=[]
  for name in shown:
   if name.startswith(('claims/','reviews/','revisions/')):
    src=parent/name
    # Keep successor manuscript; every other actual revision report, including evidence-diff, is measured.
    if name.endswith('.tex'):continue
    assert src.is_file(),name
    profile[name]=src.read_text();replaced.append(name)
  alias,_=real_alias(head,profile);raw,_=editor_packet.packet(head,profile,len(alias));spans,meta=editor_packet.span_packet(head,profile,len(alias),len(raw))
  assert editor_packet.decode_spans(spans.split('Allowed input files:\n',1)[1])==profile
  result=dict(file_frames=meta["file_frames"],prior_span_chars=999726,saved_chars=999726-len(spans),original_chars=len(head+pce._json(profile)),alias_chars=len(alias),raw_chars=len(raw),span_chars=len(spans),cap=1000000,headroom=1000000-len(spans),replaced_profile_paths=replaced,expanded_sha256={k:pce._sha(v) for k,v in profile.items()},purpose='Offline actual scalar full-report profile, including archivist evidence-diff; not successor judgements or a bound on future report length.')
  (ROOT/'operator-log/2026-10-20-editor-manuscript-blocks/measurement.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('expanded_sha256','replaced_profile_paths','file_frames')})
  assert len(spans)==999726
  assert result["saved_chars"]==0
  assert result["headroom"]==274
  raise Measured
 monkeypatch.setattr(pce,'editor_alias_packet',measure)
 import pytest
 with pytest.raises(Measured):account_successor.run(c,'Q053-P011',identity='feature-record-specifications-20261020',packet=PACK/'Q053-P011',reason='Offline sizing only',apply=True)
 assert len(calls)==4
 assert pce_recovery.hashes(parent)==before
 assert pce_recovery.hashes(live)==live_before
 print("Preserved copied parent files",len(before),"and live workflow files",len(live_before))
