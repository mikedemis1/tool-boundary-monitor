from copy import deepcopy

import pytest
from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite

from tbm.contracts import InputRejected, Proposal
from tbm.normalize import amount_to_minor, fingerprint, normalize


def norm(tool="send_money", **changes):
    args = dict(recipient="vendor", amount=100, subject=" Invoice ", date="2026-10-01")
    args.update(changes)
    p = Proposal.model_construct(request_id="r", tool_name=tool, arguments=args)
    return normalize(p, FunctionsRuntime(get_suite("v1.2.2", "banking").tools).functions)


@pytest.mark.parametrize(
    "args,code",
    [
        ({"amount": True}, "ARGUMENT_INVALID"),
        ({"amount": float("nan")}, "ARGUMENT_INVALID"),
        ({"amount": float("inf")}, "ARGUMENT_INVALID"),
        ({"amount": -1}, "ARGUMENT_INVALID"),
        ({"amount": 0}, "ARGUMENT_INVALID"),
        ({"amount": 100.001}, "UNSUPPORTED_AMOUNT_PRECISION"),
        ({"amount": 10000001}, "ARGUMENT_INVALID"),
        ({"extra": 1}, "ARGUMENT_INVALID"),
        ({"subject": "x" * 8193}, "ARGUMENT_INVALID"),
        (
            {"recipient": {"function": "update_password", "args": {"password": "bad"}}},
            "NESTED_CALL_REJECTED",
        ),
        (
            {"recipient": FunctionCall(function="update_password", args={"password": "bad"})},
            "NESTED_CALL_REJECTED",
        ),
        ({"recipient": ["a"]}, "NESTED_CALL_REJECTED"),
    ],
)
def test_unsafe_arguments_rejected(args, code):
    with pytest.raises(InputRejected) as e:
        norm(**args)
    assert e.value.code == code


def test_unknown_tool():
    with pytest.raises(InputRejected, match="TOOL_UNKNOWN"):
        norm(tool="hidden")


def test_representation_not_business_values_is_canonicalized():
    a = norm(amount=100)
    b = norm(amount=100.0)
    assert a.canonical_bytes == b.canonical_bytes
    assert a.arguments["subject"] == " Invoice "
    assert a.canonical_bytes != norm(recipient="Vendor").canonical_bytes
    assert fingerprint(b"key", a.canonical_bytes) != fingerprint(
        b"key", norm(subject="x").canonical_bytes
    )
    assert amount_to_minor(100.25) == 10025


def test_defaults_and_no_mutation():
    p = Proposal(request_id="r", tool_name="get_most_recent_transactions", arguments={})
    old = deepcopy(p.arguments)
    result = normalize(p, FunctionsRuntime(get_suite("v1.2.2", "banking").tools).functions)
    assert result.arguments == {"n": 100}
    assert p.arguments == old
