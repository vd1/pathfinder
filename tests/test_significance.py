import hashlib
import json
import pytest
from pathfinder import significance as s, paper, pce, stub, transport, runner, exhaustion, seats, admission
from stubcampaign import make

RATING = {'strongest_result': 'A bounded specialist contribution.', 'nonobvious': 'somewhat',
          'level': 'journal', 'score': 5, 'reason': 'A useful result with a limited scope.'}


def released(tmp_path):
    c = make(tmp_path)
    pd = paper.folder(c, 'Q1P1');out = pd / 'release/20261019T142530Z';out.mkdir(parents=True)
    files = {'paper-20261019T142530Z.tex': b'Released source with scientific limitations.',
             'paper-20261019T142530Z.pdf': b'pdf fixture', 'references.bib': b''}
    for name, data in files.items(): (out/name).write_bytes(data)
    record = {'tex': list(files)[0], 'pdf': list(files)[1],
              'sha256': {k: hashlib.sha256(v).hexdigest() for k,v in files.items()}}
    for dest in (out/'manifest.json',out.parent/'release.json'):dest.write_text(json.dumps(record))
    paper._set(c,'Q1P1',status='RELEASED',release_manifest='release/20261019T142530Z/manifest.json',
               release_sha256=record['sha256'][record['tex']])
    return c, out


def replies(monkeypatch):
    seen=[]
    def reply(c,req):
        seen.append((c,req))
        assert seats.held(c) if hasattr(seats,'held') else True
        return json.dumps(RATING)
    monkeypatch.setattr(stub,'reply',reply)
    return seen


def test_two_independent_once_only_with_receipts_and_raw_resume(tmp_path,monkeypatch):
    c,out=released(tmp_path);seen=replies(monkeypatch)
    original={p:p.read_bytes() for p in paper.folder(c,'Q1P1').rglob('*') if p.is_file()}
    assert s.run(c,'Q1P1')['status']=='prepared';assert not seen
    result=s.run(c,'Q1P1',apply=True)
    assert result['status']=='complete' and len(seen)==2
    assert [r.model for _,r in seen]==list(s.MODELS.values())
    assert len({r.cwd for _,r in seen})==2
    for routed,req in seen:
        assert not req.tools and not req.search and not req.reads
        assert routed.raw['codex']['reasoning_effort']=='medium'
        assert 'typical solid specialist-journal paper' in req.prompt
        assert 'A bounded specialist contribution.' not in req.prompt
    root=c.thread_dir('Q1P1')/'significance'
    assert len(transport.receipts(c))==2
    assert all(len(json.loads((root/j/'receipts.json').read_text()))==1 for j in s.MODELS)
    (root/'result.json').unlink();(root/'astra/result.json').unlink()
    assert s.run(c,'Q1P1',apply=True)==result and len(seen)==2
    assert all(p.read_bytes()==v for p,v in original.items())


@pytest.mark.parametrize('which',['source','pdf','manifest','status'])
def test_tamper_refused_before_dispatch(tmp_path,monkeypatch,which):
    c,out=released(tmp_path);seen=replies(monkeypatch);s.run(c,'Q1P1')
    if which=='status': paper._set(c,'Q1P1',status='CLEARED')
    else:
        name={'source':'paper-20261019T142530Z.tex','pdf':'paper-20261019T142530Z.pdf','manifest':'manifest.json'}[which]
        (out/name).write_text('{}')
    with pytest.raises(pce.Changed):s.run(c,'Q1P1',apply=True)
    assert not seen


@pytest.mark.parametrize('guard',['stop','budget','provider','admission'])
def test_guards_prevent_calls(tmp_path,monkeypatch,guard):
    c,out=released(tmp_path);seen=replies(monkeypatch)
    if guard=='stop':runner.request_stop(c,'owner stop')
    elif guard=='budget':c.budget_usd=0.01
    elif guard=='provider':monkeypatch.setattr(exhaustion,'active',lambda *_:{'remaining_seconds':60})
    else:monkeypatch.setattr(admission,'_stop_marker',lambda *_:'parent stopped')
    result=s.run(c,'Q1P1',apply=True)
    assert result['status'] in ('stopped','provider_paused','not_dispatched') and not seen
    assert not (c.thread_dir('Q1P1')/'significance/sol/dispatch.json').exists()


def test_shared_pool_is_used(tmp_path,monkeypatch):
    c,out=released(tmp_path);seen=replies(monkeypatch);taken=[]
    monkeypatch.setattr(seats,'account',lambda *_:{'name':'test','seats':6})
    monkeypatch.setattr(seats,'take',lambda *a,**kw:taken.append(kw) or {'token':'x'})
    monkeypatch.setattr(seats,'release',lambda *a,**kw:None)
    s.run(c,'Q1P1',apply=True)
    assert len(taken)==2 and len(seen)==2


def test_crash_does_not_repeat_uncertain_call(tmp_path,monkeypatch):
    c,out=released(tmp_path)
    monkeypatch.setattr(transport,'execute',lambda *a:(_ for _ in ()).throw(RuntimeError('interrupted')))
    with pytest.raises(RuntimeError):s.run(c,'Q1P1',apply=True)
    with pytest.raises(pce.Changed,match='uncertain'):s.run(c,'Q1P1',apply=True)


def test_bad_raw_never_repeated(tmp_path,monkeypatch):
    c,out=released(tmp_path);seen=[]
    monkeypatch.setattr(stub,'reply',lambda c,r:seen.append(r) or 'invalid')
    for _ in range(2):
        with pytest.raises(pce.Changed,match='invalid rating'):s.run(c,'Q1P1',apply=True)
    assert len(seen)==1


def test_fixed_configuration_and_no_fallback(tmp_path):
    c,_=released(tmp_path);c.raw.update(routes={'edit':{'backend':'claude'}},refusal_fallback={'backend':'claude'},
       codex={'config':['features.shell_tool=true'],'persist_sessions':True,'reasoning_effort':'high','base_url':'other'})
    r=s._campaign(c)
    assert r.raw['routes']=={} and r.raw['refusal_fallback'] is None
    assert transport.retry_policy(r)[0]==0 and transport.transient_backoffs(r,None,{})==[]
    r.backend='codex';cmd=transport._command(r,'gpt-6-astra',False,False,c.root)
    assert 'features.shell_tool=false' in cmd and 'web_search="disabled"' in cmd and '--ephemeral' in cmd
    assert 'model_reasoning_effort="medium"' in cmd
    assert 'features.shell_tool=true' not in cmd
    assert c.raw['codex']['persist_sessions']


@pytest.mark.parametrize('change',[{'score':True},{'score':float('nan')},{'score':11},{'level':'great'},{'reason':''}])
def test_schema(change):
    with pytest.raises(pce.Changed):s.parse({'text':json.dumps({**RATING,**change})})


def test_served_failure_has_no_retry_or_fallback(tmp_path,monkeypatch):
    c,_=released(tmp_path);seen=[]
    c.raw['refusal_fallback']={'backend':'claude','model':'claude'}
    def failed(c,r):
        seen.append(r)
        return {'text':'','error':'timeout after service','outcome':'timeout','session':'served','seconds':1}
    monkeypatch.setattr(stub,'execute',failed)
    for _ in range(2):
        with pytest.raises(pce.Changed,match='failed'):s.run(c,'Q1P1',apply=True)
    assert len(seen)==1 and len(transport.receipts(c))==1


def test_new_release_does_not_grant_two_more_calls(tmp_path,monkeypatch):
    c,out=released(tmp_path);seen=replies(monkeypatch);s.run(c,'Q1P1',apply=True)
    manifest=json.loads((out/'manifest.json').read_text())
    source=out/manifest['tex'];source.write_text('A newly revised released source.')
    manifest['sha256'][manifest['tex']]=hashlib.sha256(source.read_bytes()).hexdigest()
    for path in (out/'manifest.json',out.parent/'release.json'):path.write_text(json.dumps(manifest))
    paper._set(c,'Q1P1',release_sha256=manifest['sha256'][manifest['tex']])
    with pytest.raises(pce.Changed):s.run(c,'Q1P1',apply=True)
    assert len(seen)==2
