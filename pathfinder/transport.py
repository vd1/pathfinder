"""One adapter over the Claude Code CLI and the Codex CLI. Streams JSON lines so the
session id arrives early; a call with no session within SESSION_GRACE is a transport failure.
Every attempted call appends one receipt. What the provider did not report stays null: never
zero, never an estimate."""
from __future__ import annotations
import dataclasses
from dataclasses import dataclass
import hashlib, json, os, re, shlex, signal, subprocess, threading, time, uuid, random, math
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
    reads: bool = False           # a reader: tools to read the workspace, never to change it
    schema: dict | None = None    # the reply's declared contract (pathfinder.contracts); validated by the engine


class TransportFailed(Exception):
    """Raised by callers when a call never reached a model session, or failed in transport; carries the
    classified failure so the stage's stopped status can say which."""

    def __init__(self, pair_id, failure: dict | None = None):
        super().__init__(pair_id)
        self.failure = failure


def extended(base: float, previous: dict | None) -> int:
    """A stage's allowance, twice its base once when its previous call timed out while working (julien-2,
    2 October: an editor at 600 s was still working); the doubling is not compounded."""
    return int(base * 2) if (previous or {}).get("class") == "timeout" else int(base)


def stopped_reason(failure: dict | None) -> str:
    return f"transport failed: {(failure or {}).get('class', 'unknown')}"


DEFAULT_MAX_PROMPT_CHARS = 1_000_000          # the Codex CLI rejects prompts over 1,048,576 characters


UNSERVED = {"rate", "no_session", "launch"}          # the model never served the call: safe to ask again
TRANSIENT = {"server", "rate", "timeout"}           # the provider failed the call (dropped, at capacity, too slow): ask again


def _campaign_stopped(campaign) -> bool:
    from .admission import _stop_marker
    return _stop_marker(campaign) is not None


def retry_policy(campaign) -> tuple[int, float]:
    raw = campaign.raw or {}
    return int(raw.get("unserved_retries", 1)), float(raw.get("retry_backoff_seconds", 30))


def transient_backoffs(campaign, request, failure: dict) -> list[float]:
    """The waits before asking again a call the provider failed after it started: dropped (server), at capacity
    (rate) or past its full deadline (timeout), from transient_backoff_seconds (default 60 then 120 s; nobel,
    12 October 2026: a provider slowdown stopped three branches and the runner within an hour). A timeout is asked
    again once, since each attempt spends a whole deadline, and a peer's timeout at the allowance's remainder never:
    the turn is over (thread.residual_timeout)."""
    waits = [float(w) for w in (campaign.raw or {}).get("transient_backoff_seconds", [60, 120])]
    if failure.get("class") != "timeout":
        return waits
    allowances = getattr(campaign, "allowances", None) or {}
    if request.stage == "peer" and "peer_seconds" in allowances:
        from .thread import residual_timeout
        if residual_timeout(campaign, request.timeout, failure):
            return []
    return waits[:1]


class PromptTooLarge(Exception):
    """A prompt over the campaign's limit: refused before admission, with a receipt and no launch."""
    failure_class = "input_too_large"


def max_prompt_chars(campaign) -> int:
    return int((campaign.raw or {}).get("max_prompt_chars", DEFAULT_MAX_PROMPT_CHARS))


def _env(campaign, cwd=None):
    env = {k: v for k, v in os.environ.items() if not any(s in k for s in SCRUB)}
    from . import resources                             # the agents build with latexmk themselves; they must see the style files
    env["TEXINPUTS"] = resources.texinputs(campaign, env.get("TEXINPUTS", ""))
    prov = (campaign.raw or {}).get("codex") or {}
    if campaign.backend == "elm":
        env[prov["env_key"]] = os.environ[prov["env_key"]]
    if campaign.backend == "codex" and prov.get("key_file"):
        env[prov["env_key"]] = _key_from_file(campaign.path(prov["key_file"]), prov["env_key"])
    if cwd is not None:                            # the agent's shell, here-documents and TeX write inside its workspace
        base = Path(cwd) / ".pathfinder"
        (base / "tmp").mkdir(parents=True, exist_ok=True)
        (base / "texmf-var").mkdir(parents=True, exist_ok=True)
        env.update(TMPDIR=str(base / "tmp"), TMPPREFIX=str(base / "tmp" / "zsh"), TEXMFVAR=str(base / "texmf-var"))
    return env


def _key_from_file(path, name):
    """Read NAME=value from a dotenv-style file; the value goes to the child environment only."""
    for line in Path(path).read_text().splitlines():
        k, _, v = line.strip().partition("=")
        if k == name:
            return v.strip().strip("'\"")
    raise RuntimeError(f"{name} not found in {path}")


def schema_file(campaign, request) -> Path | None:
    """The strict form of the request's contract as a file for the Codex CLI's --output-schema, when the
    campaign asks for it ("codex": {"output_schema": true}). The Claude CLI gets none: the engine validates."""
    if request.schema is None or campaign.backend in ("claude", "stub"):
        return None
    if not ((campaign.raw or {}).get("codex") or {}).get("output_schema"):
        return None
    from . import contracts
    data = json.dumps(contracts.strict(request.schema), indent=1, sort_keys=True).encode()
    path = campaign.path(f"schemas/{hashlib.sha256(data).hexdigest()}.json")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return path


def _source_cache(campaign) -> Path:
    """The one directory outside its workspace an agent with tools may write: the shared arXiv source cache."""
    from . import library
    path = library.cache(campaign).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _command(campaign, model, tools, search, cwd, reads=False, schema_path=None):
    from . import collection
    restricted = collection.enabled(campaign)
    if restricted:
        collection.validate_config(campaign)
        if campaign.backend != "codex":
            raise collection.Refused("restricted real calls require Codex")
        search = False
    if campaign.backend == "claude":
        cmd = shlex.split(os.environ.get("PATHFINDER_CLAUDE", "claude"))
        cmd += ["-p", "--model", model, "--output-format", "stream-json", "--verbose", "--no-session-persistence"]
        if tools and reads:
            cmd += ["--tools", "Read,Glob,Grep" + (",WebSearch,WebFetch" if search else ""), "--dangerously-skip-permissions"]
        elif tools:
            cmd += ["--tools", CLAUDE_TOOLS + (",WebSearch,WebFetch" if search else ""),
                    "--dangerously-skip-permissions", "--add-dir", str(_source_cache(campaign))]
        else:
            cmd += ["--tools", ""]
        effort = ((campaign.raw or {}).get("claude") or {}).get("effort")     # set by a route (pathfinder.routing)
        if effort:
            cmd += ["--effort", effort]
        return cmd
    cmd = shlex.split(os.environ.get("PATHFINDER_CODEX", "codex"))
    prov = (campaign.raw or {}).get("codex") or {}
    if prov.get("search") == "config":             # CLIs that take web search as configuration, not a flag
        cmd += ["-c", f'web_search="{"live" if tools and search else "disabled"}"']
    elif search and (tools or prov.get("search") == "always"):   # "always": a tool-less call may still search
        cmd += ["--search"]
    cmd += ["exec", "--json", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
            "--cd", str(cwd), "--model", model, "-c", 'approval_policy="never"']
    if restricted:
        cmd += collection.args(campaign, cwd, tools and not reads)
    elif prov.get("filesystem_profile"):             # a per-request permission profile in place of the sandbox mode
        from . import sandbox
        cmd += sandbox.args(cwd, tools and not reads, prov["filesystem_profile"], network=bool(tools and search and not reads),
                            cache=_source_cache(campaign))
    else:
        cmd += ["--sandbox", "workspace-write" if tools and not reads else "read-only"]
        if tools and not reads:                                  # the shared source cache (pathfinder.library)
            cmd += ["--add-dir", str(_source_cache(campaign))]
        if tools and search and not reads:                       # the workspace sandbox has no network unless asked
            cmd += ["-c", "sandbox_workspace_write.network_access=true"]
    if prov.get("persist_sessions"):
        cmd.remove("--ephemeral")
    if prov.get("reasoning_effort"):
        cmd += ["-c", f'model_reasoning_effort="{prov["reasoning_effort"]}"']
    if schema_path is not None:
        cmd += ["--output-schema", str(schema_path)]
    if prov.get("disable_toolless_shell") and not tools:
        cmd += ["-c", "features.shell_tool=false"]
    for entry in prov.get("config") or ():           # a deployment's own Codex settings, each passed with -c
        cmd += ["-c", str(entry)]
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
            message = row["item"].get("text", "")
            if isinstance(message, str) and message.strip():
                text = message  # An empty trailing event must not erase a completed response.
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


def _tool_errors(lines) -> tuple[int, list[str]]:
    """Failed tool uses the session reported (Codex non-zero exit codes, Claude tool results marked as
    errors), with up to five samples of their output, so environment friction shows in the receipt."""
    count, samples = 0, []
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        texts = []
        item = row.get("item") or {}
        if row.get("type") == "item.completed" and item.get("type") == "command_execution" and item.get("exit_code") not in (0, None):
            texts.append(str(item.get("aggregated_output") or f"exit {item.get('exit_code')}"))
        if row.get("type") == "user":
            for block in (row.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result" and block.get("is_error"):
                    texts.append(str(block.get("content")))
        for text in texts:
            count += 1
            if len(samples) < 5:
                samples.append(text.strip()[-200:])
    return count, samples


SOURCE_LIMITS = {   # a source that rate-limits the agents' own requests: (where, what it answers when it does)
    "arxiv": (re.compile(r"arxiv\.org", re.I), re.compile(r"rate exceeded|\b429\b|too many requests", re.I)),
}


def _source_limits(lines) -> dict:
    """Rate limits the agents met in their own tool calls, by source. arXiv answers "Rate exceeded." with a
    successful exit code, so every tool output is read, not only failed ones. A hit needs a call made to the source
    (its address in the command, the query or the tool's input) and its rate-limit answer in the output: an agent
    reading a file that quotes both, such as its own request with its instructions, met no limit. A Claude tool
    result whose call is not on record counts when it is an error naming the source."""
    hits, calls = {}, {}
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        pairs = []                                   # (what was called, what came back)
        item = row.get("item") or {}
        if row.get("type") == "item.completed" and item.get("type") in ("command_execution", "mcp_tool_call", "web_search"):
            called = item.get("command") or item.get("query") or json.dumps(item.get("arguments") or "")
            pairs.append((str(called), str(item.get("aggregated_output") or item.get("result") or "")))
        if row.get("type") == "assistant":
            for block in (row.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls[block.get("id")] = json.dumps(block.get("input") or {})
        if row.get("type") == "user":
            for block in (row.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    content = str(block.get("content"))
                    called = calls.get(block.get("tool_use_id"))
                    if called is None:
                        called = content if block.get("is_error") else ""
                    pairs.append((called, content))
        for called, output in pairs:
            for source, (where, limited) in SOURCE_LIMITS.items():
                if where.search(called) and limited.search(output):
                    hits[source] = hits.get(source, 0) + 1
    return hits


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


_call = threading.local()          # the attempt in progress on this thread: its receipt carries the id


def _receipt(campaign, thread, stage, actor, model, r):
    """Append one receipt and classify the call; r gains the same "failure" value the receipt records."""
    from . import failures
    try:
        rules, rules_error = failures.rules_for(campaign), None
    except Exception as error:                    # a broken deployment rule must not lose the receipt
        rules, rules_error = (), f"{type(error).__name__}: {error}"
    failure = failures.classify(r.get("outcome"), r.get("error"), rules, provider=r.get("provider_error"))
    r["failure"] = failure.record() if failure else None
    if failure is not None and failure.cls == "quota" and r.get("outcome") != "refused":   # the provider's limit: every campaign pauses
        from . import exhaustion
        exhaustion.record(campaign.backend, r.get("error") or "", campaign=campaign.root)
    row = {"v": 3, "call_id": getattr(_call, "id", None) or uuid.uuid4().hex,
           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "run_id": getattr(campaign, "run_id", None),
           "thread": thread, "branch": getattr(campaign, "branch", None), "stage": stage,
           "actor": actor, "backend": campaign.backend, "model": model,
           **{k: r.get(k) for k in ("outcome", "seconds", "deadline_seconds", "usage", "input_tokens", "output_tokens", "cache_write",
                                     "cache_read", "prefix_read", "cost", "cost_basis", "exit_status", "terminal_event",
                                     "raw_events", "error", "failure", "prompt_chars", "tool_calls", "tool_errors",
                                     "tool_error_samples", "source_limits", "provider_error", "provider_errors",
                                     "usage_completeness", "usage_samples", "evidence_journal")}}
    if isinstance(row.get("raw_events"), list):   # commands and answers kept, long tool outputs shortened
        from . import gc
        row["raw_events"] = gc.compact_events(row["raw_events"])
    if r.get("rates"):
        row["rates"] = r["rates"]
    if getattr(campaign, "route", None):           # the route this call ran on (pathfinder.routing)
        row["route"] = campaign.route
    if rules_error:
        row["failure_rules_error"] = rules_error
    with open(campaign.path("receipts.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")
    from . import events
    events.emit(campaign, "call_finished", unit=thread, stage=stage, actor=actor, outcome=r.get("outcome"),
                failure_class=(r["failure"] or {}).get("class"), seconds=r.get("seconds"),
                input_tokens=r.get("input_tokens"), output_tokens=r.get("output_tokens"),
                cache_read=r.get("cache_read"), tool_calls=r.get("tool_calls"), tool_errors=r.get("tool_errors"))
    failures.stop_for(campaign, failure, r.get("error"))
    if failure is not None and failure.cls in ("rate", "server"):
        _cool_down(campaign, r.get("error"), model, (r.get("provider_error") or {}).get("retry_after_seconds"))
    return failure


def _cool_down(campaign, reason, model=None, retry_after=None):
    """Hold admission for the retry backoff after a rate limit; a later cooldown keeps the later end."""
    from .admission import _cooldown_roots
    from . import health, provider_cooldown
    delay = max(retry_policy(campaign)[1], retry_after or 0.)
    if provider_cooldown.extend(campaign, model or campaign.model, delay, reason):
        return
    for root in _cooldown_roots(campaign):           # the arms of one parent share the account, so they cool together
        if not root.is_dir():                        # never create a missing parent
            print(f"cooldown not recorded at {root}: no such directory")
            continue
        path = root / "cooldown.json"
        until = time.time() + delay
        try:
            until = max(until, float(json.loads(path.read_text()).get("until", 0)))
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        try:
            health.write(path, {"until": until, "reason": reason})   # unique temporary name: siblings write the parent
        except OSError as error:                     # a missing or read-only parent must not fail the call's bookkeeping
            print(f"cooldown not recorded at {root}: {error}")


def _failed(campaign, thread, stage, actor, model, started, outcome, error, prompt_chars=None, evidence=None):
    """A call that never reached a model session: a receipt with no usage and no cost."""
    r = {"text": "", "session": None, "seconds": round(time.time() - started, 1), "usage": None, "input_tokens": None,
         "output_tokens": None, "cache_write": None, "cache_read": None, "prefix_read": None, "cost": None,
         "cost_basis": None, "outcome": outcome, "error": error, "transport_failed": True,
         "prompt_chars": prompt_chars, "tool_calls": None, **(evidence or {})}
    _receipt(campaign, thread, stage, actor, model, r)
    return r


RESULT_KEYS = ("text", "session", "seconds", "usage", "input_tokens", "output_tokens", "cache_write", "cache_read",
               "prefix_read", "cost", "cost_basis", "rates", "outcome", "error", "transport_failed", "exit_status",
               "terminal_event", "raw_events", "failure", "prompt_chars", "tool_calls", "tool_errors", "tool_error_samples",
               "provider_error", "provider_errors", "usage_completeness", "usage_samples", "evidence_journal")


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


def _retry_deadline(campaign, request):
    from . import provider_evidence
    provider_evidence.validate_options(campaign.raw or {})
    retries, backoff = retry_policy(campaign)
    waits = transient_backoffs(campaign, request, {})
    ceiling = request.timeout * (1 + max(0, retries) + len(waits)) + max(0, retries) * backoff + sum(waits)
    seconds = float((campaign.raw or {}).get("retry_episode_seconds", ceiling))
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("retry_episode_seconds must be finite and positive")
    return time.monotonic() + seconds


def _retry_delay(campaign, base, result):
    fraction = float((campaign.raw or {}).get("retry_jitter_fraction", .5))
    if not math.isfinite(base) or base < 0 or not 0 <= fraction <= 1:
        raise ValueError("retry delays must be finite/nonnegative and jitter fraction in [0,1]")
    hint = (result.get("provider_error") or {}).get("retry_after_seconds") or 0.
    return max(random.uniform(base * (1 - fraction), base), hint)


def _admitted_attempt(campaign, request, deadline):
    from . import provider_cooldown, budget_group, admission
    while True:
        with provider_cooldown.gate(campaign, request, deadline) as lease:
            try:
                with budget_group.admission(campaign, request), admission.admission(
                        campaign, request.stage, request.actor, thread=request.thread, model=request.model):
                    provider_cooldown.check(campaign, request.model, lease)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        admission._refuse(campaign, request.thread, request.stage, request.actor, request.model,
                                          'retry episode exhausted before dispatch; no call started')
                    bounded = dataclasses.replace(request, timeout=min(request.timeout, math.ceil(remaining)))
                    result = _attempt(campaign, bounded)
                    lease['successful'] = result.get('outcome') == 'completed'
                    return result
            except provider_cooldown.Deferred:
                pass  # Release seats/group lock before returning to the shared wait.


def execute(campaign, request: ModelRequest):
    """Refuse an oversized prompt, then admit the call, then record an active attempt before launching it,
    including abrupt-exit evidence. A refused call raises before any active-call record exists. A campaign
    route for the request's stage (pathfinder.routing) applies first, so every stage is routed alike."""
    from . import routing, library, collection
    campaign, request = routing.apply(campaign, request)
    if collection.enabled(campaign):
        collection.check_request(campaign, request)
        request = dataclasses.replace(request, search=False)
    request = dataclasses.replace(request, prompt=library.request_rule(campaign, request) + request.prompt)
    request = _json_only(campaign, request)
    limit, size = max_prompt_chars(campaign), len(request.prompt)
    if size > limit:
        error = f"input too large: {size} characters exceed {limit}; no model call started"
        _receipt(campaign, request.thread, request.stage, request.actor, request.model, {
            "outcome": "refused", "seconds": 0.0, "usage": None, "input_tokens": None, "output_tokens": None,
            "cache_write": None, "cache_read": None, "prefix_read": None, "cost": None, "cost_basis": None,
            "error": error, "prompt_chars": size, "tool_calls": None})
        raise PromptTooLarge(error)
    from . import admission, budget_group
    retries, backoff = retry_policy(campaign)
    unserved_asked = transient_asked = 0
    deadline = _retry_deadline(campaign, request)
    while True:
        result = _admitted_attempt(campaign, request, deadline)
        failure = result.get("failure") or {}
        wait = None
        if failure.get("scope") != "campaign" and failure.get("retry"):
            if (failure.get("class") in UNSERVED and result.get("session") is None and unserved_asked < retries):
                wait, unserved_asked = backoff, unserved_asked + 1    # never served: nothing was read, written or spent
            elif failure.get("class") in TRANSIENT:
                waits = transient_backoffs(campaign, request, failure)
                if transient_asked < len(waits):
                    wait, transient_asked = waits[transient_asked], transient_asked + 1
        if wait is None or _campaign_stopped(campaign):  # a launch streak may have just stopped the campaign
            break
        wait = _retry_delay(campaign, wait, result)
        from . import events, provider_cooldown
        if time.monotonic() + wait >= deadline:
            events.emit(campaign, "retry_deferred", unit=request.thread, stage=request.stage,
                        reason="provider retry delay exceeds remaining retry episode", delay_seconds=wait)
            break
        provider_cooldown.extend(campaign, request.model, wait, result.get("error"))
        events.emit(campaign, "retry_scheduled", unit=request.thread, stage=request.stage,
                    attempt=unserved_asked + transient_asked, delay_seconds=wait,
                    retry_after_seconds=(result.get("provider_error") or {}).get("retry_after_seconds"))
        if not _wait(campaign, wait):                  # outside admission; an operator's stop ends the wait
            break
    if (result.get("failure") or {}).get("class") == "refusal" and getattr(campaign, "route", {}).get("key") != "refusal_fallback":
        found = routing.fallback(campaign, request)
        if found is not None:                     # a provider's safety filter: once more, on the fallback route
            from . import events
            events.emit(campaign, "admission_deferred", unit=request.thread, stage=request.stage, actor=request.actor,
                        reason=f"refused by {campaign.backend}'s safety filter; retried on {found[0].backend}/{found[1].model}")
            return execute_routed(*found)
    if collection.enabled(campaign):
        collection.check_request(campaign, request)
    return result


def _wait(campaign, seconds: float) -> bool:
    """Sleep before asking again, in steps, so a stop is honoured within 5 s; False when the campaign stopped."""
    left = float(seconds)
    while left > 0:
        if _campaign_stopped(campaign):
            return False
        step = min(left, 5.0)
        time.sleep(step)
        left -= step
    return not _campaign_stopped(campaign)


def _json_only(campaign, request: ModelRequest) -> ModelRequest:
    """Codex can enforce a reply schema; Claude's CLI cannot, and Opus reviews often needed the contract's repair
    turn. A Claude call with a schema ends with the schema and a rule to answer with that JSON object only."""
    if campaign.backend != "claude" or not request.schema or request.prompt.rstrip().endswith(JSON_ONLY_MARK):
        return request
    rule = ("\n\nAnswer with exactly one JSON object that satisfies this schema, and nothing else: no prose before "
            "or after it, no code fence.\n" + json.dumps(request.schema, sort_keys=True) + "\n" + JSON_ONLY_MARK)
    return dataclasses.replace(request, prompt=request.prompt + rule)


JSON_ONLY_MARK = "(JSON only.)"


def execute_routed(campaign, request: ModelRequest):
    """One call on an already routed campaign: admission, then the attempt (the refusal fallback's second try)."""
    from . import admission, library, collection, budget_group
    if collection.enabled(campaign):
        collection.check_request(campaign, request)
        request = dataclasses.replace(request, search=False)
    request = dataclasses.replace(request, prompt=library.request_rule(campaign, request) + request.prompt)
    request = _json_only(campaign, request)
    return _admitted_attempt(campaign, request, _retry_deadline(campaign, request))


def _attempt(campaign, request: ModelRequest):
    from . import health
    attempt = uuid.uuid4().hex
    _call.id = attempt
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
    finally:
        _call.id = None                              # a later receipt on this thread is another call


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
        proc = subprocess.Popen(_command(campaign, model, tools, search, cwd, request.reads, schema_file(campaign, request)), cwd=cwd, env=_env(campaign, cwd),
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
    except OSError as e:
        return _failed(campaign, thread, stage, actor, model, started, "launch failed", f"launch failed: {e}",
                       prompt_chars=len(prompt))
    from . import health
    from . import provider_evidence
    journal = None
    try:
        activity["child_pid"] = proc.pid
        health.write(activity_path, activity)
        journal = provider_evidence.Journal(campaign, activity['attempt_id'])
        activity['evidence_journal'] = {k: str(v) for k, v in journal.paths.items()}
        health.write(activity_path, activity)
    except BaseException:
        _kill(proc)
        if journal is not None:
            journal.close()
        raise
    lines, session_seen, final_seen = [], threading.Event(), threading.Event()

    def reader():
        try:
            for line in proc.stdout:
                journal.append('events.jsonl', line)
                lines.append(line)
                if _final_event(campaign, [line]):
                    final_seen.set()
                if '"session_id"' in line or '"thread.started"' in line:
                    session_seen.set()
        except BaseException as error:
            journal.error = repr(error)
            _kill(proc)

    def stderr_reader():
        try:
            while chunk := proc.stderr.read(4096):
                journal.append('stderr.log', chunk)
        except BaseException as error:
            journal.error = repr(error)
            _kill(proc)

    t = threading.Thread(target=reader, daemon=True); t.start()
    stderr_thread = threading.Thread(target=stderr_reader, daemon=True); stderr_thread.start()

    def finish_evidence(completed=False):
        t.join(5); stderr_thread.join(5)
        if t.is_alive() or stderr_thread.is_alive():
            _kill(proc)
            raise RuntimeError('provider output readers did not finish; active evidence retained')
        journal.close()
        return dict(**provider_evidence.inspect(lines, completed=completed), evidence_journal=journal.manifest())

    try:
        proc.stdin.write(prompt); proc.stdin.close()
    except BrokenPipeError:
        pass
    grace = SESSION_GRACE + len(prompt) // 5000
    deadline = time.monotonic() + grace
    while not session_seen.wait(min(0.1, max(0, deadline - time.monotonic()))):
        if proc.poll() is not None:
            t.join(1)
            evidence = finish_evidence()
            parsed_error = _parse(campaign, model, lines)[4]
            error = parsed_error or journal.stderr_tail.strip()[-500:] or f"exit {proc.returncode} before session"
            return _failed(campaign, thread, stage, actor, model, started, "launch failed", error,
                           prompt_chars=len(prompt), evidence=evidence)
        if time.monotonic() >= deadline:
            _kill(proc)
            return _failed(campaign, thread, stage, actor, model, started, "no session", "no session",
                           prompt_chars=len(prompt), evidence=finish_evidence())
    error, final_at, ended = None, None, False
    while True:                                   # to the deadline, or RESULT_GRACE past the final event
        try:
            proc.wait(timeout=0.5)
            break
        except subprocess.TimeoutExpired:
            pass
        if final_at is None and final_seen.is_set():
            final_at = time.monotonic()
        if final_at is None and time.time() - started >= timeout:
            _kill(proc); error = "timeout"
            break
        if final_at is not None and time.monotonic() - final_at >= RESULT_GRACE:
            _kill_tree(proc); ended = True       # a job the agent left running holds the CLI open (Atlas pilot 6)
            break
    t.join(5)
    evidence = finish_evidence()
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
    if proc.returncode not in (0, None) and not error and not err and not ended:
        err = journal.stderr_tail.strip()[-500:] or f"exit {proc.returncode}"
    evidence.update(provider_evidence.inspect(lines, completed=not (error or err)))
    # Keep raw reported usage, but only complete totals enter accounting counters.
    counters = _counters(campaign.backend, usage if evidence['usage_completeness'] == 'complete' else None)
    cost, basis, rates = _cost(campaign, model, reported, counters)
    r = {"text": text, "session": session, "seconds": round(time.time() - started, 1), "deadline_seconds": timeout,
         "usage": usage, **counters,
          "prefix_read": prefix_read, "cost": cost, "cost_basis": basis, "rates": rates,
          "outcome": "timeout" if error else "error" if err else "completed", "error": error or err,
          "transport_failed": bool(error or err), "exit_status": proc.returncode, "ended_after_final_event": ended,
          "terminal_event": lines[-1].rstrip("\n") if lines else None,
          "prompt_chars": len(prompt), "tool_calls": _tool_calls(lines),
          **dict(zip(("tool_errors", "tool_error_samples"), _tool_errors(lines))),
          "source_limits": _source_limits(lines) or None,
          "raw_events": [line.rstrip("\n") for line in lines], **evidence}
    _receipt(campaign, thread, stage, actor, model, r)
    return r


def request(prompt, *, model, tools, search, cwd, timeout, thread, stage, actor, schema=None, reads=False) -> ModelRequest:
    return ModelRequest(identity=f"{thread}:{stage}", prompt=prompt, model=model, tools=tools, search=search,
                        cwd=Path(cwd), timeout=timeout, thread=thread, stage=stage, actor=actor, schema=schema, reads=reads)


def call(prompt, *, campaign, model, tools, search, cwd, timeout, thread, stage, actor, schema=None, reads=False):
    return execute(campaign, request(prompt, model=model, tools=tools, search=search, cwd=cwd, timeout=timeout,
                                     thread=thread, stage=stage, actor=actor, schema=schema, reads=reads))


RESULT_GRACE = 30                               # seconds a CLI may take to exit after its final event


def _final_event(campaign, lines) -> bool:
    """The CLI has emitted the event that ends its answer: Claude's result, Codex's turn.completed."""
    wanted = "result" if campaign.backend == "claude" else "turn.completed"
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(event, dict) and event.get("type") == wanted:
            return True
    return False


def _descendants(pid: int) -> list[int]:
    """Every process below pid, by parent links (ps), including those that left its process group."""
    try:
        table = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    children = {}
    for row in table.split("\n"):
        parts = row.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            children.setdefault(int(parts[1]), []).append(int(parts[0]))
    out, todo, seen = [], [pid], {pid}
    while todo:
        for child in children.get(todo.pop(), []):
            if child not in seen:
                seen.add(child); out.append(child); todo.append(child)
    return out


def _kill_tree(proc):
    """End the CLI's process group and every descendant, which a job started in its own session escapes."""
    below = _descendants(proc.pid)
    for pid in reversed(below):
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    _kill(proc)


def _kill(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM); proc.wait(5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def receipts(campaign) -> list[dict]:
    """Every call once: a receipt appended twice for one call (a replayed write) is read once."""
    p = campaign.path("receipts.jsonl")
    rows, seen = [], set()
    for line in p.read_text().splitlines() if p.exists() else []:
        if not line.strip():
            continue
        row = json.loads(line)
        key = row.get("call_id")
        if key is not None:
            if key in seen:
                continue
            seen.add(key)
        from . import usage_recovery
        rows.append(_whole_input(usage_recovery.effective(campaign, row)))
    return rows


def _whole_input(row: dict) -> dict:
    """Claude reports input apart from its cache reads and writes, Codex counts cached tokens inside its input:
    read back, a Claude receipt's input_tokens is the whole input (the reported part kept as
    input_tokens_uncached), so budgets, the state and the economy count both providers alike."""
    if row.get("backend") == "claude" and row.get("input_tokens") is not None and "input_tokens_uncached" not in row:
        row = {**row, "input_tokens_uncached": row["input_tokens"],
               "input_tokens": row["input_tokens"] + (row.get("cache_read") or 0) + (row.get("cache_write") or 0)}
    return row


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
