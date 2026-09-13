"""Read subscription limits and model capabilities without making a model call."""
import json
import os
import selectors
import signal
import subprocess
import time
from datetime import datetime, timezone


def snapshot():
    env = {k: v for k, v in os.environ.items()
           if not any(s in k for s in ('API_KEY', 'OPENAI_', 'ANTHROPIC_API', 'ELM_'))}
    proc = subprocess.Popen(
        ['codex', 'app-server', '--stdio', '-c', 'model_provider="openai"'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env=env, start_new_session=True)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    pending = bytearray()

    def send(message):
        proc.stdin.write((json.dumps(message) + '\n').encode())
        proc.stdin.flush()

    def rpc(ident, method, params=None):
        message = {'id': ident, 'method': method}
        if params is not None:
            message['params'] = params
        send(message)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            while b'\n' in pending:
                line, _, rest = pending.partition(b'\n')
                pending[:] = rest
                row = json.loads(line)
                if row.get('id') == ident:
                    if 'error' in row:
                        raise RuntimeError(f'{method}: {row["error"]}')
                    return row['result']
            if not selector.select(max(0, deadline - time.monotonic())):
                break
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError(f'app-server closed during {method}')
            pending.extend(chunk)
        raise TimeoutError(method)

    try:
        rpc(1, 'initialize', {'clientInfo': {'name': 'pathfinder_usage_probe', 'version': '0.1.0'},
                              'capabilities': {'experimentalApi': True}})
        send({'method': 'initialized'})
        account = rpc(2, 'account/read', {'refreshToken': False}).get('account') or {}
        limits = rpc(3, 'account/rateLimits/read')
        limits.pop('accountId', None)
        models = rpc(4, 'model/list', {'limit': 100, 'includeHidden': True})
        return {'at': datetime.now(timezone.utc).isoformat(),
                'account': {k: account.get(k) for k in ('type', 'planType')},
                'limits': limits,
                'astra_models': [m for m in models.get('data', []) if m.get('model') == 'gpt-6-astra']}
    finally:
        selector.close()
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
