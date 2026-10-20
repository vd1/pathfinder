"""Offline diagnostic only. Not imported by Pathfinder production code."""
import hashlib
import json

MAGIC='PATHFINDER-RAW-LITERALS-PROTOTYPE-V1\n'
ANCHOR=32
MIN_COPY=256
CHUNK=4096
MAX_INDEX=65536
MAX_BUCKET=4
MAX_PROBES=2000000
MAX_COMPARISONS=8000000
MAX_SEGMENTS=8192
MAX_TOTAL=20000000

def sha(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def strict(s):
    def pairs(rows):
        d={}
        for k,v in rows:
            if k in d:raise ValueError('duplicate key')
            d[k]=v
        return d
    return json.loads(s,object_pairs_hook=pairs)

def decode(payload):
    if not payload.startswith(MAGIC):raise ValueError('magic')
    line,sep,body=payload[len(MAGIC):].partition('\n')
    if not sep:raise ValueError('header')
    h=strict(line)
    if set(h)!= {'files','aliases'}:raise ValueError('schema')
    roots={};files={};offset=0;total=0;segments=0
    for r in h['files']:
        if set(r)!= {'path','chars','sha256','segments'}:raise ValueError('file schema')
        if not isinstance(r['path'],str) or r['path'] in files:raise ValueError('path')
        if type(r['chars']) is not int or not 0<=r['chars']<=MAX_TOTAL:raise ValueError('size')
        parts=[]
        for s in r['segments']:
            segments+=1
            if segments>MAX_SEGMENTS+len(h['files']):raise ValueError('segments')
            if set(s)=={'literal','chars','sha256'}:
                n=s['chars'];i=s['literal']
                if type(i)is not int or i!=len(roots) or type(n)is not int or n<0:raise ValueError('literal')
                text=body[offset:offset+n]
                if len(text)!=n or body[offset+n:offset+n+1]!='\n' or sha(text)!=s['sha256']:raise ValueError('literal body')
                offset+=n+1;roots[i]=text;parts.append(text)
            elif set(s)=={'copy','start','end'}:
                i,a,b=s['copy'],s['start'],s['end']
                if type(i)is not int or i not in roots or type(a)is not int or type(b)is not int or not 0<=a<b<=len(roots[i]):raise ValueError('backward literal range')
                parts.append(roots[i][a:b])
            else:raise ValueError('segment schema')
        text=''.join(parts);total+=len(text)
        if total>MAX_TOTAL or len(text)!=r['chars'] or sha(text)!=r['sha256']:raise ValueError('file hash/size')
        files[r['path']]=text
    if offset!=len(body):raise ValueError('trailing')
    result=dict(files)
    for path,source in h['aliases'].items():
        if not isinstance(path,str) or path in result or source not in files:raise ValueError('alias')
        result[path]=files[source]
    return result

def encode(files):
    roots=[];index={};records=[];raw=[];canonical={};aliases={}
    stats=dict(probes=0,comparisons=0,indexed=0,segments=0,copied_chars=0,literal_chars=0)
    def literal(text,segs):
        i=len(roots);roots.append(text);raw.append(text)
        segs.append(dict(literal=i,chars=len(text),sha256=sha(text)));stats['segments']+=1;stats['literal_chars']+=len(text)
        for pos in range(0,max(0,len(text)-ANCHOR+1),ANCHOR):
            if stats['indexed']>=MAX_INDEX:break
            key=text[pos:pos+ANCHOR];bucket=index.setdefault(key,[])
            if len(bucket)<MAX_BUCKET:bucket.append((i,pos));stats['indexed']+=1
    for name,text in sorted(files.items()):
        if text in canonical:aliases[name]=canonical[text];continue
        canonical[text]=name;segs=[];cursor=start=0
        while cursor+ANCHOR<=len(text) and stats['probes']<MAX_PROBES and stats['comparisons']<MAX_COMPARISONS and stats['segments']<MAX_SEGMENTS-2:
            if cursor-start>=CHUNK:literal(text[start:cursor],segs);start=cursor
            stats['probes']+=1;best=None
            for i,a in index.get(text[cursor:cursor+ANCHOR],()):
                base=roots[i];n=ANCHOR
                while cursor+n<len(text) and a+n<len(base) and stats['comparisons']<MAX_COMPARISONS:
                    stats['comparisons']+=1
                    if text[cursor+n]!=base[a+n]:break
                    n+=1
                if n>=MIN_COPY and (best is None or n>best[2]):best=(i,a,n)
            if best:
                if start<cursor:literal(text[start:cursor],segs)
                i,a,n=best;segs.append(dict(copy=i,start=a,end=a+n));stats['segments']+=1;stats['copied_chars']+=n;cursor+=n;start=cursor
            else:cursor+=1
        if start<len(text) or not segs:literal(text[start:],segs)
        records.append(dict(path=name,chars=len(text),sha256=sha(text),segments=segs))
    h=dict(files=records,aliases=aliases)
    payload=MAGIC+json.dumps(h,ensure_ascii=False,separators=(',',':'))+'\n'+''.join(s+'\n' for s in raw)
    assert decode(payload)==files
    return payload,h,stats
