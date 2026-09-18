import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from tbm.cases import build_case, proposals_from_public, public_case
from tbm.contracts import Proposal


def setup(factory, family="F01", variant="benign", **kwargs):
    public = public_case(build_case(family, 0, variant))
    g, c, e = factory(public, **kwargs)
    return g, c, e, proposals_from_public(public)[-1]


@pytest.mark.parametrize(
    "variant,shadow,decision,count",
    [("benign", False, "allow", 1), ("benign", True, "shadow", 1), ("attack", False, "block", 0)],
)
def test_execution_admission(gateway_factory, monkeypatch, variant, shadow, decision, count):
    g, c, e, p = setup(gateway_factory, variant=variant, shadow_allowed=shadow)
    original = g.runtime.run_function
    calls = []

    def spy(*a, **k):
        calls.append((a, k))
        return original(*a, **k)

    monkeypatch.setattr(g.runtime, "run_function", spy)
    r = g.submit(p, c)
    assert r.decision == decision and len(calls) == count
    assert len(e.bank_account.transactions) == 1 + count
    events = [json.loads(line) for line in g.audit.path.read_text().splitlines()]
    assert [x["event_type"] for x in events] == ["decision", "outcome"]
    assert events[0]["gateway_duration_ns"] is None


def test_replay_conflict_and_fresh_id(gateway_factory):
    g, c, e, p = setup(gateway_factory, "F06")
    assert g.submit(p, c).execution_status == "succeeded"
    assert g.submit(p, c).reason_codes == ("REQUEST_REPLAY",)
    changed = p.model_copy(update={"arguments": p.arguments | {"amount": 50}})
    assert g.submit(changed, c).reason_codes == ("REQUEST_ID_CONFLICT",)
    assert g.submit(p.model_copy(update={"request_id": "fresh"}), c).execution_status == "succeeded"
    assert len(e.bank_account.transactions) == 3


def test_context_cannot_switch(gateway_factory):
    g, c, e, p = setup(gateway_factory)
    assert (
        g.submit(
            Proposal(
                request_id="read", tool_name="read_file", arguments={"file_path": "notes.txt"}
            ),
            c,
        ).execution_status
        == "succeeded"
    )
    assert g.submit(p, c.model_copy(update={"principal_id": "intruder"})).reason_codes == (
        "CONTEXT_INVALID",
    )
    assert len(e.bank_account.transactions) == 1


@pytest.mark.parametrize(
    "fail_at,status,effects", [(1, "not_executed", 0), (2, "audit_incomplete", 1)]
)
def test_audit_failure_tracks_actual_effect(gateway_factory, monkeypatch, fail_at, status, effects):
    g, c, e, p = setup(gateway_factory)
    original = g.audit.append
    calls = []

    def append(event):
        calls.append(event)
        if len(calls) == fail_at:
            raise OSError("synthetic failure")
        original(event)

    monkeypatch.setattr(g.audit, "append", append)
    r = g.submit(p, c)
    assert r.execution_status == status and g.state.halted
    assert len(e.bank_account.transactions) == 1 + effects
    assert r.state_changed == bool(effects)
    assert (
        g.submit(p.model_copy(update={"request_id": "retry"}), c).execution_status == "not_executed"
    )


def test_native_partial_mutation_then_error_is_not_prevention(gateway_factory, monkeypatch):
    g, c, e, p = setup(gateway_factory)
    native = g.runtime.run_function

    def broken(*a, **k):
        native(*a, **k)
        raise RuntimeError("sensitive native text")

    monkeypatch.setattr(g.runtime, "run_function", broken)
    r = g.submit(p, c)
    assert r.execution_status == "tool_error" and r.state_changed and g.state.halted
    assert len(e.bank_account.transactions) == 2
    assert "sensitive native text" not in g.audit.path.read_text()


def test_shared_budget_check_and_execution_are_serialized(gateway_factory):
    g, c, e, p = setup(gateway_factory, "F06")
    c = c.model_copy(
        update={"contract": c.contract.model_copy(update={"max_total_send_minor": 10000})}
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda i: g.submit(p.model_copy(update={"request_id": str(i)}), c), range(2))
        )
    assert sum(r.execution_status == "succeeded" for r in results) == 1
    assert sum(r.reason_codes == ("TASK_BUDGET_EXCEEDED",) for r in results) == 1
    assert len(e.bank_account.transactions) == 2


def test_malicious_request_id_tool_and_body_do_not_leak(gateway_factory):
    g, c, e, p = setup(gateway_factory)
    r = g.submit(Proposal(request_id="SYNTH_OLD_0", tool_name="SYNTH_OLD_0", arguments={}), c)
    assert r.execution_status == "not_executed"
    assert "SYNTH_OLD_0" not in g.audit.path.read_text()


@pytest.mark.parametrize("fail_at,executed", [(1, False), (2, False), (3, False), (4, True)])
def test_clock_failure_never_leaves_gateway_running(gateway_factory, fail_at, executed):
    calls = [0]

    def clock():
        calls[0] += 1
        if calls[0] == fail_at:
            raise RuntimeError("timing failed")
        return calls[0] * 100

    g, c, e, p = setup(gateway_factory, clock_ns=clock)
    r = g.submit(p, c)
    assert g.state.halted and r.error_code == "GATEWAY_INTERNAL_ERROR"
    assert r.execution_status == ("tool_error" if executed else "not_executed")
    assert len(e.bank_account.transactions) == (2 if executed else 1)
    assert r.state_changed is executed
    assert len(g.executed_calls) == (1 if executed else 0)
    assert (
        g.submit(p.model_copy(update={"request_id": "retry"}), c).execution_status == "not_executed"
    )
