"""Contracts over parsers (D5, R4, H8).

Every structured reply has one declared schema here. A reply is read once: the JSON object is extracted,
a string "decision" is upper-cased, and the value is checked against its schema and, where a stage has
rules a schema cannot say (each active request disposed of exactly once), against a check function. A
violation earns one repair turn (`ensure`); a reply that still violates its contract is an operational
failure of class "contract", never a scientific outcome.

The validator covers the subset the schemas use: type, enum, required, properties, items, minimum,
maximum. `strict` gives the closed form the Codex CLI's --output-schema accepts."""
from __future__ import annotations
import copy
import math
import json
import re
from dataclasses import replace
from . import events, failures, transport

_FINDING = {"type": "object", "properties": {
    "id": {"type": ["string", "null"]}, "severity": {"type": ["string", "null"]}, "where": {"type": ["string", "null"]},
    "issue": {"type": ["string", "null"]}, "fix": {"type": ["string", "null"]}}}
_REQUEST = {"type": "object", "properties": {
    "id": {"type": "string"}, "action": {"enum": ["REVISE", "ITERATE"]}, "text": {"type": "string"}}}
_DISPOSITION = {"type": "object", "properties": {
    "id": {"type": "string"}, "status": {"enum": ["resolved", "deferred"]}, "reason": {"type": "string"}}}

SCHEMAS = {
    "scan": {"type": "object", "required": ["feasibility", "gain"], "properties": {
        "feasibility": {"type": "number", "minimum": 0, "maximum": 100},
        "gain": {"type": "number", "minimum": 0, "maximum": 100},
        "connexion": {"type": ["string", "null"]}, "rationale": {"type": ["string", "null"]}}},
    "verify": {"type": "object", "required": ["decision"], "properties": {
        "decision": {"enum": ["DRAFT", "REVISE", "ITERATE", "PAUSE"]},
        "reason": {"type": ["string", "null"]}, "action": {"type": ["string", "null"]}}},
    "request_review": {"type": "object", "required": ["requests", "dispositions"], "properties": {
        "decision": {"enum": [None, "REVISE", "ITERATE"]},
        "requests": {"type": "array", "items": _REQUEST},
        "dispositions": {"type": "array", "items": _DISPOSITION}}},
    "paper_review": {"type": "object", "required": ["decision"], "properties": {
        "decision": {"enum": ["ACCEPT", "AMEND", "REVISE"]}, "summary": {"type": ["string", "null"]},
        "findings": {"type": "array", "items": _FINDING}}},
}


class ContractViolation(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors[:5]))


def extract_json(text: str):
    """The first JSON object in a reply. TeX in string values, such as \\( x \\), is not valid JSON escaping;
    a second attempt doubles every backslash that does not start a JSON escape."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError("no JSON object in reply")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        # treat every backslash as literal TeX except an escaped quote or backslash; \beta must not become a backspace
        return json.loads(re.sub(r'\\(?!["\\])', r"\\\\", m.group(0)))


_TYPES = {"object": dict, "array": list, "string": str, "null": type(None)}


def _is(value, kind: str) -> bool:
    if kind in ("integer", "number"):           # NaN and infinities are valid JSON to Python, never a score
        return (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                and (kind == "number" or float(value).is_integer()))
    return isinstance(value, _TYPES[kind])


def violations(value, schema: dict, where: str = "reply") -> list[str]:
    kinds = schema.get("type")
    if kinds is not None:
        kinds = kinds if isinstance(kinds, list) else [kinds]
        if not any(_is(value, k) for k in kinds):
            return [f"{where}: expected {' or '.join(kinds)}, got {type(value).__name__}"]
    errors = []
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} is not one of {', '.join(str(e) for e in schema['enum'])}")
    if _is(value, "number"):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{where}: {value} is below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{where}: {value} is above {schema['maximum']}")
    if isinstance(value, dict):
        errors += [f"{where}: missing {key}" for key in schema.get("required", []) if key not in value]
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                errors += violations(value[key], sub, f"{where}.{key}")
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            errors += violations(item, schema["items"], f"{where}[{i}]")
    return errors


def schema_of(contract) -> dict:
    """A contract is the name of an engine schema or, for a deployment's own replies, a schema itself."""
    return contract if isinstance(contract, dict) else SCHEMAS[contract]


def _label(contract) -> str:
    return contract if isinstance(contract, str) else "deployment"


def parse(name, text: str, check=None):
    """The reply's value under contract `name`, or ContractViolation listing every problem."""
    try:
        value = extract_json(text)
    except ValueError as error:                       # json.JSONDecodeError is a ValueError
        raise ContractViolation([f"no readable JSON object: {error}"]) from None
    if isinstance(value, dict) and isinstance(value.get("decision"), str):
        value["decision"] = value["decision"].upper()
    errors = violations(value, schema_of(name))
    if not errors and check is not None:
        try:
            check(value)
        except (ValueError, KeyError, TypeError) as error:
            errors = [str(error)]
    if errors:
        raise ContractViolation(errors)
    return value


def strict(schema: dict) -> dict:
    """The closed form: every object lists all its properties as required and admits no others; a property
    the loose schema leaves optional becomes nullable; an enum gets the type of its values."""
    s = copy.deepcopy(schema)
    if "enum" in s and "type" not in s:
        kinds = sorted({"null" if v is None else "string" for v in s["enum"]})
        s["type"] = kinds[0] if len(kinds) == 1 else kinds
    if s.get("type") == "object" or (isinstance(s.get("type"), list) and "object" in s["type"]):
        props = s.get("properties", {})
        required = set(s.get("required", []))
        for key, sub in props.items():
            sub = strict(sub)
            if key not in required:
                kinds = sub.get("type")
                kinds = kinds if isinstance(kinds, list) else [kinds] if kinds else []
                if "null" not in kinds:
                    sub["type"] = kinds + ["null"]
                if "enum" in sub and None not in sub["enum"]:
                    sub["enum"] = sub["enum"] + [None]
            props[key] = sub
        s["properties"], s["required"], s["additionalProperties"] = props, list(props), False
    if "items" in s:
        s["items"] = strict(s["items"])
    return s


REPAIR_REPLY_CHARS = 50_000


def _repair_prompt(name, reply: str, errors: list[str]) -> str:
    shown = reply if len(reply) <= REPAIR_REPLY_CHARS else reply[:REPAIR_REPLY_CHARS] + "\n[... reply truncated ...]"
    return ("Your previous reply could not be read under its required format. Problems found:\n"
            + "\n".join(f"- {e}" for e in errors[:20])
            + "\n\nRestate the same answer as exactly one JSON object matching this JSON Schema, and nothing else "
            "(no prose, no code fences). Keep the substance of your reply; change only its form, and where the "
            "schema needs something your reply did not say, say it briefly.\n\n## schema\n\n"
            + json.dumps(schema_of(name), indent=1) + "\n\n## your previous reply\n\n" + shown + "\n")


def ensure(campaign, request, result: dict, name, check=None) -> tuple:
    """(value, result) for a reply under contract `name`, after at most one tool-less repair turn in the same
    stage. A transport failure passes through untouched as (None, result). A reply that still violates the
    contract gives (None, result) with failure class "contract" and the violations."""
    if result.get("transport_failed"):
        return None, result
    try:
        return parse(name, result.get("text") or "", check), result
    except ContractViolation as violation:
        first = violation
    events.emit(campaign, "contract_repair", unit=request.thread, stage=request.stage, actor=request.actor,
                contract=_label(name), errors=first.errors[:5])
    repair = replace(request, identity=request.identity + ":contract-repair", tools=False, search=False, reads=False,
                     schema=schema_of(name),
                     prompt=_repair_prompt(name, result.get("text") or "", first.errors))
    contract_failure = failures.Failure("contract", *failures.SCOPES["contract"]).record()
    try:
        repaired = transport.execute(campaign, repair)
    except transport.PromptTooLarge as error:      # the repair turn itself does not fit: the reply stays unreadable
        return None, {**result, "failure": contract_failure, "error": f"contract: {first}; repair refused: {error}",
                      "contract_errors": first.errors, "first_text": result.get("text")}
    repaired = {**repaired, "first_text": result.get("text"), "repaired": True}   # what the model said before restating it
    if repaired.get("transport_failed"):
        return None, repaired
    try:
        return parse(name, repaired.get("text") or "", check), repaired
    except ContractViolation as violation:
        events.emit(campaign, "contract_failed", unit=request.thread, stage=request.stage, actor=request.actor,
                    contract=_label(name), errors=violation.errors[:5])
        return None, {**repaired, "failure": contract_failure,
                      "error": "contract: " + "; ".join(violation.errors[:5]), "contract_errors": violation.errors}
