"""Host authority and agent proposals have separate input contracts."""

import re
from dataclasses import dataclass, field
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from tbm.registry import TOOL_POLICIES

JsonScalar = str | int | float | bool | None
Nonempty = Annotated[str, Field(min_length=1, strict=True)]
Limit = Annotated[int, Field(ge=0, strict=True)]
Decision = Literal["allow", "shadow", "approve", "block"]
ExecutionStatus = Literal["not_executed", "succeeded", "tool_error", "audit_incomplete"]


class InputRejected(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ConfigurationError(ValueError):
    pass


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Proposal(ContractModel):
    request_id: Annotated[str, Field(min_length=1, max_length=128, strict=True)]
    tool_name: Nonempty
    arguments: dict[str, JsonValue]


class TaskContract(ContractModel):
    allowed_tools: frozenset[str]
    allowed_resources: frozenset[str]
    exact_fields: dict[str, JsonScalar]
    max_amount_minor: Limit | None = None
    max_total_send_minor: Limit | None = None
    max_send_count: Limit | None = None
    unresolved_fields: frozenset[str] = frozenset()
    approval_required: bool = False
    authority_basis: Literal["trusted_user_input", "trusted_fixture_policy", "unresolved"]

    @model_validator(mode="after")
    def validate_policy_shape(self):
        if not self.allowed_tools or not self.allowed_tools <= TOOL_POLICIES.keys():
            raise ConfigurationError("CONTRACT_TOOL_INVALID")
        for resource in self.allowed_resources:
            if "*" in resource or not re.fullmatch(
                r"(account:self|profile:self|file:.+|payment:.+|scheduled:[0-9]+)", resource
            ):
                raise ConfigurationError("CONTRACT_RESOURCE_INVALID")
        writers = [TOOL_POLICIES[t] for t in self.allowed_tools if TOOL_POLICIES[t].is_write]
        if len({p.effect_field_names for p in writers}) > 1:
            raise ConfigurationError("CONTRACT_MIXED_WRITES")
        fields = frozenset().union(*(p.effect_field_names for p in writers))
        if not self.exact_fields.keys() <= fields or not self.unresolved_fields <= fields:
            raise ConfigurationError("CONTRACT_FIELD_INVALID")
        if self.unresolved_fields & self.exact_fields.keys():
            raise ConfigurationError("CONTRACT_AUTHORITY_CONFLICT")
        if self.unresolved_fields and self.authority_basis != "unresolved":
            raise ConfigurationError("CONTRACT_AUTHORITY_INVALID")
        return self


class TrustedContext(ContractModel):
    principal_id: Nonempty
    agent_id: Nonempty
    task_run_id: Nonempty
    session_id: Nonempty
    task_class: Nonempty
    policy_version: Nonempty
    grant_version: Nonempty
    granted_scopes: frozenset[str]
    contract: TaskContract


class NormalizedCall(ContractModel):
    tool_name: str
    arguments: dict[str, JsonValue]
    canonical_bytes: bytes


class Effect(ContractModel):
    tool_name: str
    resource_ids: tuple[str, ...]
    fields: dict[str, JsonScalar]
    changes: dict[str, JsonScalar]
    amount_minor: int | None
    is_write: bool


class PolicyVerdict(ContractModel):
    decision: Decision
    reason_codes: tuple[str, ...]
    authorized: bool | None


class ExecutionResult(ContractModel):
    request_id: str
    event_id: str
    decision: Decision
    reason_codes: tuple[str, ...]
    execution_status: ExecutionStatus
    value: object | None = None
    error_code: str | None = None
    pending_id: str | None = None
    state_changed: bool = False


class Approval(ContractModel):
    approval_id: str
    pending_id: str
    principal_id: str
    agent_id: str
    task_run_id: str
    session_id: str
    request_id: str
    tool_name: str
    argument_fingerprint: str
    effect_fingerprint: str
    policy_version: str
    grant_version: str
    state_version: int
    snapshot_fingerprint: str
    expires_ns: int


@dataclass
class SessionState:
    seen_request_ids: dict[str, str] = field(default_factory=dict)
    send_count: int = 0
    sent_total_minor: int = 0
    sequence_position: int = 0
    state_version: int = 0
    halted: bool = False
    active_pending_id: str | None = None
    observed_sources: list[dict] = field(default_factory=list)
    pending: dict = field(default_factory=dict)
    approvals: dict[str, Approval] = field(default_factory=dict)
    consumed_approval_ids: set[str] = field(default_factory=set)
