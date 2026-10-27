"""Provider-only telemetry. Never infer errors or usage from model/tool prose."""
import hashlib
import json
import math
import os
import threading
import time
from email.utils import parsedate_to_datetime

QUOTA_CODES = {'insufficient_quota', 'credit_balance_exhausted', 'organization_spend_limit_exceeded',
               'project_spend_limit_exceeded', 'organization_usage_limit_exceeded'}


def terminal_result_usage(lines):
    """Claude's final result reports CLI totals even when its answer failed.

    Never promote assistant-message usage, truncated streams or malformed totals.
    Cache fields must be explicit so whole-input accounting cannot undercount.
    """
    last = next((line for line in reversed(lines) if line.strip()), None)
    try:
        event = json.loads(last)
    except (TypeError, ValueError):
        return None
    if not isinstance(event, dict) or event.get('type') != 'result' or type(event.get('is_error')) is not bool:
        return None
    usage = event.get('usage')
    fields = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')
    if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0 for k in fields):
        return None
    return usage


def retry_after(value, now=None):
    if value is None or isinstance(value, bool):
        return None
    now = time.time() if now is None else now
    try:
        seconds = float(value)
    except (ValueError, TypeError):
        try:
            seconds = parsedate_to_datetime(str(value)).timestamp() - now
        except (ValueError, TypeError, OverflowError):
            return None
    return max(0., seconds) if math.isfinite(seconds) else None


def inspect(lines, *, completed=False, now=None):
    errors, samples = [], []
    for index, line in enumerate(lines):
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get('type')
        if kind in ('error', 'turn.failed'):
            detail = event.get('error')
            detail = detail if isinstance(detail, dict) else event
            headers = detail.get('headers', event.get('headers', {}))
            headers = {str(k).lower(): v for k, v in headers.items()} if isinstance(headers, dict) else {}
            status = detail.get('status_code', detail.get('status', event.get('status_code')))
            code = detail.get('code', event.get('code'))
            after = headers.get('retry-after', detail.get('retry_after', event.get('retry_after')))
            errors.append(dict(event_index=index, origin=kind, code=code if isinstance(code, str) else None,
                               type=detail.get('type'), status=status if type(status) is int else None,
                               request_id=detail.get('request_id', headers.get('x-request-id')),
                               retry_after_raw=after, retry_after_seconds=retry_after(after, now)))
        usage, semantics = event.get('usage'), 'provider-reported'
        if kind == 'event_msg' and isinstance(event.get('payload'), dict):
            payload = event['payload']
            if payload.get('type') == 'token_count':
                info = payload.get('info') or {}
                info = info if isinstance(info, dict) else {}
                usage, semantics = info.get('total_token_usage'), 'cumulative-snapshot'
        elif kind == 'token_count':
            info = event.get('info') or {}
            info = info if isinstance(info, dict) else {}
            usage, semantics = info.get('total_token_usage'), 'cumulative-snapshot'
        elif kind == 'assistant':
            usage = (event.get('message') or {}).get('usage')
            semantics = 'message-usage-not-call-total'
        if kind not in ('turn.completed', 'result', 'assistant', 'token_count', 'event_msg'):
            usage = None
        if isinstance(usage, dict):
            samples.append(dict(event_index=index, origin=kind, semantics=semantics, usage=usage))
    # A preceding quota signal must not be weakened by a generic terminal error.
    specific = next((e for e in reversed(errors) if e['code'] or e['status']), errors[-1] if errors else None)
    chosen = next((e for e in reversed(errors) if e['code'] in QUOTA_CODES), specific)
    if chosen:
        chosen = dict(chosen)
        hints = [e['retry_after_seconds'] for e in errors if e['retry_after_seconds'] is not None]
        chosen['retry_after_seconds'] = max(hints) if hints else None
    return dict(provider_error=chosen, provider_errors=errors,
                usage_completeness='complete' if terminal_result_usage(lines) is not None
                or completed and samples and samples[-1]['origin'] in ('turn.completed', 'result')
                else 'partial' if samples else 'unknown', usage_samples=samples)


class Journal:
    """Append and fsync events while the CLI runs; evidence survives a killed controller."""
    def __init__(self, campaign, call_id):
        root = campaign.path('transport-evidence'); root.mkdir(parents=True, exist_ok=True)
        self.paths = {kind: root / f'{call_id}.{kind}' for kind in ('events.jsonl', 'stderr.log')}
        self.handles = {}
        try:
            for kind, path in self.paths.items():
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                self.handles[kind] = os.fdopen(fd, 'w')
        except BaseException:
            self.close()
            raise
        self.error = None
        self.stderr_tail = ''
        self.lock = threading.Lock()

    def append(self, kind, text):
        try:
            with self.lock:
                handle = self.handles[kind]
                handle.write(text); handle.flush(); os.fsync(handle.fileno())
                if kind == 'stderr.log':
                    self.stderr_tail = (self.stderr_tail + text)[-2000:]
        except BaseException as error:
            self.error = repr(error)
            raise

    def close(self):
        for handle in self.handles.values():
            handle.close()

    def manifest(self):
        if self.error:
            raise OSError(f'provider evidence journal failed: {self.error}')
        return {kind: dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           size=path.stat().st_size) for kind, path in self.paths.items()}


def validate_options(raw):
    for key in ('retry_backoff_seconds', 'retry_jitter_fraction', 'retry_episode_seconds'):
        if key not in raw:
            continue
        value = raw[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f'{key} must be finite and nonnegative')
        if key == 'retry_jitter_fraction' and value > 1 or key == 'retry_episode_seconds' and value == 0:
            raise ValueError(f'{key} outside supported range')
    if 'unserved_retries' in raw and (type(raw['unserved_retries']) is not int or raw['unserved_retries'] < 0):
        raise ValueError('unserved_retries must be a nonnegative integer')
    if 'transient_backoff_seconds' in raw:
        waits = raw['transient_backoff_seconds']
        if not isinstance(waits, list) or any(type(w) not in (int, float) or not math.isfinite(w) or w < 0 for w in waits):
            raise ValueError('transient_backoff_seconds must be a list of finite nonnegative delays')
