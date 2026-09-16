"""Pass through Codex events and retain complete pilot usage evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


root = Path(__file__).resolve().parent
args = sys.argv[1:]
if not args or args[0] != 'exec':
    raise SystemExit('This wrapper accepts codex exec only.')
model = args[args.index('--model') + 1]
if model != 'gpt-6-astra':
    raise SystemExit(f'Unexpected pilot model: {model}')
cwd = Path(args[args.index('--cd') + 1]).resolve()
if not cwd.is_relative_to(root / 'threads'):
    raise SystemExit(f'Pilot session outside isolated threads: {cwd}')
cmd = ['codex', 'exec', '-c', 'model_reasoning_effort="medium"',
       '-c', 'model_provider="openai"', '-c', 'forced_login_method="chatgpt"',
       *args[1:]]
ident = f'{cwd.name}-{time.time_ns()}-{uuid.uuid4().hex[:8]}'
telemetry = root / 'telemetry'
telemetry.mkdir(exist_ok=True)
started = time.time()
prompt = sys.stdin.buffer.read()
(telemetry / f'{ident}.prompt').write_bytes(prompt)
meta = {'id': ident, 'pair': cwd.name, 'started': started, 'command': cmd,
        'model': model, 'reasoning_effort': 'medium', 'auth': 'chatgpt',
        'service_tier_override': None, 'events_file': f'{ident}.jsonl'}
(telemetry / f'{ident}.meta.json').write_text(json.dumps(meta, indent=2))
with (telemetry / f'{ident}.jsonl').open('w') as events, (telemetry / f'{ident}.stderr').open('w') as errors:
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=errors, text=True)
    proc.stdin.write(prompt.decode())
    proc.stdin.close()
    usages = []
    for line in proc.stdout:
        events.write(line)
        events.flush()
        sys.stdout.write(line)
        sys.stdout.flush()
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get('type') == 'thread.started':
            meta['thread_id'] = event.get('thread_id')
        if event.get('type') == 'turn.completed':
            usages.append(event.get('usage') or {})
    code = proc.wait()
meta.update(exit_code=code, elapsed_seconds=round(time.time() - started, 3), usages=usages)
(telemetry / f'{ident}.meta.json').write_text(json.dumps(meta, indent=2))
sys.exit(code)
