"""Two independent, once-only significance ratings of an authoritative dated release.

No acceptance or release gate depends on these opinions. Dispatch intent is durable:
uncertain outcomes block replay, while saved raw responses can always be parsed again.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
from . import account_release, admission, exhaustion, health, library, paper, pce, provenance, runner, transport
from .significance_rubric import RUBRIC

MODELS = {'sol': 'gpt-6.1-sol', 'astra': 'gpt-6-astra'}
STAGE = 'significance'
SCHEMA = {'type': 'object', 'additionalProperties': False, 'required':
          ['strongest_result', 'nonobvious', 'level', 'score', 'reason'], 'properties': {
    'strongest_result': {'type': 'string'}, 'reason': {'type': 'string'},
    'nonobvious': {'type': 'string', 'enum': ['no', 'somewhat', 'yes']},
    'level': {'type': 'string', 'enum': ['note', 'journal', 'strong']},
    'score': {'type': 'number', 'minimum': 1, 'maximum': 10}}}


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _file(root, name):
    rel = Path(name)
    path = root / rel
    if (rel.is_absolute() or '..' in rel.parts or not path.resolve().is_relative_to(root.resolve())
            or any((root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts)+1))):
        raise pce.Changed('unsafe released artifact path')
    return path


def binding(campaign, pair, edited):
    c = account_release.view(campaign, pair) if edited else campaign
    pd = paper.folder(c, pair)
    status = paper.status(c, pair)
    if status.get('status') != 'RELEASED':
        raise pce.Changed('significance requires a final RELEASED account or paper')
    manifest = _file(pd, status['release_manifest'])
    raw = manifest.read_bytes()
    record = json.loads(raw)
    if json.loads((pd / 'release/release.json').read_text()) != record:
        raise pce.Changed('release pointer differs from authoritative manifest')
    for name, digest in record['sha256'].items():
        if _hash(_file(manifest.parent, name).read_bytes()) != digest:
            raise pce.Changed('released artifact changed: ' + name)
    source = _file(manifest.parent, record['tex']).read_bytes()
    if _hash(source) != status.get('release_sha256') or record['sha256'].get(record['tex']) != _hash(source):
        raise pce.Changed('released source hash disagrees with release status')
    prompt = RUBRIC.format(paper=source.decode('utf-8'))
    return {'version': 1, 'pair': pair, 'edited': edited,
            'release_manifest': str(manifest.relative_to(campaign.thread_dir(pair))),
            'manifest_sha256': _hash(raw), 'source_sha256': _hash(source),
            'rubric_sha256': _hash(RUBRIC.encode()), 'prompt_sha256': _hash(prompt.encode()),
            'models': MODELS, 'effort': 'medium', 'calls_per_model': 1,
            'tools': False, 'search': False}, prompt, source


def _campaign(campaign):
    c = copy.copy(campaign)
    if c.backend not in ('codex', 'stub'):
        raise pce.Changed('significance requires the OpenAI codex backend')
    if (c.raw.get('extensions') or {}).get('transport'):
        raise pce.Changed('significance cannot use a custom transport dispatcher')
    c.raw = copy.deepcopy(c.raw)
    c.raw.update(routes={}, refusal_fallback=None, unserved_retries=0, transient_backoff_seconds=[])
    # Do not inherit custom providers, persistent sessions, or configuration that can
    # re-enable tools or override the fixed effort. Keep deployment filesystem policy.
    profile = (c.raw.get('codex') or {}).get('filesystem_profile')
    c.raw['codex'] = {'reasoning_effort': 'medium', 'disable_toolless_shell': True, 'search': 'config'}
    if profile:
        c.raw['codex']['filesystem_profile'] = profile
    return c


def parse(raw):
    if raw.get('error') or raw.get('failure') or raw.get('tool_calls'):
        raise pce.Changed('rating call failed; raw and receipt retained, no automatic repeat')
    try:
        value = json.loads(raw['text'])
        score = value.get('score')
        valid = (set(value) == set(SCHEMA['required']) and type(score) in (int, float)
                 and math.isfinite(score) and 1 <= score <= 10
                 and value['level'] in ('note', 'journal', 'strong')
                 and value['nonobvious'] in ('no', 'somewhat', 'yes')
                 and all(isinstance(value[k], str) and value[k].strip() for k in ('reason', 'strongest_result')))
        if not valid:
            raise ValueError('invalid rating schema')
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise pce.Changed('invalid rating response; raw retained, no automatic repeat') from exc
    return value


def run(campaign, pair, *, edited=False, apply=False, accept_change=None):
    c = _campaign(campaign)
    with health.owner(campaign, nested=True), runner.Lock(campaign.thread_dir(pair)):
        bound, prompt, source = binding(campaign, pair, edited)
        # One fixed slot per account, not per release: a new release cannot silently
        # double the owner's two-call allowance. There is deliberately no reset flag.
        root = campaign.thread_dir(pair) / 'significance'
        pce._write(root, 'binding.json', pce._json(bound), immutable=True)
        pce._write(root, 'source.tex', source.decode('utf-8'), immutable=True)
        pce._write(root, 'prompt.txt', prompt, immutable=True)
        if not apply:
            return {'status': 'prepared', 'path': str(root), 'calls': 2}
        with provenance.run_context(campaign, accept_change):
            c.run_id = campaign.run_id
            results = {}
            for judge, model in MODELS.items():
                d = root / judge
                actor = f'significance-{judge}-{bound["source_sha256"][:16]}'
                raw_path = d / 'raw.json'
                if not raw_path.exists():
                    if (d / 'dispatch.json').exists():
                        raise pce.Changed('uncertain rating outcome; inspect dispatch, receipts and active calls; no automatic repeat')
                    if runner.stopped(c) or not runner.guard_ok(c, inflight=1):
                        return {'status': 'stopped', 'completed': list(results)}
                    if exhaustion.active(c.backend):
                        return {'status': 'provider_paused', 'completed': list(results)}
                    work = d / 'work'
                    work.mkdir(parents=True, exist_ok=True)
                    req = transport.request(prompt, model=model, tools=False, search=False, reads=False,
                                            cwd=work, timeout=1800, thread=pair, stage=STAGE, actor=actor, schema=SCHEMA)
                    pce._write(d, 'dispatch.json', pce._json({'binding': bound, 'model': model,
                               'actor': actor, 'run_id': c.run_id,
                               'effective_prompt_sha256': _hash((library.request_rule(c, req) + prompt).encode())}), immutable=True)
                    try:
                        raw = transport.execute(c, req)
                    except (admission.Refused, transport.PromptTooLarge) as exc:
                        # These exceptions prove that no provider call started.
                        pce._write(d, 'not-dispatched.json', pce._json({'reason': str(exc)}))
                        (d / 'dispatch.json').unlink()
                        return {'status': 'not_dispatched', 'reason': str(exc), 'completed': list(results)}
                    pce._write(d, 'raw.json', pce._json(raw), immutable=True)
                raw = json.loads(raw_path.read_text())
                receipts = [r for r in transport.receipts(c) if r.get('thread') == pair
                            and r.get('stage') == STAGE and r.get('actor') == actor]
                pce._write(d, 'receipts.json', pce._json(receipts), immutable=True)
                row = {'judge': judge, 'model': model, 'effort': 'medium', 'source_sha256': bound['source_sha256'],
                       'prompt_sha256': bound['prompt_sha256'], 'raw_sha256': _hash(raw_path.read_bytes()),
                       'rating': parse(raw), 'usage': raw.get('usage')}
                pce._write(d, 'result.json', pce._json(row), immutable=True)
                results[judge] = row
            result = {'status': 'complete', 'binding': bound, 'ratings': results}
            pce._write(root, 'result.json', pce._json(result), immutable=True)
            return result
