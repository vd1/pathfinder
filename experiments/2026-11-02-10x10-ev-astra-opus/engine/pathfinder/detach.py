"""Start a long run detached from the shell or agent tool session that launches it:

    python -m pathfinder.detach LOG -- uv run pathfinder --root CAMPAIGN research

The command runs in a new session and process group, with stdin closed and stdout and stderr appended to LOG,
so it outlives its launcher; the pid is printed. An agent's tool session tears down its process group when it
ends, and when the agent's daemon restarts: a runner started inside it goes with it (proofTree planar S21,
8 October 2026: a Codex daemon's graceful restart)."""
from __future__ import annotations
import os, sys


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] != "--":
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    log, command = argv[0], argv[2:]
    read, write = os.pipe()
    pid = os.fork()
    if pid == 0:                                   # the child leaves the launcher's session, then forks the run
        os.close(read)
        os.setsid()
        run = os.fork()
        if run:
            os.write(write, str(run).encode()); os._exit(0)
        os.close(write)
        out = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        null = os.open(os.devnull, os.O_RDONLY)
        os.dup2(null, 0); os.dup2(out, 1); os.dup2(out, 2)
        try:
            os.execvp(command[0], command)
        finally:
            os._exit(127)
    os.close(write)
    os.waitpid(pid, 0)
    run = os.read(read, 32).decode()
    print(run)
    return 0 if run else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
