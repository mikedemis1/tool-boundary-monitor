from copy import deepcopy

import pytest
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite

from tbm.cases import build_case, environment_from_public, public_case
from tbm.contracts import InputRejected, Proposal
from tbm.effects import resolve_effect
from tbm.normalize import normalize


@pytest.mark.parametrize(
    "tool,args",
    [
        ("send_money", dict(recipient="vendor", amount=5, subject="x", date="today")),
        (
            "schedule_transaction",
            dict(recipient="vendor", amount=5, subject="x", date="today", recurring=False),
        ),
        ("update_scheduled_transaction", dict(id=7, amount=120)),
        ("update_scheduled_transaction", dict(id=8, amount=0, subject="", recurring=False)),
        ("update_password", dict(password="new")),
        ("update_user_info", dict(city="Patras", street="")),
    ],
)
def test_prediction_matches_native_state_and_does_not_mutate(tool, args):
    env = environment_from_public(public_case(build_case("F04", 0, "benign")))
    before = env.model_dump()
    untouched = deepcopy(before)
    runtime = FunctionsRuntime(get_suite("v1.2.2", "banking").tools)
    call = normalize(Proposal(request_id="r", tool_name=tool, arguments=args), runtime.functions)
    effect = resolve_effect(call, before)
    assert before == untouched and env.model_dump() == before
    _, error = runtime.run_function(env, tool, call.arguments, raise_on_error=True)
    assert error is None
    if tool in ("send_money", "schedule_transaction"):
        key = "transactions" if tool == "send_money" else "scheduled_transactions"
        actual = env.model_dump()["bank_account"][key][-1]
        assert effect.changes == effect.fields
        assert env.bank_account.balance == 1000
    elif tool == "update_scheduled_transaction":
        actual = next(
            t
            for t in env.model_dump()["bank_account"]["scheduled_transactions"]
            if t["id"] == args["id"]
        )
        old = next(
            t for t in before["bank_account"]["scheduled_transactions"] if t["id"] == args["id"]
        )
        assert effect.changes == {k: v for k, v in effect.fields.items() if old[k] != v}
        assert f"payment:{actual['recipient']}" in effect.resource_ids
    else:
        actual = env.model_dump()["user_account"]
        assert effect.changes == {
            k: v for k, v in effect.fields.items() if before["user_account"][k] != v
        }
    assert effect.fields == {k: actual[k] for k in effect.fields}


def test_missing_scheduled_record_rejected():
    env = environment_from_public(public_case(build_case("F04", 0, "benign")))
    runtime = FunctionsRuntime(get_suite("v1.2.2", "banking").tools)
    call = normalize(
        Proposal(request_id="r", tool_name="update_scheduled_transaction", arguments={"id": 999}),
        runtime.functions,
    )
    with pytest.raises(InputRejected, match="RESOURCE_NOT_FOUND"):
        resolve_effect(call, env.model_dump())
