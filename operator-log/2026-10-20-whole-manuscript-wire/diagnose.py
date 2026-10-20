from pathlib import Path
import json,hashlib
from pathfinder import pce,config,raw_literals,pce_recovery
HERE=Path(__file__).resolve().parent
base=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2');t=base/'threads/Q053-P011';root=t/'edited/account-amendments/floating-bound-definition-20261020';r=root/'review';c=config.load(base)
grant=json.loads((r/'grant.json').read_text());frozen=json.loads((r/'frozen-inputs.json').read_text());files=dict(frozen)
for folder in ['drafts','claims','reviews','revisions']:
 for f in (r/folder).rglob('*'):
  if f.is_file():files[str(f.relative_to(r))]=f.read_bytes().decode()
head,shown=pce.role_context(c,'fact-checker',['reviews/history/pass-01-fact-check.json','reviews/current/fact-check.json'],files,grant,HISTORY='reviews/history/pass-01-fact-check.json',CURRENT='reviews/current/fact-check.json',FACT_SCHEMA=pce._json(pce.FACT_SCHEMA).strip())
prompt,meta=raw_literals.packet(head,shown,'fact-checker');vis=json.loads((r/'visibility/pass-01-fact-checker.json').read_text())
assert pce._sha(prompt)==vis['prompt_sha256']
assert meta['expanded_files_sha256']==vis['files_sha256']
payload=prompt.split('Allowed input files:\n',1)[1];expanded=raw_literals.decode(payload,vis['files_sha256'],'fact-checker')
assert pce._sha(expanded[pce.DRAFT])=='4ba9ba6677a8058866809531e6f51ad44d30b0dc16587617a3e8c950cd0e2753'
frame=next(x for x in vis['file_frames'] if x['path']==pce.DRAFT);offset=0;cuts=[]
for i,s in enumerate(frame['segments']):
 offset+=s['chars'] if 'literal'in s else s['end']-s['start']
 if s.get('literal') in (15,19,20):cuts.append(dict(literal=s['literal'],end=offset,ending=expanded[pce.DRAFT][offset-100:offset],next_segment=frame['segments'][i+1]))
fact=json.loads((r/'reviews/current/fact-check.json').read_text());weak=[x for x in fact['claims'] if x['status']!='supported']
assert len(weak)==3
result=dict(status='read-only diagnosis; no candidate or grant change',prompt_sha256=vis['prompt_sha256'],payload_sha256=vis['payload_sha256'],candidate_sha256=pce._sha(expanded[pce.DRAFT]),weak=weak,boundaries=cuts,failed_round_sha256=pce_recovery.hashes(r),root_request_sha256=pce._sha((root/'request.json').read_text()),selected_pointer=json.loads((t/'edited/account-amendment.json').read_text()),old_record_count=len(json.loads((root/'request.json').read_text())['changes']['changes']))
(HERE/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
print('Exact prompt and candidate verified; literal cutoffs:',[(x['literal'],x['end'])for x in cuts]);print('Failed files bound:',len(result['failed_round_sha256']))
