"""One adapter over the Claude Code CLI and the Codex CLI. Streams JSON lines so the
session id arrives early; a call with no session within SESSION_GRACE is a transport failure."""
from __future__ import annotations
import json, os, shlex, signal, subprocess, threading, time
from pathlib import Path

SESSION_GRACE = 60
SCRUB = ("API_KEY", "OPENAI_", "ANTHROPIC_API", "ELM_")
CLAUDE_TOOLS = "Read,Write,Edit,Bash,Glob,Grep"


class TransportFailed(Exception):
    """Raised by callers when a call never reached a model session."""


def _env(campaign):
    env = {k: v for k, v in os.environ.items() if not any(s in k for s in SCRUB)}
    styles = Path(__file__).parent / "styles"          # the agents build with latexmk themselves; they must see the style files
    env["TEXINPUTS"] = f"{styles}{os.pathsep}" + env.get("TEXINPUTS", "")
    prov = (campaign.raw or {}).get("codex") or {}
    if campaign.backend == "codex" and prov.get("key_file"):
        env[prov["env_key"]] = _key_from_file(campaign.path(prov["key_file"]), prov["env_key"])
    return env


def _key_from_file(path, name):
    """Read NAME=value from a dotenv-style file; the value goes to the child environment only."""
    for line in Path(path).read_text().splitlines():
        k, _, v = line.strip().partition("=")
        if k == name:
            return v.strip().strip("'\"")
    raise RuntimeError(f"{name} not found in {path}")


def _command(campaign, model, tools, search, cwd):
    if campaign.backend == "claude":
        cmd = shlex.split(os.environ.get("PATHFINDER_CLAUDE", "claude"))
        cmd += ["-p", "--model", model, "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
        if tools:
            cmd += ["--tools", CLAUDE_TOOLS + (",WebSearch,WebFetch" if search else ""),
                    "--dangerously-skip-permissions"]
        else:
            cmd += ["--tools", "", "--permission-prompts", "none"]
        return cmd
    cmd = shlex.split(os.environ.get("PATHFINDER_CODEX", "codex"))
    cmd += ["exec", "--json", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
            "--cd", str(cwd), "--model", model, "-c", 'approval_policy="never"',
            "--sandbox", "workspace-write" if tools else "read-only",
            "-c", f'web_search="{"live" if (tools and search) else "disabled"}"']
    if tools and search:                           # the workspace sandbox has no network unless asked
        cmd += ["-c", "sandbox_workspace_write.network_access=true"]
    prov = (campaign.raw or {}).get("codex") or {}
    if prov.get("base_url"):                       # a custom OpenAI-compatible provider, e.g. a university proxy
        name = prov.get("name", "custom")
        cmd += ["-c", f'model_provider="{name}"', "-c", f'model_providers.{name}.name="{name}"',
                "-c", f'model_providers.{name}.base_url="{prov["base_url"]}"',
                "-c", f'model_providers.{name}.env_key="{prov["env_key"]}"',
                "-c", f'model_providers.{name}.wire_api="{prov.get("wire_api", "responses")}"']
    return cmd + ["-"]


def _parse(campaign, model, lines):
    text, session, inp, out, cost, err = "", None, 0, 0, None, None
    cache = {"cache_write": 0, "cache_read": 0}
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        t = row.get("type")
        if t == "system" and row.get("session_id"):
            session = row["session_id"]
        elif t == "thread.started":
            session = row.get("thread_id")
        elif t == "result":
            text = row.get("result") or ""
            u = row.get("usage") or {}
            inp, out = u.get("input_tokens", 0), u.get("output_tokens", 0)
            cache = {"cache_write": u.get("cache_creation_input_tokens", 0), "cache_read": u.get("cache_read_input_tokens", 0)}
            cost = row.get("total_cost_usd")
            if row.get("is_error"):
                err = text or "error"
        elif t == "item.completed" and (row.get("item") or {}).get("type") == "agent_message":
            text = row["item"].get("text", "")
        elif t == "turn.completed":
            u = row.get("usage") or {}
            inp, out = u.get("input_tokens", 0), u.get("output_tokens", 0)
            cache = {"cache_write": 0, "cache_read": u.get("cached_input_tokens", 0)}
        elif t in ("error", "turn.failed"):
            err = str(row.get("error") or row.get("message") or t)
    if cost is None:
        cost = campaign.price(model, inp, out)
    return text, session, inp, out, cost, err, cache


def call(prompt, *, campaign, model, tools, search, cwd, timeout, thread, stage, actor):
    cwd = Path(cwd); cwd.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(_command(campaign, model, tools, search, cwd), cwd=cwd, env=_env(campaign),
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    lines, session_seen = [], threading.Event()

    def reader():
        for line in proc.stdout:
            lines.append(line)
            if '"session_id"' in line or '"thread.started"' in line:
                session_seen.set()

    t = threading.Thread(target=reader, daemon=True); t.start()
    try:
        proc.stdin.write(prompt); proc.stdin.close()
    except BrokenPipeError:
        pass
    started = time.time()
    if not session_seen.wait(SESSION_GRACE + len(prompt) // 5000):      # a long prompt takes longer to open
        _kill(proc)
        return {"text": "", "session": None, "seconds": round(time.time() - started, 1), "input_tokens": 0,
                "output_tokens": 0, "cost": 0.0, "error": "no session", "transport_failed": True}
    try:
        proc.wait(timeout=max(1, timeout - (time.time() - started)))
        error = None
    except subprocess.TimeoutExpired:
        _kill(proc); error = "timeout"
    t.join(5)
    text, session, inp, out, cost, err, cache = _parse(campaign, model, lines)
    if error == "timeout" and not (inp or out):
        cost = campaign.call_estimate_usd          # usage unknown after a kill: charge the estimate
    if proc.returncode not in (0, None) and not error and not err:
        err = (proc.stderr.read() or "").strip()[-500:] or f"exit {proc.returncode}"
    r = {"text": text, "session": session, "seconds": round(time.time() - started, 1), "input_tokens": inp,
         "output_tokens": out, **cache, "cost": float(cost or 0), "error": error or err, "transport_failed": False}
    with open(campaign.path("receipts.jsonl"), "a") as f:
        f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "thread": thread,
                            "stage": stage, "actor": actor, "backend": campaign.backend, "model": model,
                            **{k: r[k] for k in ("seconds", "input_tokens", "output_tokens", "cache_write", "cache_read", "cost", "error")}}) + "\n")
    return r


def _kill(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM); proc.wait(5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def receipts(campaign) -> list[dict]:
    p = campaign.path("receipts.jsonl")
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def spend(campaign) -> float:
    return round(sum(r.get("cost") or 0 for r in receipts(campaign)), 4)
