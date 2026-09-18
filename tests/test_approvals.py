import pytest

from tbm.cases import build_case, proposals_from_public, public_case
from tbm.contracts import Proposal


def pending(factory, **options):
    public = public_case(build_case("U01", 0, "benign"))
    g, c, e = factory(public, **options)
    p = proposals_from_public(public)[-1]
    r = g.submit(p, c)
    assert r.decision == "approve" and len(e.bank_account.transactions) == 1
    return g, c, e, p, r.pending_id


def test_approval_executes_once_and_pauses_other_calls(gateway_factory):
    g, c, e, p, pid = pending(gateway_factory)
    read = Proposal(
        request_id="read", tool_name="read_file", arguments={"file_path": "invoice.txt"}
    )
    assert g.submit(read, c).reason_codes == ("APPROVAL_PENDING",)
    aid = g.issue_approval(pid, c)
    assert g.resume(pid, aid, c).execution_status == "succeeded"
    assert g.resume(pid, aid, c).execution_status == "not_executed"
    assert g.submit(p, c).reason_codes == ("REQUEST_REPLAY",)
    assert g.submit(read, c).execution_status == "succeeded"
    assert len(e.bank_account.transactions) == 2


@pytest.mark.parametrize(
    "change",
    [
        "principal_id",
        "agent_id",
        "task_run_id",
        "session_id",
        "policy_version",
        "grant_version",
        "scope",
        "state",
        "amount",
    ],
)
def test_mismatched_approval_never_executes(gateway_factory, change):
    g, c, e, p, pid = pending(gateway_factory)
    aid = g.issue_approval(pid, c)
    if change == "scope":
        c = c.model_copy(update={"granted_scopes": frozenset()})
    elif change == "state":
        e.bank_account.balance += 1
    elif change == "amount":
        p.arguments["amount"] = 50
        assert g.submit(p, c).reason_codes == ("APPROVAL_PENDING",)
        # Pending action retains the original immutable proposal.
        assert g.resume(pid, aid, c).execution_status == "succeeded"
        assert e.bank_account.transactions[-1].amount == 100
        return
    else:
        c = c.model_copy(update={change: "changed"})
    assert g.resume(pid, aid, c).execution_status == "not_executed"
    assert len(e.bank_account.transactions) == 1
    assert g.state.active_pending_id == pid


def test_expiry_and_rejection(gateway_factory):
    now = [0]
    g, c, e, p, pid = pending(gateway_factory, clock_ns=lambda: now[0])
    aid = g.issue_approval(pid, c, ttl_seconds=1)
    now[0] = 1_000_000_000
    assert g.resume(pid, aid, c).reason_codes == ("APPROVAL_EXPIRED",)
    assert g.reject(pid, c).reason_codes == ("APPROVAL_REJECTED",)
    assert g.state.active_pending_id is None
    assert g.submit(p, c).reason_codes == ("REQUEST_REPLAY",)
    assert g.submit(p.model_copy(update={"request_id": "fresh"}), c).decision == "approve"
