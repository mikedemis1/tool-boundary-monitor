"""Normalize only representation; do not execute native function resolution."""

import hashlib
import hmac
import json
import math
from copy import deepcopy
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from tbm.contracts import InputRejected, NormalizedCall, Proposal
from tbm.registry import TOOL_POLICIES


def canonical(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def fingerprint(key: bytes, payload: bytes) -> str:
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def amount_to_minor(value: int | float) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputRejected("ARGUMENT_INVALID")
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > 10000000:
            raise InputRejected("ARGUMENT_INVALID")
        cents = amount * 100
        if cents != cents.to_integral_value():
            raise InputRejected("UNSUPPORTED_AMOUNT_PRECISION")
        return int(cents)
    except InvalidOperation:
        raise InputRejected("ARGUMENT_INVALID") from None


def normalize(proposal: Proposal, functions: dict) -> NormalizedCall:
    if proposal.tool_name not in TOOL_POLICIES or proposal.tool_name not in functions:
        raise InputRejected("TOOL_UNKNOWN")
    raw = proposal.arguments
    if not isinstance(raw, dict):
        raise InputRejected("ARGUMENT_INVALID")
    for name, value in raw.items():
        if not isinstance(name, str):
            raise InputRejected("ARGUMENT_INVALID")
        if value is not None and type(value) not in (str, int, float, bool):
            raise InputRejected("NESTED_CALL_REJECTED")
        if isinstance(value, str) and len(value) > 8192:
            raise InputRejected("ARGUMENT_INVALID")
        if isinstance(value, float) and not math.isfinite(value):
            raise InputRejected("ARGUMENT_INVALID")
        if name in ("amount", "id", "n") and isinstance(value, bool):
            raise InputRejected("ARGUMENT_INVALID")
    try:
        if len(canonical(raw)) > 16384:
            raise InputRejected("ARGUMENT_INVALID")
        schema = functions[proposal.tool_name].parameters
        if not raw.keys() <= schema.model_fields.keys():
            raise InputRejected("ARGUMENT_INVALID")
        args = schema.model_validate(deepcopy(raw)).model_dump()
        if args.get("amount") is not None:
            cents = amount_to_minor(args["amount"])
            if proposal.tool_name in ("send_money", "schedule_transaction") and cents == 0:
                raise InputRejected("ARGUMENT_INVALID")
        data = canonical({"tool_name": proposal.tool_name, "arguments": args})
    except (ValidationError, TypeError, ValueError, OverflowError) as exc:
        if isinstance(exc, InputRejected):
            raise
        raise InputRejected("ARGUMENT_INVALID") from None
    return NormalizedCall(tool_name=proposal.tool_name, arguments=args, canonical_bytes=data)
