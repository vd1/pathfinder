import json
import time
import threading
from email.utils import formatdate
import pytest
from pathfinder import provider_evidence as pe, provider_cooldown as pc, failures, transport, admission
from stubcampaign import make


def lines(*events):
    return [json.dumps(e) for e in events]


def test_structured_quota_precedes_generic_terminal_and_no_prose_inference():
    events = lines(dict(type='error', error=dict(code='project_spend_limit_exceeded', status_code=429)),
                   dict(type='turn.failed', error=dict(message='at capacity')),
                   dict(type='item.completed', item=dict(type='agent_message', text='503 server_is_overloaded')))
    info = pe.inspect(events)
    f = failures.classify('error', 'at capacity', provider=info['provider_error'])
    assert f.cls == 'quota' and not f.retry
    assert pe.inspect(events[-1:])['provider_error'] is None
    assert failures.classify('completed', None, provider=info['provider_error']) is None


def test_retry_after_date_seconds_and_specific_error_survives_terminal():
    now = 1000000000
    events = lines(dict(type='error', error=dict(code='server_is_overloaded', status_code=503,
                    headers={'Retry-After': formatdate(now + 120, usegmt=True), 'X-Request-ID': 'req'})),
                   dict(type='turn.failed', error=dict(message='service unavailable')))
    info = pe.inspect(events, now=now)['provider_error']
    assert info['retry_after_seconds'] == 120 and info['status'] == 503 and info['request_id'] == 'req'
    assert pe.retry_after('30', now) == 30
    for value in ('garbage', 'nan', 'inf', True):
        assert pe.retry_after(value, now) is None
    assert pe.retry_after(formatdate(now - 5, usegmt=True), now) == 0


def test_usage_samples_not_summed_or_promoted_and_reset_preserved():
    events = lines(*[dict(type='event_msg', payload=dict(type='token_count', info=dict(
        total_token_usage=dict(input_tokens=n, output_tokens=2)))) for n in (10, 20, 20, 5)],
        dict(type='turn.failed', error=dict(message='capacity')))
    info = pe.inspect(events)
    assert info['usage_completeness'] == 'partial'
    assert [s['usage']['input_tokens'] for s in info['usage_samples']] == [10, 20, 20, 5]
    assert pe.inspect([], completed=False)['usage_completeness'] == 'unknown'
    events += lines(dict(type='turn.completed', usage=dict(input_tokens=30, output_tokens=5)))
    assert pe.inspect(events, completed=True)['usage_completeness'] == 'complete'


def test_journal_append_is_durable_and_private(tmp_path):
    c = make(tmp_path)
    j = pe.Journal(c, 'one')
    j.append('events.jsonl', '{"type":"turn.started"}\n')
    assert j.paths['events.jsonl'].read_text() == '{"type":"turn.started"}\n'
    assert j.paths['events.jsonl'].stat().st_mode & 0o777 == 0o600
    j.append('stderr.log', 'x' * 10000)
    assert len(j.stderr_tail) == 2000
    j.close()
    assert j.manifest()['stderr.log']['size'] == 10000
    with pytest.raises(FileExistsError):
        pe.Journal(c, 'one')


def test_retry_jitter_respects_hint_and_episode_stops_before_retry(tmp_path, monkeypatch):
    c = make(tmp_path, retry_episode_seconds=2, transient_backoff_seconds=[60], retry_backoff_seconds=0)
    result = dict(outcome='error', failure=dict(scope='call', retry=True, **{'class':'rate'}),
                  session='served', provider_error={'retry_after_seconds': 100}, error='capacity')
    monkeypatch.setattr(transport, '_attempt', lambda *args: result)
    monkeypatch.setattr(transport, '_wait', lambda *args: pytest.fail('must not wait beyond episode'))
    assert transport._retry_delay(c, 60, result) == 100
    request = transport.request('p', model='stub', tools=False, search=False, cwd=c.root,
                                timeout=5, thread='Q1P1', stage='verify', actor='verifier')
    assert transport.execute(c, request) == result
    assert 'retry_deferred' in c.path('events.jsonl').read_text()
    for _ in range(30):
        assert 30 <= transport._retry_delay(c, 60, {}) <= 60


def pair(tmp_path, monkeypatch):
    monkeypatch.setenv('PATHFINDER_ACCOUNTS', str(tmp_path / 'accounts'))
    a, b = [make(tmp_path / n, account=dict(name='shared', seats=2)) for n in ('a', 'b')]
    return a, b


def req(c, model='stub'):
    return transport.request('p', model=model, tools=False, search=False, cwd=c.root,
                             timeout=1, thread='Q1P1', stage='verify', actor='verifier')


def test_shared_scope_max_expiry_and_stale_success_does_not_clear(tmp_path, monkeypatch):
    a, b = pair(tmp_path, monkeypatch)
    pc.extend(a, 'stub', 1, 'first')
    pc.extend(b, 'stub', .01, 'second')
    assert pc.remaining(b, 'stub') > .8
    assert pc.remaining(b, 'other-model') == 0
    b.raw['account']['name'] = 'other-account'
    assert pc.remaining(b, 'stub') == 0
    b.raw['account']['name'] = 'shared'
    # Expire without waiting; this is a synthetic state in a test-owned directory.
    state = pc.paths(a, 'stub')[0]
    doc = json.loads(state.read_text()); doc['until'] = 0; state.write_text(json.dumps(doc))
    with pc.gate(a, req(a), time.monotonic() + 2) as lease:
        pc.check(a, 'stub', lease)
        pc.extend(b, 'stub', 1, 'new failure while probe waited')
        with pytest.raises(pc.Deferred):
            pc.check(a, 'stub', lease)
        lease['successful'] = True
    assert pc.remaining(a, 'stub') > .8


def test_single_probe_and_stop_without_seat_or_budget_lease(tmp_path, monkeypatch):
    a, b = pair(tmp_path, monkeypatch)
    pc.extend(a, 'stub', 0, 'test')
    entered = threading.Event(); done = threading.Event(); errors = []
    def contender():
        try:
            with pc.gate(b, req(b), time.monotonic() + 3):
                entered.set()
        except admission.Refused as e:
            errors.append(e)
        finally:
            done.set()
    with pc.gate(a, req(a), time.monotonic() + 3) as lease:
        t = threading.Thread(target=contender); t.start()
        assert not entered.wait(.1)
        assert admission.reserved(b) == 0
        b.path('stop.json').write_text('{"reason":"operator stop"}')
        assert done.wait(2)
        lease['successful'] = True
    t.join()
    assert errors and not pc.paths(a, 'stub')[0].exists()


def test_failed_probe_releases_lease_for_later_recovery(tmp_path, monkeypatch):
    a, b = pair(tmp_path, monkeypatch)
    pc.extend(a, 'stub', 0, 'test')
    with pytest.raises(RuntimeError):
        with pc.gate(a, req(a), time.monotonic() + 1):
            raise RuntimeError('test failure')
    with pc.gate(b, req(b), time.monotonic() + 1) as lease:
        assert lease['generation']
        lease['successful'] = True
    assert not pc.paths(a, 'stub')[0].exists()


def _extend_worker(c, delay):
    pc.extend(c, 'stub', delay, 'process')


def test_independent_process_updates_keep_maximum_expiry(tmp_path, monkeypatch):
    import multiprocessing
    a, b = pair(tmp_path, monkeypatch)
    ctx = multiprocessing.get_context('fork')
    jobs = [ctx.Process(target=_extend_worker, args=(c, seconds)) for c, seconds in ((a, 10), (b, 1))]
    for job in jobs:
        job.start()
    for job in jobs:
        job.join(3)
        assert job.exitcode == 0
    assert pc.remaining(a, 'stub') > 8
    assert pc.snapshot(b)[0]['identity']['model'] == 'stub'


def test_real_cli_large_stderr_partial_tokens_and_structured_error(tmp_path, monkeypatch):
    import sys
    import hashlib
    script = tmp_path / 'fake_capacity.py'
    script.write_text('''import sys,json,os
sys.stdin.read()
print(json.dumps({'type':'thread.started','thread_id':'test'}),flush=True)
os.write(2,b'x'*300000)
print(json.dumps({'type':'token_count','info':{'total_token_usage':{'input_tokens':10,'output_tokens':2}}}),flush=True)
print(json.dumps({'type':'turn.failed','error':{'message':'busy','code':'server_is_overloaded','status_code':503,'headers':{'Retry-After':'0','x-request-id':'test-request'}}}),flush=True)
sys.exit(1)
''')
    monkeypatch.setenv('PATHFINDER_CODEX', f'{sys.executable} {script}')
    c = make(tmp_path / 'campaign', backend='codex', model='test', transient_backoff_seconds=[],
             unserved_retries=0, retry_backoff_seconds=0)
    result = transport.execute(c, req(c, 'test'))
    assert result['failure']['class'] == 'rate'
    assert result['provider_error']['code'] == 'server_is_overloaded'
    assert result['usage_completeness'] == 'partial'
    assert result['input_tokens'] is None and result['output_tokens'] is None
    row = transport.receipts(c)[0]
    for record in row['evidence_journal'].values():
        from pathlib import Path
        data = Path(record['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == record['sha256']
    assert row['evidence_journal']['stderr.log']['size'] == 300000
    assert row['usage_samples'][0]['usage']['input_tokens'] == 10


@pytest.mark.parametrize('options', [dict(retry_jitter_fraction=2), dict(retry_episode_seconds=0),
    dict(transient_backoff_seconds=[float('nan')]), dict(unserved_retries=-1), dict(retry_backoff_seconds=True)])
def test_invalid_retry_options_refused_before_launch(tmp_path, options):
    with pytest.raises(ValueError):
        make(tmp_path, **options)


def test_episode_caps_attempt_timeout_without_changing_model(tmp_path, monkeypatch):
    c = make(tmp_path, retry_episode_seconds=2)
    seen = []
    monkeypatch.setattr(transport, '_attempt', lambda campaign, request:
                        seen.append(request) or dict(outcome='completed', failure=None))
    request = transport.request('p', model='stub', tools=False, search=False, cwd=c.root,
                                timeout=300, thread='Q1P1', stage='verify', actor='verifier')
    transport.execute(c, request)
    assert len(seen) == 1 and seen[0].timeout <= 2 and seen[0].model == 'stub'


def test_failed_event_journal_retains_unresolved_active_call(tmp_path, monkeypatch):
    import sys
    from pathlib import Path
    fake = Path(__file__).parent / 'fake_cli.py'
    monkeypatch.setenv('PATHFINDER_CODEX', f'{sys.executable} {fake}')
    monkeypatch.setenv('FAKE_MODE', 'codex')
    c = make(tmp_path / 'campaign', backend='codex', model='test', transient_backoff_seconds=[], unserved_retries=0)
    def failed(*args):
        raise OSError('simulated full evidence disk')
    monkeypatch.setattr(pe.Journal, 'append', failed)
    with pytest.raises(OSError, match='journal failed'):
        transport.execute(c, req(c, 'test'))
    assert list(c.path('active-calls').glob('*.json'))
    assert not transport.receipts(c)
