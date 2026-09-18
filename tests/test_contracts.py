import pytest
from agentdojo.task_suite.load_suites import get_suite
from pydantic import ValidationError

from tbm.contracts import Proposal, TaskContract, TrustedContext
from tbm.registry import TOOL_POLICIES


def task(**changes):
    values = dict(
        allowed_tools=["send_money", "read_file"],
        allowed_resources=["payment:vendor", "file:notes.txt"],
        exact_fields={"subject": "Invoice"},
        max_amount_minor=10000,
        max_total_send_minor=10000,
        max_send_count=1,
        unresolved_fields=[],
        approval_required=False,
        authority_basis="trusted_fixture_policy",
    )
    return TaskContract(**(values | changes))


def test_proposal_cannot_supply_authority():
    with pytest.raises(ValidationError):
        Proposal(
            request_id="r1", tool_name="get_balance", arguments={}, granted_scopes=["payments:send"]
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"allowed_resources": ["*"]},
        {"max_amount_minor": -1},
        {"exact_fields": {"absent_field": 1}},
        {"allowed_tools": ["hidden_tool"]},
        {"unresolved_fields": ["absent_field"]},
        {"allowed_tools": ["send_money", "update_password"]},
    ],
)
def test_invalid_trusted_contract_is_rejected(changes):
    with pytest.raises((ValidationError, ValueError)):
        task(**changes)


def test_empty_context_identity_is_rejected():
    with pytest.raises(ValidationError):
        TrustedContext(
            principal_id="",
            agent_id="a",
            task_run_id="t",
            session_id="s",
            task_class="payment",
            policy_version="p",
            grant_version="g",
            granted_scopes=["payments:send"],
            contract=task(),
        )


def test_registry_matches_native_exposed_tools():
    assert set(TOOL_POLICIES) == {t.name for t in get_suite("v1.2.2", "banking").tools}
    assert TOOL_POLICIES["update_scheduled_transaction"].required_scope == "payments:update"
