"""Cross-frozen-engine coordinator drain/resume proof using local provider fixtures only."""
from pathlib import Path
import json,sys,hashlib
sys.path.insert(0,'/Users/v/Code_2026/pathfinder/tests')
from stubcampaign import make
from pathfinder import coordinator,config,runner,stub,transport,cli
root=Path(sys.argv[1]);phase=sys.argv[2];mode=sys.argv[3]
path=root/'schedule.json'
if phase=='old':
    for i in range(1,7):
        make(root/'runs'/f'pair-{i}',parent='../..',rounds=6,repairs=2)
    path.write_text(json.dumps({'arms':{f'pair-{i}':f'runs/pair-{i}' for i in range(1,7)},'stages':['research'],
                              'schedule':[{'arm':f'pair-{i}','pair':'Q1P1'} for i in range(1,7)]}))
    original=stub.reply;stopped=[]
    def reply(c,r):
        if mode=='peer-unready' and r.stage=='peer':
            from pathfinder.ledger import Ledger
            Ledger(c.thread_dir('Q1P1')/'ledger.jsonl').add('ada','idea','incomplete work')
            text='continuing; not ready'
        else:
            text=original(c,r)
        if not stopped and r.stage==mode.split('-')[0]:
            stopped.append(True);runner.request_stop(c,'operator engine migration drain')
        return text
    stub.reply=reply
    state=coordinator.run(path,interval=.01,heartbeat=.01)
    assert state['status']=='stopped'
    first=config.load(root/'runs/pair-1')
    receipt_bytes=first.path('receipts.jsonl').read_bytes()
    (root/'before-receipts').write_bytes(receipt_bytes)
    saved={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in root.rglob('*') if p.is_file() and p.name!='pathfinder-meta.tex' and (p.name=='campaign.json' or p.suffix=='.tex' or p.name=='ledger.jsonl' or p.name.endswith('.verdict.json') or p.parent.name=='consolidation')}
    (root/'before-files.json').write_text(json.dumps(saved))
    assert len(transport.receipts(first))=={'peer':1,'peer-unready':1,'consolidate':2,'verify':3}[mode]
    assert all(not config.load(root/'runs'/f'pair-{i}').path('receipts.jsonl').exists() for i in range(2,7))
else:
    if mode=='peer-unready':
        from pathfinder import research
        c=config.load(root/'runs/pair-1')
        assert research.status(c,'Q1P1')['stage']=='peers'
        assert len(transport.receipts(c))==1
        assert 'peer_call' not in research.status(c,'Q1P1')
        print(json.dumps({'mode':mode,'status':'hold: partial classic peer allowance not persisted','real_model_calls':0}))
        raise SystemExit(0)
    before=json.loads((root/'before-files.json').read_text())
    assert cli.main(['--root',str(root/'runs/pair-1'),'stop','--clear']) in (None,0)
    c=config.load(root/'runs/pair-1');calls=[];real=transport.execute
    def execute(c,r):
        calls.append((c.root.name,r.stage));return real(c,r)
    transport.execute=execute
    state=coordinator.run(path,interval=.01,heartbeat=.01,accept_change='Test verified engine migration; unchanged configuration and prompts')
    assert state['status']=='complete'
    wanted={'peer':['consolidate','verify'],'consolidate':['verify'],'verify':[]}[mode]
    assert [stage for name,stage in calls if name=='pair-1']==wanted
    assert c.path('receipts.jsonl').read_bytes().startswith((root/'before-receipts').read_bytes())
    assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in before.items())
    assert all(len(transport.receipts(config.load(root/'runs'/f'pair-{i}')))==3 for i in range(1,7))
    assert len({r['call_id'] for i in range(1,7) for r in transport.receipts(config.load(root/'runs'/f'pair-{i}'))})==18
    final=coordinator.run(path,interval=.01,heartbeat=.01,accept_change='same runtime')
    assert final['status']=='complete' and len(calls)==len(wanted)+15
    print(json.dumps({'mode':mode,'status':'passed','receipt_prefix_preserved':True,'prior_files_preserved':len(before),'total_calls':18,'replayed_calls':0,'real_model_calls':0}))
