"""Offline actual-receipt repair and same-grant resume; no real model or live writes."""
from pathlib import Path
import hashlib,json,os,shutil,tempfile
from pathfinder import config,usage_recovery,budget_group,research,transport,cli
pilot=Path('/Users/v/Code_2026/qap-atlas/pilots/atlas-pilot-9')
source=pilot/'runs/pair-3';call='caed1dc5cd774d5b8009d54c42c5e480';pair='Q001-P002'
def sha(p):return 'symlink:'+os.readlink(p) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(root):return {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
before=inventory(source)
root=Path(tempfile.mkdtemp(prefix='atlas-timeout-copy-',dir='/private/tmp'))
shutil.copytree(source,root/'runs/pair-3',symlinks=True)
raw=json.loads((source/'campaign.json').read_text());spec=raw['budget_group']
doc=json.loads(Path(spec['manifest']).read_text());newroots=[]
for old in doc['campaigns']:
    old=Path(old);new=root/'runs'/old.name;newroots.append(str(new))
    if old!=source:
        new.mkdir(parents=True)
        if (old/'receipts.jsonl').exists():shutil.copyfile(old/'receipts.jsonl',new/'receipts.jsonl')
        if (old/'active-calls').exists():shutil.copytree(old/'active-calls',new/'active-calls')
doc['campaigns']=newroots;group=root/'group.json';group.write_text(json.dumps(doc))
raw['budget_group']={'manifest':str(group),'sha256':sha(group)}
# Only offline copies rebase their manifest roots. No live manifest/config is edited.
c=config.campaign_from(root/'runs/pair-3',raw)
assert budget_group.report(c)['refusal'] is not None
plan=usage_recovery.recover(c,call,'Offline proof of final-result accounting')
thread=c.thread_dir(pair);oldstate=(thread/'status.json').read_bytes();oldnote=(thread/f'{pair}.tex').read_bytes()
receipts=c.path('receipts.jsonl').read_bytes();grant=research.status(c,pair)['grant']
usage_recovery.recover(c,call,'Offline proof of final-result accounting',apply=True,expected=plan['sha256'])
assert c.path('receipts.jsonl').read_bytes()==receipts
assert (thread/'status.json').read_bytes()==oldstate and (thread/f'{pair}.tex').read_bytes()==oldnote
report=budget_group.report(c);assert report['refusal'] is None
row=next(r for r in transport.receipts(c) if r['call_id']==call)
assert (row['input_tokens'],row['output_tokens'])==(106235,298) and row['outcome']=='error'
assert research.status(c,pair)['grant']==grant
# Stub only model boundaries. The normal research state machine consumes the existing grant.
calls=[]
def execute(c,r):
    calls.append(r.stage)
    if r.stage=='consolidate':
        assert grant['review']['action'] in r.prompt
        text=oldnote.decode()+'\n% offline fixture only\n'
    elif r.stage=='verify':text='{"decision":"REVISE","reason":"offline sentinel","action":"fixture"}'
    else:raise AssertionError(r.stage)
    return dict(text=text,error=None,transport_failed=False,session='offline',seconds=0)
transport.execute=execute
assert research.run_thread(c,pair)=='PAUSE-ON-REVISE'
assert calls==['consolidate','verify'] and research.status(c,pair)['grant'] is None
assert c.path('receipts.jsonl').read_bytes()==receipts
assert before==inventory(source)
result=dict(engine=str(Path(research.__file__).resolve()),copy=str(root),
            original_files_preserved=len(before),call=call,input_tokens=106235,output_tokens=298,
            unknown_before=True,group_refusal_after=report['refusal'],same_grant=True,
            fixture_stages=calls,real_model_calls=0,bindings=before)
Path(__file__).with_name('copy-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='bindings'},indent=2))
