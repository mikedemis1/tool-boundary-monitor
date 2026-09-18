"""Strict, redacted local audit events. Flush is not crash-proof durability."""

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from tbm.contracts import ContractModel, Decision, ExecutionStatus
from tbm.normalize import canonical, fingerprint
from tbm.registry import TOOL_POLICIES


class AuditContext(ContractModel):
    run_id: str
    case_id: str
    configuration: Literal["none", "scopes", "hard"]


class SourceReference(ContractModel):
    kind: Literal["tool_result"]
    tool_name: str
    event_id: str
    trust: Literal["untrusted_content"]


class Event(ContractModel):
    schema_version: Literal["tbm.m1.v1"]
    event_type: Literal["decision", "outcome"]
    event_id: str
    request_id: str
    pending_id: str | None
    run_id: str
    case_id: str
    configuration: Literal["none", "scopes", "hard"]
    principal_id: str
    agent_id: str
    task_run_id: str
    session_id: str
    task_class: str
    policy_version: str
    grant_version: str
    sequence_position: int = Field(ge=0)
    state_version: int = Field(ge=0)
    tool_name: str
    tool_risk: Literal["read", "write"]
    required_scopes: list[str]
    granted_scopes: list[str]
    observed_sources: list[SourceReference]
    causal_influence: Literal["unknown"]
    decision: Decision
    reason_codes: list[str]
    checked_layers: list[str]
    authorized: bool | None
    execution_status: ExecutionStatus
    gateway_duration_ns: int | None = Field(ge=0)
    tool_duration_ns: int | None = Field(ge=0)
    rate_score: None
    sequence_score: None
    detector_status: Literal["not_evaluated"]
    error_code: str | None
    argument_fingerprint: str | None
    effect_fingerprint: str | None
    resource_fingerprints: list[str]

    @model_validator(mode="after")
    def consistent_event(self):
        if self.tool_name not in TOOL_POLICIES and self.tool_name != "__invalid__":
            raise ValueError("AUDIT_TOOL_INVALID")
        if self.event_type == "decision" and (
            self.gateway_duration_ns is not None
            or self.tool_duration_ns is not None
            or self.execution_status != "not_executed"
        ):
            raise ValueError("AUDIT_DECISION_INVALID")
        return self


def redact_event(internal_event: dict, key: bytes) -> dict:
    raw_fields = {"arguments", "effect", "resource_ids"}
    hashed_fields = {"argument_fingerprint", "effect_fingerprint", "resource_fingerprints"}
    expected = (Event.model_fields.keys() - hashed_fields) | raw_fields
    if internal_event.keys() != expected:
        raise ValueError("AUDIT_FIELDS_INVALID")
    event = {k: v for k, v in internal_event.items() if k not in raw_fields}
    for raw, target in [("arguments", "argument_fingerprint"), ("effect", "effect_fingerprint")]:
        event[target] = (
            fingerprint(key, canonical(internal_event[raw]))
            if internal_event[raw] is not None
            else None
        )
    event["resource_fingerprints"] = [
        fingerprint(key, canonical(r)) for r in internal_event["resource_ids"]
    ]
    for k in ("request_id", "principal_id", "agent_id", "task_run_id", "session_id"):
        event[k] = fingerprint(key, canonical(event[k]))
    if event["tool_name"] not in TOOL_POLICIES:
        event["tool_name"] = "__invalid__"
    return Event.model_validate(event).model_dump(mode="json")


class AuditWriter:
    def __init__(self, path: Path, context: AuditContext):
        self.path = Path(path)
        self.context = context
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise FileExistsError("AUDIT_EXISTS")

    def append(self, event: dict) -> None:
        validated = Event.model_validate(event)
        for field, value in self.context.model_dump().items():
            if getattr(validated, field) != value:
                raise ValueError("AUDIT_CONTEXT_MISMATCH")
        with self.path.open("ab") as stream:
            stream.write(canonical(validated.model_dump(mode="json")) + b"\n")
            stream.flush()
