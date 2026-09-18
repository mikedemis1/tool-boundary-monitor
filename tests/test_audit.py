import json

import pytest

from tbm.audit import AuditContext, AuditWriter, redact_event


def internal_event():
    return dict(
        schema_version="tbm.m1.v1",
        event_type="decision",
        event_id="e1",
        request_id="SYNTH_OLD_0",
        pending_id=None,
        run_id="run",
        case_id="case",
        configuration="hard",
        principal_id="p",
        agent_id="a",
        task_run_id="t",
        session_id="s",
        task_class="payment",
        policy_version="p1",
        grant_version="g1",
        sequence_position=1,
        state_version=0,
        tool_name="send_money",
        tool_risk="write",
        required_scopes=["payments:send"],
        granted_scopes=["payments:send"],
        arguments={"recipient": "TBM_VENDOR_0", "subject": "SYNTH_OLD_0"},
        effect={"recipient": "TBM_VENDOR_0"},
        resource_ids=["payment:TBM_VENDOR_0"],
        observed_sources=[],
        causal_influence="unknown",
        decision="block",
        reason_codes=["TASK_RESOURCE_FORBIDDEN"],
        checked_layers=["scope", "task"],
        authorized=False,
        execution_status="not_executed",
        gateway_duration_ns=None,
        tool_duration_ns=None,
        rate_score=None,
        sequence_score=None,
        detector_status="not_evaluated",
        error_code=None,
    )


def test_redaction_and_unknown_tool_name(tmp_path):
    e = internal_event()
    e["tool_name"] = "SYNTH_OLD_0"
    path = tmp_path / "audit.jsonl"
    writer = AuditWriter(path, AuditContext(run_id="run", case_id="case", configuration="hard"))
    redacted = redact_event(e, b"test-key")
    writer.append(redacted)
    raw = path.read_text(encoding="utf-8")
    assert "SYNTH_OLD_0" not in raw and "TBM_VENDOR_0" not in raw
    record = json.loads(raw)
    assert record["tool_name"] == "__invalid__"
    assert len(record["argument_fingerprint"]) == 64
    assert record["sequence_score"] is None
    assert not {"arguments", "effect", "resource_ids"} & record.keys()
    with pytest.raises(ValueError):
        writer.append(redacted | {"arguments": "secret"})
    with pytest.raises(ValueError):
        redact_event(e | {"unreviewed": "secret"}, b"key")
    with pytest.raises(ValueError):
        writer.append(redacted | {"case_id": "different"})


def test_writer_does_not_swallow_io_failure(tmp_path, monkeypatch):
    from pathlib import Path

    writer = AuditWriter(
        tmp_path / "audit.jsonl", AuditContext(run_id="run", case_id="case", configuration="hard")
    )

    def fail(*args, **kwargs):
        raise OSError("disk failure")

    monkeypatch.setattr(Path, "open", fail)
    with pytest.raises(OSError):
        writer.append(redact_event(internal_event(), b"key"))
