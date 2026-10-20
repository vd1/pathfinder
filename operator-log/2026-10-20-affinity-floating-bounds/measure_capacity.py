from pathlib import Path
from types import SimpleNamespace
import json,time
from pathfinder import pce,config,resources,library,account_register,editor_packet,editor_blocks
base=Path('/Users/v/Code_2026/pathfinder-julien-2/campaign-2-batch-2');t=base/'threads/Q053-P011';parent=t/'edited/account-amendments/feature-record-specifications-20261020';review=parent/'review';pack=Path('/Users/v/Code_2026/pathfinder/operator-log/2026-10-20-affinity-floating-bounds/Q053-P011');c=config.load(base);delta=json.loads((pack/'successor.json').read_text());candidate=(pack/'account-candidate.tex').read_text();files=json.loads((review/'frozen-inputs.json').read_text());old=files[pce.BASELINE];files[pce.BASELINE]=candidate;files['sources/internal/original.tex']=old
additions={r['path']:(t/r['path']).read_bytes().decode() for r in delta['evidence_projection']['include']};files[pce.SUPPLEMENT]+='\n\n## Additional retained scientific files\n\n'+pce._json(additions)
files['sources/internal/changes.json']=pce._json(dict(baseline_sha256=pce._sha(old),candidate_sha256=pce._sha(candidate),changes=delta['changes']))
prep=len(pce._json(files));history=json.loads((review/'replacement-history.json').read_text());register=account_register.build(history['baseline'],history['changes']+delta['changes'],candidate);files['sources/internal/changes.json']=pce._json({'changes':[{'finding':r['finding'],'after':r['claim']} for r in register['records'] if r['claim'].strip()]})
actual=json.loads((review/'visibility/pass-01-editor.json').read_text());shown={}
for name in actual['files_sha256']:
 if name in files:shown[name]=files[name]
 elif name.endswith('.tex'):shown[name]=candidate
 else:shown[name]=(review/name).read_bytes().decode()
contract=resources.prompt(c,'pce-editor',FEEDBACK='reviews/editor-feedback.md');head=contract.rstrip()+pce.TRANSPORT+'Permitted outputs: '+json.dumps(['reviews/editor-feedback.md'])+'\nAllowed input files:\n';head=library.request_rule(c,SimpleNamespace(prompt=head,tools=False,reads=False))+head
alias,_=pce.editor_alias_packet(head,shown);raw,_=editor_packet.packet(head,shown,len(alias));oldspan,_=editor_packet.span_packet(head,shown,len(alias),len(raw))
old=editor_blocks._eligible
editor_blocks._eligible=lambda name: old(name) or name=='sources/internal/changes.json'
start=time.perf_counter();payload,header,stats=editor_blocks.encode(shown);seconds=time.perf_counter()-start
spans,meta=editor_packet.span_packet(head,shown,len(alias),len(raw));assert editor_packet.decode_spans(spans.split('Allowed input files:\n',1)[1])==shown
prepwire,pmeta=editor_packet.packet('',files,len(pce._json(files)));assert editor_packet.decode(prepwire[prepwire.index(editor_packet.MAGIC):])==files
result={'purpose':'OFFLINE PROTOTYPE ONLY; no production encoder/preparation change','old_editor_span_chars':len(oldspan),'new_editor_span_chars':len(spans),'saved':len(oldspan)-len(spans),'headroom':1000000-len(spans),'stats':stats,'seconds':seconds,'pre_register_json_chars':prep,'final_register_json_chars':len(pce._json(files)),'final_register_raw_wire_chars':len(prepwire),'raw_wire_plus_unchanged_reserve':len(prepwire)+100000,'cap':1000000,'reserve':100000,'changes_file_chars':len(shown['sources/internal/changes.json']),'expanded_sha256':{k:pce._sha(v) for k,v in shown.items()}}
(pack.parent/'capacity-prototype.json').write_text(pce._json(result));Path('/private/tmp/affinity-complete-profile.json').write_text(json.dumps({'head':head,'shown':shown,'files':files}));print({k:v for k,v in result.items() if k!='expanded_sha256'})
