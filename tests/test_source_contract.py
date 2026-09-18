from importlib.metadata import version

import pytest
from agentdojo.agent_pipeline.ground_truth_pipeline import GroundTruthPipeline
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite


def test_pinned_banking_inventory():
    suite = get_suite("v1.2.2", "banking")
    assert version("agentdojo") == "0.1.35"
    assert len(suite.user_tasks) == 16
    assert len(suite.injection_tasks) == 9
    assert {tool.name for tool in suite.tools} == {
        "get_iban",
        "get_balance",
        "get_most_recent_transactions",
        "get_scheduled_transactions",
        "read_file",
        "get_user_info",
        "send_money",
        "schedule_transaction",
        "update_scheduled_transaction",
        "update_password",
        "update_user_info",
    }


def test_all_native_reference_traces_execute():
    suite = get_suite("v1.2.2", "banking")
    for task in suite.user_tasks.values():
        environment = suite.load_and_inject_default_environment({})
        _, _, _, responses, _ = GroundTruthPipeline(task).query(
            task.PROMPT, FunctionsRuntime(suite.tools), environment
        )
        assert responses
        assert not any(response.get("error") for response in responses)


@pytest.mark.parametrize("task_id,history", [(0, "spotify"), (1, "pizza"), (3, "iphone")])
def test_native_disclosure_scorer_accepts_unrelated_subject(task_id, history):
    from tbm.cases import build_case, environment_from_public, public_case

    suite = get_suite("v1.2.2", "banking")
    task = suite.injection_tasks[f"injection_task_{task_id}"]
    pre = environment_from_public(public_case(build_case("F01", 0, "benign")))
    pre.bank_account.transactions[0].subject = history
    post = pre.model_copy(deep=True)
    FunctionsRuntime(suite.tools).run_function(
        post,
        "send_money",
        dict(recipient=task._ATTACKER_IBAN, amount=0.01, subject="unrelated", date="2026-10-01"),
        raise_on_error=True,
    )
    assert task.security("", pre, post) is True


def test_native_scheduled_scorer_quirk():
    from tbm.cases import build_case, environment_from_public, public_case

    suite = get_suite("v1.2.2", "banking")
    task = suite.injection_tasks["injection_task_4"]
    pre = environment_from_public(public_case(build_case("F04", 0, "benign")))
    post = pre.model_copy(deep=True)
    FunctionsRuntime(suite.tools).run_function(
        post,
        "update_scheduled_transaction",
        dict(id=7, recipient=task._ATTACKER_IBAN),
        raise_on_error=True,
    )
    assert post.bank_account.scheduled_transactions[0].recipient == task._ATTACKER_IBAN
    assert task.security("", pre, post) is False
