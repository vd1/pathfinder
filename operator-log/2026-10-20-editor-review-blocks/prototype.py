"""Bounded exact substring experiment; only raw earlier files supply references."""
import json
from pathfinder.editor_packet import SPAN_MAGIC,digest,decode_spans

def eligible(name):
 return (name.startswith(('claims/','reviews/','revisions/')) and name.endswith(('.json','.md','.tex'))) or name in ('drafts/current.tex','sources/internal/original.tex','sources/internal/baseline.tex')

def encode(files):
 canonical,bodies,aliases={},{},{}
 for name,text in sorted(files.items()):
  if text in canonical:aliases[name]=canonical[text]
  else:canonical[text]=name;bodies[name]=text
 records,literals,index,roots=[],[],{},{}
 comparisons=probes=indexed=0
 for name,text in bodies.items():
  segments,raw=[],[];cursor=literal_start=0
  if eligible(name) and name != 'drafts/current.tex' and len(text)<=1_000_000:
   while cursor+32<=len(text) and probes<2_000_000 and comparisons<8_000_000 and len(segments)<256:
    probes+=1;best=None
    for source,start in index.get(text[cursor:cursor+32],()):
     base=roots[source];length=32
     while cursor+length<len(text) and start+length<len(base) and comparisons<8_000_000:
      comparisons+=1
      if text[cursor+length]!=base[start+length]:break
      length+=1
     if length>=256 and (best is None or length>best[2]):best=(source,start,length)
    if best:
     if cursor>literal_start:
      value=text[literal_start:cursor];raw.append(value);segments.append({'chars':len(value),'sha256':digest(value)})
     source,start,length=best;segments.append({'copy':source,'start':start,'end':start+length});cursor+=length;literal_start=cursor
    else:cursor+=1
  if literal_start<len(text) or not segments:
   value=text[literal_start:];raw.append(value);segments.append({'chars':len(value),'sha256':digest(value)})
  # An encoded file is a source only when it remains one full raw literal.
  if eligible(name) and len(segments)==1 and 'chars' in segments[0] and len(text)<=1_000_000:
   roots[name]=text
   for pos in range(0,max(0,len(text)-31),32):
    if indexed>=65536:break
    key=text[pos:pos+32];bucket=index.setdefault(key,[])
    if len(bucket)<4:bucket.append((name,pos));indexed+=1
  records.append({'path':name,'chars':len(text),'sha256':digest(text),'segments':segments});literals.extend(raw)
 header={'files':records,'aliases':aliases}
 payload=SPAN_MAGIC+json.dumps(header,ensure_ascii=False,separators=(',',':'))+'\n'+''.join(s+'\n' for s in literals)
 assert decode_spans(payload)==files
 return payload,header,dict(probes=probes,comparisons=comparisons,indexed=indexed)
