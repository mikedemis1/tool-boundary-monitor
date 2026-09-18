"""Serialized local execution boundary, with exact single-use host approvals."""

import secrets
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from time import perf_counter_ns

from pydantic import ValidationError

from tbm.audit import AuditWriter, redact_event
from tbm.contracts import (
    Approval,
    ConfigurationError,
    ExecutionResult,
    InputRejected,
    PolicyVerdict,
    Proposal,
    SessionState,
    TrustedContext,
)
from tbm.effects import resolve_effect
from tbm.normalize import amount_to_minor, canonical, fingerprint, normalize
from tbm.policy import evaluate_policy
from tbm.registry import TOOL_POLICIES

# All environments are serialized in this small single-process harness. This is
# stronger than an environment-specific lock and also covers shared environments.
_ENVIRONMENT_LOCK = RLock()


@dataclass(frozen=True)
class Pending:
    proposal_bytes: bytes
    context_bytes: bytes
    argument_fingerprint: str
    effect_fingerprint: str
    snapshot_fingerprint: str
    state_version: int


def _context_bytes(context: TrustedContext) -> bytes:
    obj = context.model_dump(mode="json")
    obj["granted_scopes"] = sorted(obj["granted_scopes"])
    for field in ("allowed_tools", "allowed_resources", "unresolved_fields"):
        obj["contract"][field] = sorted(obj["contract"][field])
    return canonical(obj)


def _identity(context):
    return tuple(
        getattr(context, k) for k in ("principal_id", "agent_id", "task_run_id", "session_id")
    )


class Gateway:
    def __init__(
        self,
        runtime,
        env,
        audit: AuditWriter,
        key: bytes,
        clock_ns: Callable[[], int] = perf_counter_ns,
        mode: str = "hard",
        shadow_allowed: bool = False,
    ):
        if mode not in ("none", "scopes", "hard") or mode != audit.context.configuration:
            raise ConfigurationError("MODE_INVALID")
        self.runtime, self.env, self.audit = runtime, env, audit
        self.key, self.clock_ns, self.mode, self.shadow_allowed = (
            key,
            clock_ns,
            mode,
            shadow_allowed,
        )
        self.state = SessionState()
        self._binding = None
        self._lock = _ENVIRONMENT_LOCK
        self.executed_calls = []  # Trusted evaluator traces; never exposed through tools.

    def _snapshot_hash(self):
        return fingerprint(self.key, canonical(self.env.model_dump()))

    def submit(self, proposal: Proposal, context: TrustedContext) -> ExecutionResult:
        with self._lock:
            return self._dispatch(proposal, context)

    def _dispatch(
        self, proposal, context, *, pending_id=None, approval_id=None, forced_reason=None
    ):
        try:
            started = self.clock_ns()
        except Exception:
            started = None
            self.state.halted = True
            forced_reason = "GATEWAY_INTERNAL_ERROR"
        event_id = secrets.token_hex(16)
        call = effect = None
        verdict = None
        error_code = "GATEWAY_INTERNAL_ERROR" if started is None else None
        request_id = getattr(proposal, "request_id", "invalid")
        if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
            request_id = "invalid"
        tool_name = getattr(proposal, "tool_name", "__invalid__")
        self.state.sequence_position += 1
        try:
            # Revalidate even when a trusted caller used Pydantic model_copy.
            context = TrustedContext.model_validate(context.model_dump())
            if self._binding is None:
                self._binding = _identity(context)
            if _identity(context) != self._binding:
                raise InputRejected("CONTEXT_INVALID")
            if forced_reason:
                raise InputRejected(forced_reason)
            if self.state.halted:
                raise InputRejected("EPISODE_HALTED")
            if self.state.active_pending_id is not None and pending_id is None:
                raise InputRejected("APPROVAL_PENDING")
            # Reject native objects before a schema can coerce them into JSON.
            if any(
                v is not None and type(v) not in (str, int, float, bool)
                for v in proposal.arguments.values()
            ):
                raise InputRejected("NESTED_CALL_REJECTED")
            proposal = Proposal.model_validate(proposal.model_dump())
            call = normalize(proposal, self.runtime.functions)
            arg_hash = fingerprint(self.key, call.canonical_bytes)
            if self.mode == "hard" and pending_id is None:
                prior = self.state.seen_request_ids.get(proposal.request_id)
                if prior is not None:
                    raise InputRejected(
                        "REQUEST_REPLAY" if prior == arg_hash else "REQUEST_ID_CONFLICT"
                    )
                self.state.seen_request_ids[proposal.request_id] = arg_hash
            effect = resolve_effect(call, self.env.model_dump())
            verdict = evaluate_policy(
                context,
                effect,
                self.state.send_count,
                self.state.sent_total_minor,
                self.mode,
                approval_satisfies=approval_id is not None,
                shadow_allowed=self.shadow_allowed,
            )
            if verdict.decision == "approve":
                pending_id = secrets.token_hex(24)
                stored = Proposal(
                    request_id=request_id, tool_name=call.tool_name, arguments=call.arguments
                )
                self.state.pending[pending_id] = Pending(
                    canonical(stored.model_dump()),
                    _context_bytes(context),
                    arg_hash,
                    fingerprint(self.key, canonical(effect.model_dump())),
                    self._snapshot_hash(),
                    self.state.state_version,
                )
                self.state.active_pending_id = pending_id
        except InputRejected as exc:
            verdict = PolicyVerdict(decision="block", reason_codes=(exc.code,), authorized=False)
        except ValidationError:
            verdict = PolicyVerdict(
                decision="block", reason_codes=("PROPOSAL_INVALID",), authorized=False
            )
        except Exception:
            self.state.halted = True
            verdict = PolicyVerdict(
                decision="block", reason_codes=("GATEWAY_INTERNAL_ERROR",), authorized=False
            )
            error_code = "GATEWAY_INTERNAL_ERROR"
        result = ExecutionResult(
            request_id=request_id,
            event_id=event_id,
            decision=verdict.decision,
            reason_codes=verdict.reason_codes,
            execution_status="not_executed",
            error_code=error_code,
            pending_id=pending_id,
        )
        event = self._event(result, context, tool_name, call, effect, verdict.authorized)
        try:
            self.audit.append(redact_event(event, self.key))
        except Exception:
            self.state.halted = True
            return result.model_copy(
                update=dict(
                    decision="block",
                    reason_codes=("AUDIT_UNAVAILABLE",),
                    error_code="AUDIT_WRITE_FAILED",
                )
            )
        try:
            gateway_ns = max(0, self.clock_ns() - started) if started is not None else None
        except Exception:
            self.state.halted = True
            gateway_ns = None
            result = result.model_copy(update={"error_code": "GATEWAY_INTERNAL_ERROR"})
        tool_ns = None
        if verdict.decision in ("allow", "shadow") and not self.state.halted:
            if approval_id is not None:
                self.state.consumed_approval_ids.add(approval_id)
                self.state.active_pending_id = None
                self.state.pending.pop(pending_id, None)
            result, tool_ns = self._invoke(result, call, effect)
        event.update(
            event_type="outcome",
            execution_status=result.execution_status,
            error_code=result.error_code,
            gateway_duration_ns=gateway_ns,
            tool_duration_ns=tool_ns,
            state_version=self.state.state_version,
        )
        try:
            self.audit.append(redact_event(event, self.key))
        except Exception:
            self.state.halted = True
            if result.execution_status != "not_executed":
                return result.model_copy(
                    update=dict(
                        execution_status="audit_incomplete", error_code="AUDIT_WRITE_FAILED"
                    )
                )
            return result.model_copy(
                update=dict(
                    decision="block",
                    reason_codes=("AUDIT_UNAVAILABLE",),
                    error_code="AUDIT_WRITE_FAILED",
                )
            )
        if result.execution_status == "succeeded":
            self.state.observed_sources.append(
                dict(
                    kind="tool_result",
                    tool_name=tool_name,
                    event_id=event_id,
                    trust="untrusted_content",
                )
            )
        return result

    def _invoke(self, result, call, effect):
        before = after = None
        native_invoked = False
        tool_ns = None
        changed = False
        value, error = None, None
        try:
            before = deepcopy(self.env.model_dump())
            started = self.clock_ns()
            native_args = deepcopy(call.arguments)
            native_invoked = True
            try:
                value, native_error = self.runtime.run_function(
                    self.env, call.tool_name, native_args, raise_on_error=False
                )
                if native_error is not None:
                    error = "TOOL_EXECUTION_FAILED"
            except Exception:
                error = "TOOL_EXECUTION_FAILED"
            tool_ns = max(0, self.clock_ns() - started)
            after = deepcopy(self.env.model_dump())
            changed = before != after
            if changed:
                self.state.state_version += 1
            if not effect.is_write and changed:
                error = "PROVIDER_CONTRACT_FAILED"
            if not error and call.tool_name == "send_money":
                new = after["bank_account"]["transactions"][
                    len(before["bank_account"]["transactions"]) :
                ]
                total = sum(amount_to_minor(t["amount"]) for t in new)
                self.state.send_count += len(new)
                self.state.sent_total_minor += total
        except Exception:
            error = "GATEWAY_INTERNAL_ERROR"
            if native_invoked and after is None:
                # Preserve actual state even if timing/accounting failed after
                # the tool. Never retry the native invocation to recover it.
                try:
                    after = deepcopy(self.env.model_dump())
                    changed = before != after
                    if changed:
                        self.state.state_version += 1
                except Exception:
                    # A missing snapshot remains an explicit invalid evaluator
                    # trace; verification rejects it rather than assuming safety.
                    after = None
        if error:
            self.state.halted = True
        if native_invoked:
            self.executed_calls.append(
                dict(
                    tool_name=call.tool_name,
                    result=value,
                    error_code=error,
                    before=before,
                    after=after,
                )
            )
        status = ("tool_error" if error else "succeeded") if native_invoked else "not_executed"
        return result.model_copy(
            update=dict(
                value=value, error_code=error, state_changed=changed, execution_status=status
            )
        ), tool_ns

    def _event(self, result, context, tool_name, call, effect, authorized):
        metadata = TOOL_POLICIES.get(tool_name)
        return dict(
            schema_version="tbm.m1.v1",
            event_type="decision",
            event_id=result.event_id,
            request_id=result.request_id,
            pending_id=result.pending_id,
            **self.audit.context.model_dump(),
            **{
                k: getattr(context, k)
                for k in (
                    "principal_id",
                    "agent_id",
                    "task_run_id",
                    "session_id",
                    "task_class",
                    "policy_version",
                    "grant_version",
                )
            },
            sequence_position=self.state.sequence_position,
            state_version=self.state.state_version,
            tool_name=tool_name,
            tool_risk="write" if metadata and metadata.is_write else "read",
            required_scopes=[metadata.required_scope] if metadata else [],
            granted_scopes=sorted(context.granted_scopes),
            arguments=call.arguments if call else None,
            effect=effect.model_dump() if effect else None,
            resource_ids=list(effect.resource_ids) if effect else [],
            observed_sources=deepcopy(self.state.observed_sources),
            causal_influence="unknown",
            decision=result.decision,
            reason_codes=list(result.reason_codes),
            checked_layers={
                "none": [],
                "scopes": ["scope"],
                "hard": ["scope", "task", "replay", "approval"],
            }[self.mode],
            authorized=authorized,
            execution_status="not_executed",
            gateway_duration_ns=None,
            tool_duration_ns=None,
            rate_score=None,
            sequence_score=None,
            detector_status="not_evaluated",
            error_code=result.error_code,
        )

    def issue_approval(
        self, pending_id: str, context: TrustedContext, ttl_seconds: int = 60
    ) -> str:
        with self._lock:
            item = self.state.pending.get(pending_id)
            if (
                item is None
                or pending_id != self.state.active_pending_id
                or self.state.halted
                or _context_bytes(context) != item.context_bytes
                or ttl_seconds <= 0
            ):
                raise InputRejected("APPROVAL_INVALID")
            proposal = Proposal.model_validate_json(item.proposal_bytes)
            aid = secrets.token_hex(24)
            self.state.approvals[aid] = Approval(
                approval_id=aid,
                pending_id=pending_id,
                **{
                    k: getattr(context, k)
                    for k in (
                        "principal_id",
                        "agent_id",
                        "task_run_id",
                        "session_id",
                        "policy_version",
                        "grant_version",
                    )
                },
                request_id=proposal.request_id,
                tool_name=proposal.tool_name,
                argument_fingerprint=item.argument_fingerprint,
                effect_fingerprint=item.effect_fingerprint,
                state_version=item.state_version,
                snapshot_fingerprint=item.snapshot_fingerprint,
                expires_ns=self.clock_ns() + ttl_seconds * 1_000_000_000,
            )
            return aid

    def resume(self, pending_id: str, approval_id: str, context: TrustedContext) -> ExecutionResult:
        with self._lock:
            item = self.state.pending.get(pending_id)
            approval = self.state.approvals.get(approval_id)
            reason = None
            proposal = Proposal(
                request_id="invalid-approval", tool_name="get_balance", arguments={}
            )
            if item is not None:
                proposal = Proposal.model_validate_json(item.proposal_bytes)
            if approval_id in self.state.consumed_approval_ids:
                reason = "APPROVAL_USED"
            elif (
                item is None
                or approval is None
                or approval.pending_id != pending_id
                or self.state.active_pending_id != pending_id
            ):
                reason = "APPROVAL_INVALID"
            elif self.clock_ns() >= approval.expires_ns:
                reason = "APPROVAL_EXPIRED"
            elif _context_bytes(context) != item.context_bytes:
                reason = "APPROVAL_INVALID"
            elif (
                self.state.state_version != item.state_version
                or self._snapshot_hash() != item.snapshot_fingerprint
            ):
                reason = "APPROVAL_STALE"
            else:
                try:
                    call = normalize(proposal, self.runtime.functions)
                    effect = resolve_effect(call, self.env.model_dump())
                    if (
                        fingerprint(self.key, call.canonical_bytes) != approval.argument_fingerprint
                        or fingerprint(self.key, canonical(effect.model_dump()))
                        != approval.effect_fingerprint
                    ):
                        reason = "APPROVAL_STALE"
                except InputRejected:
                    reason = "APPROVAL_STALE"
            return self._dispatch(
                proposal,
                context,
                pending_id=pending_id,
                approval_id=approval_id if reason is None else None,
                forced_reason=reason,
            )

    def reject(self, pending_id: str, context: TrustedContext) -> ExecutionResult:
        with self._lock:
            item = self.state.pending.get(pending_id)
            if item is None or _identity(context) != self._binding:
                return self._dispatch(
                    Proposal(request_id="invalid-rejection", tool_name="get_balance", arguments={}),
                    context,
                    pending_id=pending_id,
                    forced_reason="APPROVAL_INVALID",
                )
            proposal = Proposal.model_validate_json(item.proposal_bytes)
            self.state.pending.pop(pending_id)
            if self.state.active_pending_id == pending_id:
                self.state.active_pending_id = None
            return self._dispatch(
                proposal, context, pending_id=pending_id, forced_reason="APPROVAL_REJECTED"
            )
