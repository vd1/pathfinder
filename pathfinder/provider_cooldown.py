"""Cross-process backend/account/model cooldown and exclusive recovery probes."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import time
import uuid
from . import health, seats


class Deferred(Exception):
    pass


def paths(campaign, model):
    spec = seats.account(campaign)
    if not spec:
        return None
    identity = dict(backend=campaign.backend, account=spec['name'], model=model)
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    root = seats.accounts_dir() / 'provider-cooldowns'
    root.mkdir(parents=True, exist_ok=True)
    return root / f'{key}.json', root / f'{key}.lock', root / f'{key}.probe', identity


@contextmanager
def locked(path):
    with path.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def extend(campaign, model, seconds, reason):
    found = paths(campaign, model)
    if found is None:
        return False
    state, lock, _, identity = found
    with locked(lock):
        previous = health.read(state) or {}
        health.write(state, dict(identity=identity, until=max(time.time() + seconds, previous.get('until', 0)),
                                 reason=reason, generation=uuid.uuid4().hex))
    return True


def remaining(campaign, model):
    found = paths(campaign, model)
    if found is None:
        return 0.
    state, lock, _, _ = found
    with locked(lock):
        record = health.read(state) or {}
    return max(0., record.get('until', 0) - time.time())


def check(campaign, model, lease):
    """Recheck after acquiring budgets/seats; never sleep while holding them."""
    found = paths(campaign, model)
    if found is None:
        return
    state, lock, _, _ = found
    with locked(lock):
        record = health.read(state)
        if record and (record['until'] > time.time() or lease.get('generation') != record['generation']):
            raise Deferred()


@contextmanager
def gate(campaign, request, deadline):
    from . import admission, events
    found = paths(campaign, request.model)
    lease = dict(generation=None, successful=False)
    if found is None:
        yield lease
        return
    state, lock, probe, identity = found
    held = None
    announced = False
    try:
        while True:
            reason = admission._stop_marker(campaign)
            if reason:
                admission._refuse(campaign, request.thread, request.stage, request.actor, request.model, reason)
            if time.monotonic() >= deadline:
                admission._refuse(campaign, request.thread, request.stage, request.actor, request.model,
                                  'provider cooldown exceeds bounded retry episode; no call started')
            with locked(lock):
                record = health.read(state)
                if not record:
                    break
                if record['until'] <= time.time():
                    handle = probe.open('a')
                    try:
                        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        handle.close()
                    else:
                        held = handle
                        lease['generation'] = record['generation']
                        break
            if not announced:
                events.emit(campaign, 'admission_deferred', unit=request.thread, stage=request.stage,
                            actor=request.actor, reason='shared provider cooldown', provider_scope=identity)
                announced = True
            time.sleep(min(.5, max(0., deadline - time.monotonic())))
        yield lease
        if lease['successful'] and held is not None:
            with locked(lock):
                record = health.read(state)
                if record and record['generation'] == lease['generation']:
                    state.unlink()
    finally:
        if held is not None:
            held.close()


def snapshot(campaign):
    """Read-only account/model cooldown visibility, including pending recovery probes."""
    spec = seats.account(campaign)
    if not spec:
        return []
    rows = []
    for path in (seats.accounts_dir() / 'provider-cooldowns').glob('*.json'):
        record = health.read(path)
        identity = (record or {}).get('identity', {})
        if identity.get('backend') == campaign.backend and identity.get('account') == spec['name']:
            rows.append(dict(identity=identity, remaining_seconds=max(0., record['until'] - time.time()),
                             recovery_probe_required=True, reason=record.get('reason'), path=str(path)))
    return rows
