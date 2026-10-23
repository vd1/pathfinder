"""Conservative file custody, separate from legacy garbage collection.

No deletion or ignore installation. Archives contain every inventoried regular file;
restore only creates a new tree. Git administration is explicitly outside scope.
"""
from __future__ import annotations

import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile
import tempfile
import shutil
from contextlib import contextmanager

VERSION = 'pathfinder-lifecycle-v1'
RETAIN = {'threads', 'branches', 'branch-runs', 'reopened', 'replay', 'release',
          'releases', 'publication', 'operator-log', 'receipts', 'active-calls', 'transport-evidence',
          'paper-pool', 'arxiv-cache', 'sources', 'inputs', 'library', 'pool'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True).encode()


def paths(root):
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs.sort(); files.sort()
        for name in list(dirs):
            if name == '.git':
                dirs.remove(name)
            elif (Path(base) / name).is_symlink():
                dirs.remove(name); files.append(name)
        for name in sorted(files):
            if name != '.git':
                yield Path(base) / name


def category(rel):
    parts = set(rel.parts)
    if parts & {'paper-pool', 'arxiv-cache', 'sources', 'inputs', 'library', 'pool'}:
        return 'retained-source'
    if parts & RETAIN or rel.name in {'receipts.jsonl', 'ledger.jsonl', 'engine-freeze.json'}:
        return 'retained-evidence'
    if rel.name == '.DS_Store' or ('__pycache__' in parts and rel.suffix == '.pyc'):
        return 'reproducible-cache'
    if rel.name in {'campaign.json', 'pyproject.toml', '.gitignore'} or rel.suffix == '.py':
        return 'configuration-or-code'
    return 'retain-unclassified'


def entry(root, path):
    rel = path.relative_to(root)
    s = path.lstat()
    if stat.S_ISLNK(s.st_mode):
        data = os.fsencode(os.readlink(path)); kind = 'symlink'
        size, sha = len(data), digest(data)
    elif stat.S_ISREG(s.st_mode):
        sha = file_digest(path); size = s.st_size; kind = 'file'
        after = path.stat()
        if (after.st_mtime_ns, after.st_size, after.st_ino) != (s.st_mtime_ns, s.st_size, s.st_ino):
            raise RuntimeError(f'file changed during inventory: {rel}')
    else:
        raise RuntimeError(f'unsupported special file: {rel}')
    return {'path': rel.as_posix(), 'kind': kind, 'size': size,
            'sha256': sha, 'mode': stat.S_IMODE(s.st_mode), 'category': category(rel)}


def git_states(root, names):
    def git(*args, data=None):
        return subprocess.run(['git', '-C', str(root), *args], input=data, capture_output=True)
    if git('rev-parse', '--show-toplevel').returncode:
        return {}, 'not-a-git-worktree'
    tracked = git('ls-files', '-z', '--cached', '--', '.')
    if tracked.returncode:
        raise RuntimeError('cannot read git index')
    tracked = set(os.fsdecode(x) for x in tracked.stdout.split(b'\0') if x)
    ignored = git('check-ignore', '-z', '--stdin', data=b''.join(os.fsencode(n) + b'\0' for n in names))
    if ignored.returncode not in (0, 1):
        raise RuntimeError('cannot read git ignore policy')
    ignored = set(os.fsdecode(x) for x in ignored.stdout.split(b'\0') if x)
    return {n: 'tracked' if n in tracked else 'ignored' if n in ignored else 'untracked' for n in names}, 'git'


@contextmanager
def ownership(root):
    """Probe existing OS locks without creating metadata. Hold them during snapshot.

This is not a scheduler barrier: newly created campaigns cannot be excluded. The
operator must quiesce the tree; the complete inventory is checked again afterward.
"""
    handles = []
    try:
        for p in paths(root):
            if p.name == 'runner.lock':
                if p.is_symlink():
                    raise RuntimeError(f'symlink ownership lock: {p}')
                h = p.open('rb'); handles.append(h)
                try:
                    fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise RuntimeError(f'active campaign owner: {p}') from None
            elif p.name == 'lock' and 'threads' in p.parts:
                from .health import alive
                try:
                    pid = int(p.read_text().strip())
                except ValueError:
                    raise RuntimeError(f'unreadable thread owner: {p}') from None
                if alive(pid):
                    raise RuntimeError(f'active thread owner: {p}')
            elif p.parent.name == 'active-calls' and p.suffix == '.json':
                # Even an orphan is retained pending explicit reconciliation.
                raise RuntimeError(f'unresolved active-call record: {p}')
        yield
    finally:
        for h in reversed(handles):
            h.close()


def inventory(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('root must be a directory')
    rows = [entry(root, p) for p in paths(root)]
    states, git = git_states(root, [r['path'] for r in rows])
    for r in rows:
        r['git'] = states.get(r['path'], 'untracked')
        r['recommendation'] = ('ignore-or-archive' if r['category'] == 'reproducible-cache'
                               else 'track-or-archive')
        r['retained_but_ignored'] = r['git'] == 'ignored' and r['category'] != 'reproducible-cache'
    return {'version': VERSION, 'root': str(root), 'git': git,
            'excluded': ['.git administration at any depth; archive is not a Git repository backup'],
            'files': rows, 'files_sha256': digest(encoded(rows))}


def ignore_rules(manifest, archived=None):
    """Exact paths only, never broad rules swallowing future scientific outputs."""
    bound = {r['path']: r for r in archived['files']} if archived else {}
    lines = ['# Proposed exact-path exclusions; no permission to delete retained files.']
    if archived:
        lines.append('# Verified archive inventory SHA256: ' + archived['files_sha256'])
    for r in manifest['files']:
        saved = bound.get(r['path'])
        matches = saved and all(saved[k] == r[k] for k in ('kind', 'size', 'sha256', 'mode'))
        if r['git'] != 'tracked' and (r['category'] == 'reproducible-cache' or matches):
            name = r['path']
            if any(c in name for c in '\r\n') or name.endswith(' '):
                continue
            for c in ('\\', '*', '?', '[', ']', '#', '!'):
                name = name.replace(c, '\\' + c)
            lines.append('/' + name)
    return '\n'.join(lines) + '\n'


def cleanup_plan(root):
    m = inventory(root)
    try:
        with ownership(Path(m['root'])):
            pass
        blocker = None
    except RuntimeError as error:
        blocker = str(error)
    return {'version': VERSION, 'dry_run': True, 'deletion_supported': False,
            'ownership_blocker': blocker, 'manifest_sha256': m['files_sha256'],
            'candidates': [r for r in m['files'] if r['category'] == 'reproducible-cache' and r['git'] != 'tracked'],
            'policy': 'Retain all other files. Archive and verify before any separately authorised removal.'}


def outside(root, dest):
    dest = Path(dest).absolute()
    if dest.exists() or dest.is_symlink():
        raise ValueError('destination already exists')
    if dest.resolve().is_relative_to(root):
        raise ValueError('destination must be outside source tree')
    return dest


def archive(root, dest):
    root = Path(root).resolve(strict=True); dest = outside(root, dest)
    with ownership(root):
        m = inventory(root)
        if any(r['kind'] != 'file' for r in m['files']):
            raise ValueError('archive refuses symlinks; inventory records them without following')
        fd, temp = tempfile.mkstemp(dir=dest.parent, prefix='.lifecycle-')
        os.close(fd)
        try:
            with tarfile.open(temp, 'w:gz') as t:
                body = encoded(m); info = tarfile.TarInfo('manifest.json'); info.size = len(body)
                t.addfile(info, io.BytesIO(body))
                for r in m['files']:
                    source = root / r['path']
                    if source.is_symlink() or file_digest(source) != r['sha256']:
                        raise RuntimeError(f"source changed: {r['path']}")
                    info = tarfile.TarInfo('files/' + r['path']); info.size = r['size']; info.mode = r['mode']
                    with source.open('rb') as handle:
                        t.addfile(info, handle)
            if inventory(root) != m:
                raise RuntimeError('source inventory changed during archive')
            verify_archive(Path(temp))
            os.link(temp, dest)  # exclusive publication: never overwrite
        finally:
            Path(temp).unlink(missing_ok=True)
    return {'archive': str(dest), 'sha256': file_digest(dest), 'files': len(m['files'])}


def safe_name(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or p.as_posix() != name or '.git' in p.parts:
        raise ValueError('unsafe archive path')


def verify_archive(path):
    with tarfile.open(path, 'r:gz') as t:
        members = t.getmembers()
        if any(not x.isfile() for x in members) or len({x.name for x in members}) != len(members):
            raise ValueError('archive contains duplicate or nonregular members')
        m = json.load(t.extractfile('manifest.json'))
        if m['version'] != VERSION or digest(encoded(m['files'])) != m['files_sha256']:
            raise ValueError('invalid manifest digest/version')
        names = [r['path'] for r in m['files']]
        if len(set(names)) != len(names) or {x.name for x in members} != {'manifest.json', *('files/' + n for n in names)}:
            raise ValueError('archive inventory mismatch')
        for r in m['files']:
            safe_name(r['path'])
            if r['kind'] != 'file' or r['mode'] & ~0o777:
                raise ValueError('invalid archived file type/mode')
            member = t.getmember('files/' + r['path'])
            with t.extractfile(member) as handle:
                sha = hashlib.file_digest(handle, 'sha256').hexdigest()
            if member.size != r['size'] or sha != r['sha256']:
                raise ValueError(f"archive hash mismatch: {r['path']}")
        return m


def restore(source, dest, expected_sha256):
    source = Path(source)
    if file_digest(source) != expected_sha256:
        raise ValueError('archive SHA256 differs from external receipt')
    m = verify_archive(source)
    dest = Path(dest).absolute()
    if dest.exists() or dest.is_symlink():
        raise ValueError('restore requires a new destination')
    temp = Path(tempfile.mkdtemp(dir=dest.parent, prefix='.lifecycle-restore-'))
    try:
        with tarfile.open(source, 'r:gz') as t:
            for r in m['files']:
                p = temp / r['path']; p.parent.mkdir(parents=True, exist_ok=True)
                with t.extractfile('files/' + r['path']) as src, p.open('xb') as out:
                    shutil.copyfileobj(src, out, length=1024 * 1024)
                if file_digest(p) != r['sha256'] or p.stat().st_size != r['size']:
                    raise ValueError('archive changed during restore')
                p.chmod(r['mode'])
        # mkdir is exclusive; never merge with an existing run.
        dest.mkdir()
        for p in temp.iterdir():
            p.rename(dest / p.name)
    finally:
        shutil.rmtree(temp)
    return {'destination': str(dest), 'files': len(m['files']), 'archive_sha256': expected_sha256}
