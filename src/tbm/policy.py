"""Deterministic policy over trusted authority and a resolved effect."""

from tbm.contracts import ConfigurationError, Effect, PolicyVerdict, TrustedContext
from tbm.registry import TOOL_POLICIES


def _verdict(decision, reason, authorized):
    return PolicyVerdict(decision=decision, reason_codes=(reason,), authorized=authorized)


def evaluate_policy(
    context: TrustedContext,
    effect: Effect,
    send_count: int,
    sent_total_minor: int,
    mode: str,
    approval_satisfies: bool = False,
    shadow_allowed: bool = False,
) -> PolicyVerdict:
    if mode not in ("none", "scopes", "hard"):
        raise ConfigurationError("MODE_INVALID")
    if (
        mode != "none"
        and TOOL_POLICIES[effect.tool_name].required_scope not in context.granted_scopes
    ):
        return _verdict("block", "SCOPE_MISSING", False)
    if mode == "hard":
        task = context.contract
        if effect.tool_name not in task.allowed_tools:
            return _verdict("block", "TASK_TOOL_FORBIDDEN", False)
        for resource in effect.resource_ids:
            deferred = resource.startswith("payment:") and "recipient" in task.unresolved_fields
            if resource not in task.allowed_resources and not deferred:
                return _verdict("block", "TASK_RESOURCE_FORBIDDEN", False)
        if effect.is_write:
            for field, expected in task.exact_fields.items():
                if field in effect.fields and effect.fields[field] != expected:
                    return _verdict("block", "TASK_FIELD_MISMATCH", False)
            if (
                effect.amount_minor is not None
                and task.max_amount_minor is not None
                and effect.amount_minor > task.max_amount_minor
            ):
                return _verdict("block", "TASK_AMOUNT_EXCEEDED", False)
            if effect.tool_name == "send_money":
                if task.max_send_count is not None and send_count + 1 > task.max_send_count:
                    return _verdict("block", "TASK_COUNT_EXCEEDED", False)
                if (
                    task.max_total_send_minor is not None
                    and sent_total_minor + effect.amount_minor > task.max_total_send_minor
                ):
                    return _verdict("block", "TASK_BUDGET_EXCEEDED", False)
            if task.unresolved_fields & effect.fields.keys() and not approval_satisfies:
                return _verdict("approve", "AUTHORITY_UNRESOLVED", None)
            if task.approval_required and not approval_satisfies:
                return _verdict("approve", "APPROVAL_REQUIRED", None)
    return _verdict(
        "shadow" if shadow_allowed else "allow",
        "OBSERVE_ALLOWED" if shadow_allowed else "POLICY_ALLOW",
        None if mode == "none" else True,
    )
