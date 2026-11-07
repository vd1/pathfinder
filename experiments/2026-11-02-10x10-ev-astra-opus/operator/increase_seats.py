"""Wait for the authorized graceful drain, then restart the same experiment with four seats."""
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from pathfinder import health
from pathfinder.launch import launch

REASON = 'User-authorized graceful seat increase from 2 to 4; finish active calls before restart'


def main():
    state = ROOT / 'operator/seat-change.json'
    old = json.loads((ROOT / 'runner.json').read_text())
    deadline = time.monotonic() + 7500
    while health.alive(old['pid']):
        state.write_text(json.dumps({'status': 'waiting-for-drain', 'old_pid': old['pid']}))
        if time.monotonic() >= deadline:
            raise RuntimeError('Drain deadline exceeded; no calls cancelled, no configuration changed')
        time.sleep(5)
    if list((ROOT / 'active-calls').glob('*.json')):
        raise RuntimeError('Active-call records remain; manual diagnosis required')
    stopped = json.loads((ROOT / 'runner.json').read_text())
    if stopped['status'] != 'stopped' or stopped['pid'] != old['pid']:
        raise RuntimeError('Unexpected runner state; no configuration changed')
    marker = json.loads((ROOT / 'stop.json').read_text())
    if marker.get('reason') != REASON:
        raise RuntimeError('Stop marker changed; not clearing another operator stop')
    path = ROOT / 'campaign.json'
    before = path.read_bytes()
    raw = json.loads(before)
    previous = json.loads((ROOT / 'run.json').read_text())['config']['raw']
    if raw != previous or raw['seats'] != 2:
        raise RuntimeError('Configuration changed while draining')
    (ROOT / 'operator/campaign-before-four-seats.json').write_bytes(before)
    manifest = ROOT / 'operator/manifest.json'
    (ROOT / 'operator/manifest-before-four-seats.json').write_bytes(manifest.read_bytes())
    raw['seats'] = 4
    temp = path.with_suffix('.json.tmp'); temp.write_text(json.dumps(raw, indent=2) + '\n'); temp.replace(path)
    hashes = json.loads(manifest.read_text())
    for name in ('campaign.json', 'run_experiment.py'):
        hashes[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    manifest.write_text(json.dumps(hashes, indent=2) + '\n')
    (ROOT / 'operator/seat-change-stop.json').write_text(json.dumps(marker, indent=2) + '\n')
    (ROOT / 'stop.json').unlink()
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    log = ROOT / 'operator' / f'four-seats-{stamp}.log'
    argv = [sys.executable, '-u', str(ROOT / 'run_experiment.py'), '--accept-seat-change']
    pid = launch(argv, log, 20, ROOT)
    record = {'pid': pid, 'argv': argv, 'log': str(log), 'started_at': stamp, 'reason': REASON}
    with (ROOT / 'launches.jsonl').open('a') as stream:
        stream.write(json.dumps(record) + '\n')
    (ROOT / 'operator/latest-launch.json').write_text(json.dumps(record, indent=2) + '\n')
    time.sleep(45)
    current = json.loads((ROOT / 'runner.json').read_text())
    if (not health.alive(pid) or current['pid'] != pid or current['status'] != 'running'
            or time.time() - current['heartbeat_at'] > 30):
        raise RuntimeError('Four-seat runner failed its post-launch health check')
    state.write_text(json.dumps({'status': 'running', 'seats': 4, **record,
                                'active_pairs': current['active_pairs']}, indent=2) + '\n')
    print(json.dumps({'status': 'running', 'pid': pid, 'seats': 4, 'active_pairs': current['active_pairs']}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        (ROOT / 'operator/seat-change-error.json').write_text(json.dumps({'error': str(error)}))
        raise
