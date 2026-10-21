# Deployment file lifecycle

The `lifecycle` command inventories deployment files without changing campaigns,
calling models, installing ignore rules, staging files or deleting evidence. It
works on a campaign or a deployment directory without requiring campaign.json.
It is separate from legacy `gc`, which can compact receipts and remove downloads.
Do not use legacy `gc` for a preservation-only cleanup.

## Classification and custody

Every inventoried file has its relative path, type, size, SHA256, mode, Git state
(tracked, ignored or untracked), category and retention recommendation. Files
under source pools and inputs are retained source data. Thread evidence, releases,
receipts and runtime manifests are retained evidence. Unknown files are explicitly
`retain-unclassified`. Existing ignored retained files are flagged for review.

Only Python bytecode in `__pycache__` and `.DS_Store` outside known retained
subtrees are proposed as reproducible cache. Even these are only dry-run candidates.
The engine does not classify PDFs, downloaded text, peer directories, transcripts,
NPZ data, working notes or old review rounds as disposable by extension or age.
Citations cannot reliably identify every required dependency, so retention is the
default. Configuration and code should be versioned. Large evidence can be retained
in a verified archive whose digest and manifest are versioned by the operator.

Git administration (`.git` at any depth) is excluded explicitly. This archive is
not a backup of Git history. Empty directories are not captured. Symlinks are
inventoried without following them; archive creation refuses them. Special files
also cause refusal. File modes and bytes are preserved, not timestamps, ACLs or
extended attributes. Configured pools outside the chosen root need their own
inventory/archive; they are never traversed implicitly.

## Read-only review

Run these commands with the deployment root, saving reports outside that root:

```sh
python -P -m pathfinder.cli --root /path/to/deployment lifecycle inventory
python -P -m pathfinder.cli --root /path/to/deployment lifecycle cleanup
python -P -m pathfinder.cli --root /path/to/deployment lifecycle ignores
```

`cleanup` is always a dry-run and reports ownership blockers. There is no apply
flag or deletion operation. Ignore output is a proposal containing exact paths,
not broad directory patterns. Review it before installing it in .gitignore.
Ignoring a file does not preserve its content or authorise its deletion.

## Archive and restore

Quiesce writers before archiving. Existing runner OS locks are acquired for the
capture; active thread owners and any unresolved active-call record cause refusal.
The complete inventory is compared again after capture and every archive member
is verified before exclusive publication. A newly starting campaign without an
existing lock is not blocked by these probes: this is not a scheduler barrier or
a transactional snapshot of arbitrary external writers. A busy read-only inventory
is observational and can fail if files change.

```sh
python -P -m pathfinder.cli --root /path/to/deployment lifecycle archive --dest /backup/deployment.tgz
python -P -m pathfinder.cli lifecycle verify --archive /backup/deployment.tgz
python -P -m pathfinder.cli lifecycle restore --archive /backup/deployment.tgz --dest /new/restore --sha256 ARCHIVE_SHA256
```

Keep the returned archive SHA256 receipt independently with the versioned custody
record. Restore requires that external digest, validates the full member set and
all hashes, rejects traversal, links and duplicate members, and only writes a new
destination. It never merges into a live run. An interrupted restore may leave a
partial new destination; preserve or remove that destination separately before a
new attempt. Restored ownership metadata is historical evidence, not permission
to resume a campaign. Inspect it through normal recovery procedures.

For retained local originals backed by an archive, generate a separate proposal:

```sh
python -P -m pathfinder.cli --root /path/to/deployment lifecycle ignores --archive /backup/deployment.tgz
```

Each retained path is eligible only when its type, mode, size and full hash match
the verified archive entry. Changed files and new unknown files remain unclassified
for custody. Already tracked files are not proposed for ignoring. The archive's
inventory digest is included in the proposed rules. No ignore file is installed,
no Git index is changed, and no original is removed. Version the archive receipt
and manifest alongside any installed ignore rules. Archive splitting and remote
backup are operator tasks; this command does not claim remote durability.
