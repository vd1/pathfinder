"""One adapter over the Claude Code CLI and the Codex CLI. Streams JSON lines so the
session id arrives early; a call with no session within SESSION_GRACE is a transport failure.
Every attempted call appends one receipt. What the provider did not report stays null: never
zero, never an estimate."""
from __future__ import annotations
from dataclasses import dataclass
import json, os, shlex, signal, subprocess, threading, time, uuid
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


DEFAULT_MAX_PROMPT_CHARS = 1_000_000          # the Codex CLI rejects prompts over 1,048,576 characters


class PromptTooLarge(Exception):
    """A prompt over the campaign's limit: refused before admission, with a receipt and no launch."""
    failure_class = "input_too_large"


def max_prompt_chars(campaign) -> int:
    return int((campaign.raw or {}).get("max_prompt_chars", DEFAULT_MAX_PROMPT_CHARS))


def _env(campaign):
    env = {k: v for k, v in os.environ.items() if not any(s in k for s in SCRUB)}
    from . import resources                             # the agents build with latexmk themselves; they must see the style files
    env["TEXINPUTS"] = resources.texinputs(campaign, env.get("TEXINPUTS", ""))
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
            cmd += ["--tools", ""]
        return cmd
    cmd = shlex.split(os.environ.get("PATHFINDER_CODEX", "codex"))
    prov = (campaign.raw or {}).get("codex") or {}
    if prov.get("search") == "config":             # CLIs that take web search as configuration, not a flag
        cmd += ["-c", f'web_search="{"live" if tools and search else "disabled"}"']
    elif tools and search:
        cmd += ["--search"]
    cmd += ["exec", "--json", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
            "--cd", str(cwd), "--model", model, "-c", 'approval_policy="never"',
            "--sandbox", "workspace-write" if tools else "read-only"]
    if tools and search:                           # the workspace sandbox has no network unless asked
        cmd += ["-c", "sandbox_workspace_write.network_access=true"]
    prov = (campaign.raw or {}).get("codex") or {}
    if prov.get("persist_sessions"):
        cmd.remove("--ephemeral")
    if prov.get("reasoning_effort"):
        cmd += ["-c", f'model_reasoning_effort="{prov["reasoning_effort"]}"']
    if prov.get("disable_toolless_shell") and not tools:
        cmd += ["-c", "features.shell_tool=false"]
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
    terminal_failure = False
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
            if not terminal_failure:
                err = None  # A completed turn can recover from transient reconnect events.
        elif t in ("error", "turn.failed"):
            detail = row.get("error") or row.get("message") or t
            err = str(detail.get("message") or detail) if isinstance(detail, dict) else str(detail)
            terminal_failure = terminal_failure or t == "turn.failed"
    return text, session, usage, cost, err, prefix_read


def _counters(backend, usage):
    """The monitor's convenience fields, read from the raw usage; a counter that was not reported is None."""
    u = usage or {}
    if backend == "claude":
        return {"input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
                "cache_write": u.get("cache_creation_input_tokens"), "cache_read": u.get("cache_read_input_tokens")}
    return {"input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
            "cache_write": u.get("cache_write_input_tokens"), "cache_read": u.get("cached_input_tokens")}


TOOL_ITEMS = {"command_execution", "web_search", "mcp_tool_call", "file_change"}


def _tool_calls(lines) -> int:
    """Tool uses the session reported: Codex items of a tool type, Claude tool_use content blocks."""
    count = 0
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get("type") == "item.completed" and (row.get("item") or {}).get("type") in TOOL_ITEMS:
            count += 1
        elif row.get("type") == "assistant":
            count += sum(1 for block in (row.get("message") or {}).get("content") or []
                         if isinstance(block, dict) and block.get("type") == "tool_use")
    return count


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
    """Append one receipt and classify the call; r gains the same "failure" value the receipt records."""
    from . import failures
    try:
        rules, rules_error = failures.rules_for(campaign), None
    except Exception as error:                    # a broken deployment rule must not lose the receipt
        rules, rules_error = (), f"{type(error).__name__}: {error}"
    failure = failures.classify(r.get("outcome"), r.get("error"), rules)
    r["failure"] = failure.record() if failure else None
    row = {"v": 3, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "run_id": getattr(campaign, "run_id", None),
           "thread": thread, "stage": stage,
           "actor": actor, "backend": campaign.backend, "model": model,
           **{k: r.get(k) for k in ("outcome", "seconds", "usage", "input_tokens", "output_tokens", "cache_write",
                                     "cache_read", "prefix_read", "cost", "cost_basis", "exit_status", "terminal_event",
                                     "raw_events", "error", "failure", "prompt_chars", "tool_calls")}}
    if r.get("rates"):
        row["rates"] = r["rates"]
    if rules_error:
        row["failure_rules_error"] = rules_error
    with open(campaign.path("receipts.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")
    from . import events
    events.emit(campaign, "call_finished", unit=thread, stage=stage, actor=actor, outcome=r.get("outcome"),
                failure_class=(r["failure"] or {}).get("class"), seconds=r.get("seconds"),
                input_tokens=r.get("input_tokens"), output_tokens=r.get("output_tokens"),
                cache_read=r.get("cache_read"), tool_calls=r.get("tool_calls"))
    failures.stop_for(campaign, failure, r.get("error"))
    return failure


def _failed(campaign, thread, stage, actor, model, started, outcome, error, prompt_chars=None):
    """A call that never reached a model session: a receipt with no usage and no cost."""
    r = {"text": "", "session": None, "seconds": round(time.time() - started, 1), "usage": None, "input_tokens": None,
         "output_tokens": None, "cache_write": None, "cache_read": None, "prefix_read": None, "cost": None,
         "cost_basis": None, "outcome": outcome, "error": error, "transport_failed": True,
         "prompt_chars": prompt_chars, "tool_calls": None}
    _receipt(campaign, thread, stage, actor, model, r)
    return r


RESULT_KEYS = ("text", "session", "seconds", "usage", "input_tokens", "output_tokens", "cache_write", "cache_read",
               "prefix_read", "cost", "cost_basis", "rates", "outcome", "error", "transport_failed", "exit_status",
               "terminal_event", "raw_events", "failure", "prompt_chars", "tool_calls")


def _extension_call(campaign, request, dispatcher):
    """A deployment's transport extension answers the request. The engine has already admitted the call and
    written its active-call record; it normalises the result and writes the receipt, so the engine's
    records do not depend on the extension keeping its own. A missing counter stays unknown."""
    started = time.time()
    try:
        raw = dispatcher(campaign, request)
    except Exception as error:
        r = {"text": "", "outcome": "error", "error": f"transport extension: {error!r}", "transport_failed": True,
             "seconds": round(time.time() - started, 1), "prompt_chars": len(request.prompt)}
        _receipt(campaign, request.thread, request.stage, request.actor, request.model, {k: r.get(k) for k in RESULT_KEYS})
        raise
    if not isinstance(raw, dict) or not isinstance(raw.get("text", ""), str):
        raise TypeError(f"transport extension returned {type(raw).__name__}; expected a result dict with text")
    r = {k: raw.get(k) for k in RESULT_KEYS}
    r["text"] = raw.get("text") or ""
    r["error"] = raw.get("error")
    r["transport_failed"] = bool(raw.get("transport_failed"))
    r["seconds"] = raw.get("seconds") if raw.get("seconds") is not None else round(time.time() - started, 1)
    r["outcome"] = raw.get("outcome") or ("error" if r["error"] or r["transport_failed"] else "completed")
    r["cost_basis"] = raw.get("cost_basis") or ("reported" if raw.get("cost") is not None else None)
    r["prompt_chars"] = len(request.prompt)
    _receipt(campaign, request.thread, request.stage, request.actor, request.model, r)
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
    """Refuse an oversized prompt, then admit the call, then record an active attempt before launching it,
    including abrupt-exit evidence. A refused call raises before any active-call record exists."""
    limit, size = max_prompt_chars(campaign), len(request.prompt)
    if size > limit:
        error = f"input too large: {size} characters exceed {limit}; no model call started"
        _receipt(campaign, request.thread, request.stage, request.actor, request.model, {
            "outcome": "refused", "seconds": 0.0, "usage": None, "input_tokens": None, "output_tokens": None,
            "cache_write": None, "cache_read": None, "prefix_read": None, "cost": None, "cost_basis": None,
            "error": error, "prompt_chars": size, "tool_calls": None})
        raise PromptTooLarge(error)
    from . import admission
    with admission.admission(campaign, request.stage, request.actor, thread=request.thread, model=request.model):
        return _attempt(campaign, request)


def _attempt(campaign, request: ModelRequest):
    from . import health
    attempt = uuid.uuid4().hex
    path = campaign.path(f"active-calls/{attempt}.json")
    started = time.time()
    activity = {"attempt_id": attempt, "run_id": getattr(campaign, "run_id", None),
                "pid": os.getpid(), "thread": request.thread, "stage": request.stage,
                "actor": request.actor, "started_at": started,
                "deadline_at": started + request.timeout, "timeout_seconds": request.timeout,
                "cwd": str(request.cwd) if request.cwd else None}
    health.write(path, activity)
    from . import events
    events.emit(campaign, "call_started", unit=request.thread, stage=request.stage, actor=request.actor,
                attempt_id=attempt, prompt_chars=len(request.prompt))
    try:
        result = _execute(campaign, request, path, activity)
    except BaseException as error:
        health.write(path, {**activity, "exception": repr(error)})
        raise
    else:
        path.unlink(missing_ok=True)
        return result


def _execute(campaign, request: ModelRequest, activity_path, activity):
    """@planks("When Pathfinder records the completed provider call")
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
    if campaign.backend == "stub":                  # model-free contract tests; see pathfinder.stub
        from . import stub
        r = stub.execute(campaign, request)
        _receipt(campaign, thread, stage, actor, model, r)
        return r
    from . import extensions
    dispatcher = extensions.load(campaign, "transport")
    if dispatcher is not None:                      # a deployment's own dispatcher, inside admission and receipts
        return _extension_call(campaign, request, dispatcher)
    started = time.time()
    try:
        proc = subprocess.Popen(_command(campaign, model, tools, search, cwd), cwd=cwd, env=_env(campaign),
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
    except OSError as e:
        return _failed(campaign, thread, stage, actor, model, started, "launch failed", f"launch failed: {e}",
                       prompt_chars=len(prompt))
    from . import health
    activity["child_pid"] = proc.pid
    health.write(activity_path, activity)
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
    grace = SESSION_GRACE + len(prompt) // 5000
    deadline = time.monotonic() + grace
    while not session_seen.wait(min(0.1, max(0, deadline - time.monotonic()))):
        if proc.poll() is not None:
            t.join(1)
            error = (proc.stderr.read() or "").strip()[-500:] or f"exit {proc.returncode} before session"
            return _failed(campaign, thread, stage, actor, model, started, "launch failed", error,
                           prompt_chars=len(prompt))
        if time.monotonic() >= deadline:
            _kill(proc)
            return _failed(campaign, thread, stage, actor, model, started, "no session", "no session",
                           prompt_chars=len(prompt))
    try:
        proc.wait(timeout=max(1, timeout - (time.time() - started)))
        error = None
    except subprocess.TimeoutExpired:
        _kill(proc); error = "timeout"
    t.join(5)
    text, session, usage, reported, err, prefix_read = _parse(campaign, model, lines)
    if campaign.backend != "claude" and not err and not error:
        events = []
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event.get("type"))
        if "turn.completed" not in events:
            err = "CLI exited without a completed turn"
    if proc.returncode not in (0, None) and not error and not err:
        err = (proc.stderr.read() or "").strip()[-500:] or f"exit {proc.returncode}"
    counters = _counters(campaign.backend, usage)
    cost, basis, rates = _cost(campaign, model, reported, counters)
    r = {"text": text, "session": session, "seconds": round(time.time() - started, 1), "usage": usage, **counters,
          "prefix_read": prefix_read, "cost": cost, "cost_basis": basis, "rates": rates,
          "outcome": "timeout" if error else "error" if err else "completed", "error": error or err,
          "transport_failed": bool(error or err), "exit_status": proc.returncode,
          "terminal_event": lines[-1].rstrip("\n") if lines else None,
          "prompt_chars": len(prompt), "tool_calls": _tool_calls(lines),
          "raw_events": [line.rstrip("\n") for line in lines]}
    _receipt(campaign, thread, stage, actor, model, r)
    return r


def call(prompt, *, campaign, model, tools, search, cwd, timeout, thread, stage, actor):
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


UNCHARGED = ("no session", "launch failed", "refused")    # outcomes that never reached a model


def spend(campaign) -> float:
    """What the budget guard counts: known cost, plus the per-call estimate for every call that opened a
    session and whose cost is unknown. A call that never reached a session is not charged, as before, or
    the probes of a long outage would exhaust the budget. The caution lives here, not in the receipts."""
    rows = receipts(campaign)
    charged = sum(1 for r in rows if r.get("cost") is None and r.get("outcome") not in UNCHARGED)
    return round(known_cost(rows) + charged * campaign.call_estimate_usd, 4)
