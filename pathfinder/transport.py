"""One adapter over the Claude Code CLI and the Codex CLI. Streams JSON lines so the
session id arrives early; a call with no session within SESSION_GRACE is a transport failure.
Every attempted call appends one receipt. What the provider did not report stays null: never
zero, never an estimate."""
from __future__ import annotations
from dataclasses import dataclass
import json, os, shlex, signal, subprocess, threading, time
from pathlib import Path

SESSION_GRACE = 60
SCRUB = ("API_KEY", "OPENAI_", "ANTHROPIC_API", "ELM_")
CLAUDE_TOOLS = "Read,Write,Edit,Bash,Glob,Grep"


@dataclass(frozen=True)
class ModelRequest:
    """@planks("Given a model request requires synchronous workspace tools")
    @planks("Given several independent immutable model requests")
    @planks("Given an immutable model request and a non-Codex synchronous adapter")
    """
    identity: str
    prompt: str
    model: str
    tools: bool
    search: bool
    timeout: int
    thread: str
    stage: str
    actor: str
    cwd: Path | None = None


class TransportFailed(Exception):
    """Raised by callers when a call never reached a model session."""


def _env(campaign):
    env = {k: v for k, v in os.environ.items() if not any(s in k for s in SCRUB)}
    styles = Path(__file__).parent / "styles"          # the agents build with latexmk themselves; they must see the style files
    env["TEXINPUTS"] = f"{styles}{os.pathsep}" + env.get("TEXINPUTS", "")
    prov = (campaign.raw or {}).get("codex") or {}
    if campaign.backend == "elm":
        env[prov["env_key"]] = os.environ[prov["env_key"]]
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
    if campaign.backend == "elm":
        prov = {**prov, "name": "elm", "base_url": "https://elm.edina.ac.uk/api/v1"}
    if prov.get("base_url"):                       # a custom OpenAI-compatible provider, e.g. a university proxy
        name = prov.get("name", "custom")
        cmd += ["-c", f'model_provider="{name}"', "-c", f'model_providers.{name}.name="{name}"',
                "-c", f'model_providers.{name}.base_url="{prov["base_url"]}"',
                "-c", f'model_providers.{name}.env_key="{prov["env_key"]}"',
                "-c", f'model_providers.{name}.wire_api="{prov.get("wire_api", "responses")}"']
    return cmd + ["-"]


def _parse(campaign, model, lines):
    """Text, session, the provider's last usage object as reported (None when none arrived, possibly
    partial on a call that did not complete), the cost the provider reported, the error, the first turn's cache hit."""
    text, session, usage, cost, err, prefix_read = "", None, None, None, None, None
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
        elif t == "assistant" and (row.get("message") or {}).get("usage"):
            usage = row["message"]["usage"]
            if prefix_read is None:                # the first turn's cache hit, the shared-head measurement
                prefix_read = usage.get("cache_read_input_tokens")
        elif t == "result":
            text = row.get("result") or ""
            usage = row.get("usage") or usage
            cost = row.get("total_cost_usd")
            if row.get("is_error"):
                err = text or "error"
        elif t == "item.completed" and (row.get("item") or {}).get("type") == "agent_message":
            text = row["item"].get("text", "")
        elif t == "turn.completed":
            usage = row.get("usage") or usage
        elif t in ("error", "turn.failed"):
            err = str(row.get("error") or row.get("message") or t)
    return text, session, usage, cost, err, prefix_read


def _counters(backend, usage):
    """The monitor's convenience fields, read from the raw usage; a counter that was not reported is None."""
    u = usage or {}
    if backend == "claude":
        return {"input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
                "cache_write": u.get("cache_creation_input_tokens"), "cache_read": u.get("cache_read_input_tokens")}
    return {"input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
            "cache_write": u.get("cache_write_input_tokens"), "cache_read": u.get("cached_input_tokens")}


def _cost(campaign, model, reported, counters):
    """(cost in USD, basis, rates). Reported by the provider, or priced from reported counters with the
    campaign's table, an approximation; otherwise unknown. Codex counts cached tokens inside its input
    total, so when the table has a cached rate and the cached count was reported they are priced apart."""
    if reported is not None:
        return float(reported), "reported", None
    rates, inp, out = campaign.prices.get(model), counters["input_tokens"], counters["output_tokens"]
    if not rates or inp is None or out is None:
        return None, None, None
    cached = counters["cache_read"] if campaign.backend == "codex" and "cached_input_per_m" in rates else None
    if cached is None:
        return campaign.price(model, inp, out), "priced", rates
    return ((inp - cached) * rates["input_per_m"] + cached * rates["cached_input_per_m"]
            + out * rates["output_per_m"]) / 1e6, "priced", rates


def _receipt(campaign, thread, stage, actor, model, r):
    row = {"v": 2, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "thread": thread, "stage": stage,
           "actor": actor, "backend": campaign.backend, "model": model,
           **{k: r.get(k) for k in ("outcome", "seconds", "usage", "input_tokens", "output_tokens", "cache_write",
                                     "cache_read", "prefix_read", "cost", "cost_basis", "exit_status", "terminal_event",
                                     "raw_events", "error")}}
    if r.get("rates"):
        row["rates"] = r["rates"]
    with open(campaign.path("receipts.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")


def _failed(campaign, thread, stage, actor, model, started, outcome, error):
    """A call that never reached a model session: a receipt with no usage and no cost."""
    r = {"text": "", "session": None, "seconds": round(time.time() - started, 1), "usage": None, "input_tokens": None,
         "output_tokens": None, "cache_write": None, "cache_read": None, "prefix_read": None, "cost": None,
         "cost_basis": None, "outcome": outcome, "error": error, "transport_failed": True}
    _receipt(campaign, thread, stage, actor, model, r)
    return r


def execute_sync(request: ModelRequest, adapter):
    """@planks("When Pathfinder assigns the request to Pi")
    @planks("When Pathfinder executes the request")
    """
    return adapter(request)


def execute_batch(requests: list[ModelRequest], adapter):
    """@planks("When Pathfinder assigns them to a batch adapter")"""
    return [adapter(request) for request in requests]


def execute(campaign, request: ModelRequest):
    """@planks("When role \"scan\" executes a minimal frozen paper pair")
    @planks("When Pathfinder records the completed provider call")
    @planks("When Pathfinder completes the provider call without a parsed research account")
    @planks("Then the receipt retains the raw response events")
    @planks("When Pathfinder executes scan, peer, consolidation, and verification model requests")
    @planks("When Pathfinder executes one stage attempt")
    @planks("When Pathfinder verifies execution routing")
    """
    prompt, model, tools, search = request.prompt, request.model, request.tools, request.search
    timeout, thread, stage, actor = request.timeout, request.thread, request.stage, request.actor
    cwd = request.cwd or campaign.path(f"{stage}-work")
    cwd = Path(cwd); cwd.mkdir(parents=True, exist_ok=True)
    started = time.time()
    try:
        proc = subprocess.Popen(_command(campaign, model, tools, search, cwd), cwd=cwd, env=_env(campaign),
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
    except OSError as e:
        return _failed(campaign, thread, stage, actor, model, started, "launch failed", f"launch failed: {e}")
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
    if not session_seen.wait(SESSION_GRACE + len(prompt) // 5000):      # a long prompt takes longer to open
        _kill(proc)
        return _failed(campaign, thread, stage, actor, model, started, "no session", "no session")
    try:
        proc.wait(timeout=max(1, timeout - (time.time() - started)))
        error = None
    except subprocess.TimeoutExpired:
        _kill(proc); error = "timeout"
    t.join(5)
    text, session, usage, reported, err, prefix_read = _parse(campaign, model, lines)
    if proc.returncode not in (0, None) and not error and not err:
        err = (proc.stderr.read() or "").strip()[-500:] or f"exit {proc.returncode}"
    counters = _counters(campaign.backend, usage)
    cost, basis, rates = _cost(campaign, model, reported, counters)
    r = {"text": text, "session": session, "seconds": round(time.time() - started, 1), "usage": usage, **counters,
          "prefix_read": prefix_read, "cost": cost, "cost_basis": basis, "rates": rates,
          "outcome": "timeout" if error else "error" if err else "completed", "error": error or err,
          "transport_failed": False, "exit_status": proc.returncode,
          "terminal_event": lines[-1].rstrip("\n") if lines else None,
          "raw_events": [line.rstrip("\n") for line in lines]}
    _receipt(campaign, thread, stage, actor, model, r)
    return r


def call(prompt, *, campaign, model, tools, search, cwd, timeout, thread, stage, actor):
    """@planks("When Pathfinder submits the role's frozen stage")"""
    request = ModelRequest(
        identity=f"{thread}:{stage}", prompt=prompt, model=model, tools=tools, search=search,
        cwd=Path(cwd), timeout=timeout, thread=thread, stage=stage, actor=actor,
    )
    return execute(campaign, request)


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


def known_cost(rows) -> float:
    return round(sum(r["cost"] for r in rows if r.get("cost") is not None), 4)


def unknown_cost_calls(rows) -> int:
    return sum(1 for r in rows if r.get("cost") is None)


def spend(campaign) -> float:
    """What the budget guard counts: known cost, plus the per-call estimate for every call that opened a
    session and whose cost is unknown. A call that never reached a session is not charged, as before, or
    the probes of a long outage would exhaust the budget. The caution lives here, not in the receipts."""
    rows = receipts(campaign)
    charged = sum(1 for r in rows if r.get("cost") is None and r.get("outcome") not in ("no session", "launch failed"))
    return round(known_cost(rows) + charged * campaign.call_estimate_usd, 4)
