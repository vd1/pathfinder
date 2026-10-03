"""Session economy (S2, phase 3a): what the calls of a campaign cost in input tokens, by stage and by pair, and
how much of it a prompt cache served. Agent sessions resend their context on every turn, so input tokens grow
with turns and tool calls, not only with the prompt; the measure is over calls that reached a model."""
from __future__ import annotations

UNCHARGED = ("no session", "launch failed", "refused")


def summary(rows: list[dict]) -> dict:
    rows = [r for r in rows if r.get("outcome") not in UNCHARGED and r.get("input_tokens") is not None]
    stages, pairs = {}, {}
    for r in rows:
        s = stages.setdefault(r.get("stage") or "?", {"calls": 0, "input_tokens": 0, "cache_read": 0, "output_tokens": 0,
                                                      "prompt_chars": 0, "tool_calls": 0})
        s["calls"] += 1
        for k in ("input_tokens", "cache_read", "output_tokens", "prompt_chars", "tool_calls"):
            s[k] += r.get(k) or 0
        pairs[r.get("thread")] = pairs.get(r.get("thread"), 0) + (r.get("input_tokens") or 0)
    out = {}
    for name, s in sorted(stages.items()):
        out[name] = {"calls": s["calls"], "input_tokens": s["input_tokens"],
                     "cached_share": round(s["cache_read"] / s["input_tokens"], 3) if s["input_tokens"] else None,
                     "output_tokens": s["output_tokens"], "mean_prompt_chars": round(s["prompt_chars"] / s["calls"]),
                     "mean_tool_calls": round(s["tool_calls"] / s["calls"], 1),
                     "mean_input_tokens": round(s["input_tokens"] / s["calls"])}
    return {"stages": out, "pairs": pairs,
            "mean_input_tokens_per_pair": round(sum(pairs.values()) / len(pairs)) if pairs else None}


def text(s: dict) -> str:
    lines = [f"{'stage':<14}{'calls':>6}{'input':>14}{'cached':>8}{'per call':>12}{'prompt chars':>14}{'tools':>7}"]
    for name, x in s["stages"].items():
        lines.append(f"{name:<14}{x['calls']:>6}{x['input_tokens']:>14,}{(x['cached_share'] or 0):>8.0%}"
                     f"{x['mean_input_tokens']:>12,}{x['mean_prompt_chars']:>14,}{x['mean_tool_calls']:>7}")
    lines.append(f"mean input tokens per pair: {s['mean_input_tokens_per_pair'] or 0:,} over {len(s['pairs'])} pairs")
    return "\n".join(lines)
