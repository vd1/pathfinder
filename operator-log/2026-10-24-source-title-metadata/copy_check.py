"""Offline metadata/build and canonical archive checks; no provider calls."""
from pathlib import Path
import hashlib
import json
import shutil
import tempfile
from pathfinder import config, paper, presentation, thread

SOURCE = Path('/Users/v/Code_2026/nobel/pilot-question/production-strong')
PAIR = 'Q135-P500'
original = SOURCE / 'threads' / PAIR
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = {str(p.relative_to(original)): sha(p) for p in original.rglob('*') if p.is_file()}
root = Path(tempfile.mkdtemp(prefix='nobel-title-copy-', dir='/private/tmp'))
shutil.copytree(original, root / 'threads' / PAIR)
shutil.copy2(SOURCE / 'campaign.json', root / 'campaign.json')
if (SOURCE / 'prompts').is_dir():
    shutil.copytree(SOURCE / 'prompts', root / 'prompts')
c = config.campaign_from(root, json.loads((root / 'campaign.json').read_text()))
d = c.thread_dir(PAIR); pd = d / 'paper'; failed = pd / 'presentation'
old = {str(p.relative_to(failed)): p.read_bytes() for p in failed.rglob('*') if p.is_file()}
accepted = {p: p.read_bytes() for p in pd.iterdir() if p.is_file()}
# Build from a separate copy before and after regenerating only the source header.
control = root / 'build-control'; shutil.copytree(failed / 'pass', control)
old_meta = (control / 'pathfinder-meta.tex').read_bytes()
assert not paper.build(control)[0], 'original failure did not reproduce'
thread.refresh_source_titles(c, PAIR, control)
ok, log = paper.build(control)
assert ok, log
new_meta = (control / 'pathfinder-meta.tex').read_bytes()
assert [x for x in old_meta.splitlines() if not x.startswith(b'\\pathfinderpapers')] == [x for x in new_meta.splitlines() if not x.startswith(b'\\pathfinderpapers')]
assert (control / 'paper.tex').read_bytes() == old['pass/paper.tex']
assert (control / 'references.bib').read_bytes() == old['pass/references.bib']
# Exercise normal blocked presentation recovery; stub only the editor response.
calls = []
def offline_call(campaign, pair_id, stage, actor, prompt, **kwargs):
    assert actor == 'editor' and stage == 'present'
    calls.append((stage, actor))
    return {'text': old['pass/reply.md'].decode(), 'transport_failed': False}, {}
class CheckerReached(Exception):
    pass
def checker(*args, **kwargs):
    assert (failed / 'pass/paper.pdf').is_file()
    raise CheckerReached('fresh independent checker required; no scientific clearance simulated')
presentation._call = offline_call
presentation._check = checker
try:
    presentation.run(c, PAIR, restart=True)
except CheckerReached:
    pass
else:
    raise AssertionError('normal checker gate was not reached')
archive = pd / 'presentation-history/attempt-0001'
assert all((archive / rel).read_bytes() == body for rel, body in old.items())
assert all(p.read_bytes() == body for p, body in accepted.items())
assert calls == [('present', 'editor')]
assert before == {str(p.relative_to(original)): sha(p) for p in original.rglob('*') if p.is_file()}
result = dict(engine=str(Path(thread.__file__).resolve()), copy=str(root), original_build=False,
              refreshed_build=True, canonical_checker_gate_reached=True, stub_calls=calls,
              original_thread_files_unchanged=len(before), archived_failed_files_preserved=len(old),
              accepted_root_files_unchanged=len(accepted), source_sha256=sha(control / 'paper.tex'),
              old_metadata_sha256=hashlib.sha256(old_meta).hexdigest(),
              new_metadata_sha256=hashlib.sha256(new_meta).hexdigest(),
              real_model_calls=0)
print(json.dumps(result, indent=2))
Path(__file__).with_name('copy-result.json').write_text(json.dumps(result, indent=2)+'\n')
