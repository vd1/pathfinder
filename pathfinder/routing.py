"""Per-stage model routing: campaign.json "routes" picks the backend, model and reasoning effort of a stage,
or of one actor of a stage, without the stage knowing.

    "routes": {"peer": {"backend": "codex", "model": "gpt-6-astra", "effort": "medium"},
               "edit/pce-critic": {"backend": "claude", "model": "claude-opus-5", "effort": "medium"}}

A key is a stage ("peer") or a stage and actor ("edit/pce-critic"); the stage-and-actor key wins. A route
names any of backend, model and effort; what it leaves out stays as the stage chose it. Routing happens once,
in transport.execute, so every stage that builds a request is routed alike, and a routed call's receipt
records the route (julien-2 ran research on codex and its assessor stages on claude: routes and
stage_routes in each experiment.json)."""
from __future__ import annotations
import copy, dataclasses

STAGES = ("scan", "peer", "consolidate", "verify", "ledger_review", "edit", "author", "review", "actionability")
BACKENDS = ("codex", "claude", "elm", "stub")
EFFORTS = ("minimal", "low", "medium", "high", "xhigh", "max")
KEYS = ("backend", "model", "effort")


def validate(raw: dict) -> None:
    """A malformed route fails at load, not at the first call it would route; composable overrides too."""
    _check(raw.get("routes"))
    fallback = raw.get("refusal_fallback")
    if fallback is not None:
        try:
            _check({"peer": fallback})
        except ValueError as error:
            raise ValueError(f"refusal_fallback: {error}".replace("routes.peer", "route")) from None
    for block in ("branch", "joint"):
        if isinstance(raw.get(block), dict):
            _check(raw[block].get("routes"))


def _check(routes) -> None:
    if routes is None:
        return
    if not isinstance(routes, dict):
        raise ValueError(f"routes must be an object of stage (or stage/actor) keys, got {routes!r}")
    for key, route in routes.items():
        stage, _, actor = key.partition("/")
        if stage not in STAGES or ("/" in key and not actor):
            raise ValueError(f"routes key {key!r} names no stage: use one of {', '.join(STAGES)}, "
                             "optionally followed by /actor")
        if not isinstance(route, dict):
            raise ValueError(f"routes.{key} must be an object with backend, model or effort, got {route!r}")
        if set(route) - set(KEYS):
            raise ValueError(f"routes.{key} has unknown keys {sorted(set(route) - set(KEYS))}")
        if not set(route) & set(KEYS):
            raise ValueError(f"routes.{key} names none of backend, model, effort")
        if "backend" in route and route["backend"] not in BACKENDS:
            raise ValueError(f"routes.{key}.backend must be one of {', '.join(BACKENDS)}, got {route['backend']!r}")
        if "model" in route and (not isinstance(route["model"], str) or not route["model"].strip()):
            raise ValueError(f"routes.{key}.model must be a non-empty string, got {route['model']!r}")
        if "effort" in route and route["effort"] not in EFFORTS:
            raise ValueError(f"routes.{key}.effort must be one of {', '.join(EFFORTS)}, got {route['effort']!r}")


def resolve(campaign, stage: str, actor: str | None):
    """(key, route) for a call, the stage-and-actor key before the stage key; None when no route applies."""
    routes = (campaign.raw or {}).get("routes") or {}
    for key in (f"{stage}/{actor}", stage):
        if key in routes:
            return key, routes[key]
    return None


def apply(campaign, request):
    """The campaign and request a call runs with: unchanged without a route; otherwise a copy of the campaign
    on the routed backend with the routed effort (Codex: model_reasoning_effort; Claude: --effort), the
    request on the routed model, and the route the receipt records."""
    found = resolve(campaign, request.stage, request.actor)
    if found is None:
        return campaign, request
    key, route = found
    routed = copy.copy(campaign)
    # a stub campaign (a deployment's contract on a copy) stays on the stub: a route never makes a real call
    backend = campaign.backend if campaign.backend == "stub" else route.get("backend", campaign.backend)
    raw = dict(campaign.raw or {})
    if "effort" in route:
        side = "claude" if backend == "claude" else "codex"
        raw[side] = {**(raw.get(side) or {}), ("effort" if side == "claude" else "reasoning_effort"): route["effort"]}
    routed.backend, routed.raw = backend, raw
    request = dataclasses.replace(request, model=route.get("model", request.model))
    routed.route = {"key": key, "backend": backend, "model": request.model, "effort": route.get("effort")}
    return routed, request


def fallback(campaign, request):
    """The campaign and request for one more attempt after a provider's safety filter refused the call:
    "refusal_fallback" in campaign.json, a route ({backend, model, effort}) applied over the call as it ran.
    None without one, or when the call already ran there. A stub campaign stays on the stub."""
    route = (campaign.raw or {}).get("refusal_fallback")
    if not route:
        return None
    backend = campaign.backend if campaign.backend == "stub" else route.get("backend", campaign.backend)
    model = route.get("model", request.model)
    if (backend, model) == (campaign.backend, request.model):
        return None
    routed = copy.copy(campaign)
    raw = dict(campaign.raw or {})
    if "effort" in route:
        side = "claude" if backend == "claude" else "codex"
        raw[side] = {**(raw.get(side) or {}), ("effort" if side == "claude" else "reasoning_effort"): route["effort"]}
    routed.backend, routed.raw = backend, raw
    routed.route = {"key": "refusal_fallback", "backend": backend, "model": model, "effort": route.get("effort")}
    return routed, dataclasses.replace(request, model=model)
