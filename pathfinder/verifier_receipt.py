"""Narrow, no-call recovery of a verdict erased by an empty trailing Codex event."""
import json
from . import contracts, pce, research, transport


def inspect(campaign, pair, call_id):
    rows = [r for r in transport.receipts(campaign)
            if r.get('thread') == pair and r.get('stage') == 'verify']
    selected = [i for i, r in enumerate(rows) if r.get('call_id') == call_id]
    if len(selected) != 1 or selected[0] != len(rows) - 2:
        raise pce.Changed('restore requires the penultimate verifier and its final empty-reply repair')
    original, repair = rows[-2:]
    for r in (original, repair):
        if r.get('backend') != 'codex' or r.get('outcome') != 'completed' or r.get('error') or r.get('failure'):
            raise pce.Changed('restore requires two completed error-free Codex receipts')
    if not original.get('run_id') or original['run_id'] != repair.get('run_id'):
        raise pce.Changed('verifier and repair belong to different runs')
    messages = []
    for line in original.get('raw_events', []):
        row = json.loads(line)
        item = row.get('item') or {}
        if row.get('type') == 'item.completed' and item.get('type') == 'agent_message':
            messages.append(item.get('text', ''))
    if len(messages) < 2 or not isinstance(messages[-1], str) or messages[-1].strip():
        raise pce.Changed('receipt has no empty trailing agent message')
    text = transport._parse(campaign, original['model'], original['raw_events'])[0]
    verdict = contracts.parse('verify', text)
    repaired = contracts.parse('verify', transport._parse(campaign, repair['model'], repair['raw_events'])[0])
    if repaired.get('decision') != 'PAUSE' or 'previous reply is empty' not in (repaired.get('reason') or '').lower():
        raise pce.Changed('final repair is not the recognised empty-reply PAUSE')
    d = campaign.thread_dir(pair)
    history = json.loads((d / f'{pair}.verdict.json').read_text())
    state = research.status(campaign, pair)
    if (not history or state.get('status') != 'PAUSE' or state.get('stage') != 'done'
            or history[-1].get('round') != state.get('round')
            or history[-1].get('at') != repair.get('at')
            or any(history[-1].get(k) != v for k, v in repaired.items())
            or history[-1].get('note_sha256') != pce._sha((d / f'{pair}.tex').read_bytes().decode('utf-8'))):
        raise pce.Changed('current note/history does not bind the empty-reply repair')
    return {'policy': 'codex-empty-tail-v1', 'original_receipt': original, 'repair_receipt': repair,
            'text': text, 'verdict': verdict, 'superseded_history_entry': history[-1]}
