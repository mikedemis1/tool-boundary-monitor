from copy import deepcopy

import pytest
from agentdojo.agent_pipeline.tool_execution import ToolsExecutor
from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite

from tbm.agentdojo_adapter import ProtectedRuntime
from tbm.cases import build_case, proposals_from_public, public_case
from tbm.contracts import InputRejected


def batch(adapter, env, calls):
    message = dict(role="assistant", content=None, tool_calls=calls)
    return ToolsExecutor().query("task", adapter, env, [message])[3][1:]


def test_real_dispatcher_batch_preserves_ids_and_policy(gateway_factory):
    public = public_case(build_case("F01", 0, "attack"))
    g, c, e = gateway_factory(public)
    runtime = ProtectedRuntime(g, c, g.runtime.functions)
    attack = proposals_from_public(public)[-1].arguments
    benign = attack | {"recipient": "TBM_VENDOR_0"}
    responses = batch(
        runtime,
        e,
        [
            FunctionCall(id="one", function="send_money", args=attack),
            FunctionCall(id="two", function="send_money", args=benign),
        ],
    )
    assert [r["tool_call_id"] for r in responses] == ["one", "two"]
    assert responses[0]["error"].startswith("TBMBlocked:")
    assert responses[1]["error"] is None
    assert len(e.bank_account.transactions) == 2


def test_approval_pauses_rest_of_native_batch(gateway_factory):
    public = public_case(build_case("U01", 0, "benign"))
    g, c, e = gateway_factory(public)
    runtime = ProtectedRuntime(g, c, g.runtime.functions)
    p = proposals_from_public(public)[-1]
    results = batch(
        runtime,
        e,
        [
            FunctionCall(id="a", function=p.tool_name, args=p.arguments),
            FunctionCall(id="b", function="read_file", args={"file_path": "invoice.txt"}),
        ],
    )
    assert "TBMApprovalRequired:" in results[0]["error"]
    assert results[1]["error"] == "TBMBlocked:APPROVAL_PENDING"
    assert len(g.executed_calls) == 0 and len(g.state.pending) == 1


def test_nested_write_and_native_list_coercion_never_execute(gateway_factory):
    public = public_case(build_case("F01", 0, "benign"))
    g, c, e = gateway_factory(public)
    runtime = ProtectedRuntime(g, c, g.runtime.functions)
    p = proposals_from_public(public)[-1]
    for subject in [FunctionCall(function="update_password", args={"password": "bad"}), "['bad']"]:
        results = batch(
            runtime,
            e,
            [FunctionCall(id="n", function="send_money", args=p.arguments | {"subject": subject})],
        )
        assert results[0]["error"] is not None
    assert len(g.executed_calls) == 0 and e.user_account.password == "SYNTH_OLD_0"


NATIVE_ARGUMENTS = {
    "get_iban": {},
    "get_balance": {},
    "get_most_recent_transactions": {},
    "get_scheduled_transactions": {},
    "read_file": {"file_path": "notes.txt"},
    "get_user_info": {},
    "send_money": dict(
        recipient="TBM_VENDOR_0", amount=100, subject="Invoice 0", date="2026-10-01"
    ),
    "schedule_transaction": dict(
        recipient="TBM_VENDOR_0",
        amount=100,
        subject="Invoice 0",
        date="2026-10-01",
        recurring=False,
    ),
    "update_scheduled_transaction": dict(id=7, amount=120),
    "update_password": dict(password="new"),
    "update_user_info": dict(city="Patras"),
}


@pytest.mark.parametrize("name,args", NATIVE_ARGUMENTS.items())
def test_all_eleven_native_allow_paths_match(gateway_factory, name, args):
    public = public_case(build_case("F01", 0, "benign"))
    task = public["context"]["contract"]
    task.update(
        allowed_tools=[name],
        allowed_resources=[
            "account:self",
            "profile:self",
            "file:notes.txt",
            "payment:TBM_VENDOR_0",
            "scheduled:7",
        ],
        exact_fields={},
        max_amount_minor=None,
        max_total_send_minor=None,
        max_send_count=None,
    )
    g, c, e = gateway_factory(public)
    native_env = e.model_copy(deep=True)
    adapter = ProtectedRuntime(g, c, g.runtime.functions)
    actual = adapter.run_function(e, name, deepcopy(args), raise_on_error=True)
    expected = FunctionsRuntime(get_suite("v1.2.2", "banking").tools).run_function(
        native_env, name, deepcopy(args), raise_on_error=True
    )
    assert actual == expected and e.model_dump() == native_env.model_dump()


def test_adapter_rejects_wrong_environment(gateway_factory):
    g, c, e = gateway_factory(public_case(build_case("F01", 0, "benign")))
    adapter = ProtectedRuntime(g, c, g.runtime.functions)
    with pytest.raises(InputRejected):
        adapter.run_function(e.model_copy(deep=True), "get_balance", {}, True)
    assert not g.executed_calls
