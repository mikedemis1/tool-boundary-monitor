import pytest
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite

from tbm.cases import (
    build_case,
    context_from_public,
    environment_from_public,
    proposals_from_public,
    public_case,
)
from tbm.effects import resolve_effect
from tbm.normalize import normalize
from tbm.policy import evaluate_policy


def inputs(family, variant="attack"):
    public = public_case(build_case(family, 0, variant))
    runtime = FunctionsRuntime(get_suite("v1.2.2", "banking").tools)
    effect = resolve_effect(
        normalize(proposals_from_public(public)[-1], runtime.functions),
        environment_from_public(public).model_dump(),
    )
    return context_from_public(public), effect


@pytest.mark.parametrize(
    "family,reason",
    [
        ("F01", "TASK_RESOURCE_FORBIDDEN"),
        ("F02", "TASK_AMOUNT_EXCEEDED"),
        ("F03", "TASK_FIELD_MISMATCH"),
        ("F04", "TASK_RESOURCE_FORBIDDEN"),
        ("F05", "SCOPE_MISSING"),
        ("F07", "TASK_FIELD_MISMATCH"),
        ("F08", "TASK_FIELD_MISMATCH"),
        ("U01", "AUTHORITY_UNRESOLVED"),
    ],
)
def test_attack_policy_table(family, reason):
    c, e = inputs(family)
    r = evaluate_policy(c, e, 0, 0, "hard", shadow_allowed=True)
    assert r.reason_codes == (reason,)
    assert r.decision == ("approve" if family == "U01" else "block")
    assert evaluate_policy(c, e, 0, 0, "none").decision == "allow"
    assert evaluate_policy(c, e, 0, 0, "scopes").decision == (
        "block" if family == "F05" else "allow"
    )


def test_next_payment_ledger_equality_and_overflow():
    c, e = inputs("F06")
    assert evaluate_policy(c, e, 2, 20000, "hard").decision == "allow"
    assert evaluate_policy(c, e, 3, 30000, "hard").reason_codes == ("TASK_BUDGET_EXCEEDED",)
    c, e = inputs("F01", "benign")
    assert evaluate_policy(c, e, 1, 10000, "hard").reason_codes == ("TASK_COUNT_EXCEEDED",)


def test_approval_cannot_override_known_violation():
    c, e = inputs("U01")
    e = e.model_copy(update={"amount_minor": 10100})
    assert evaluate_policy(c, e, 0, 0, "hard", approval_satisfies=True).decision == "block"
    c, e = inputs("F01")
    assert evaluate_policy(c, e, 0, 0, "hard", approval_satisfies=True).decision == "block"


def test_explicit_approval_and_observation():
    c, e = inputs("F01", "benign")
    assert evaluate_policy(c, e, 0, 0, "hard", shadow_allowed=True).decision == "shadow"
    c = c.model_copy(update={"contract": c.contract.model_copy(update={"approval_required": True})})
    assert evaluate_policy(c, e, 0, 0, "hard").reason_codes == ("APPROVAL_REQUIRED",)
    assert evaluate_policy(c, e, 0, 0, "hard", approval_satisfies=True).decision == "allow"


def test_task_tool_and_scope_priority():
    c, e = inputs("F05")
    c = c.model_copy(update={"granted_scopes": frozenset({"profile:password"})})
    assert evaluate_policy(c, e, 0, 0, "hard").reason_codes == ("TASK_TOOL_FORBIDDEN",)


@pytest.mark.parametrize("family", ["F01", "F03", "F07", "U01"])
def test_exact_payment_does_not_authorize_smaller_amount(family):
    c, e = inputs(family, "benign")
    e = e.model_copy(update={"fields": e.fields | {"amount": 50.0}, "amount_minor": 5000})
    assert evaluate_policy(c, e, 0, 0, "hard", approval_satisfies=True).reason_codes == (
        "TASK_FIELD_MISMATCH",
    )
