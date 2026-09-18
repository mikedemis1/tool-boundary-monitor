"""Metadata for the eleven pinned native banking tools."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPolicy:
    required_scope: str
    is_write: bool
    effect_field_names: frozenset[str]


PAYMENT_FIELDS = frozenset({"recipient", "amount", "subject", "date", "recurring"})
PROFILE_FIELDS = frozenset({"first_name", "last_name", "street", "city"})
TOOL_POLICIES = {
    name: ToolPolicy("bank:read", False, frozenset())
    for name in (
        "get_iban",
        "get_balance",
        "get_most_recent_transactions",
        "get_scheduled_transactions",
    )
}
TOOL_POLICIES.update(
    {
        "read_file": ToolPolicy("files:read", False, frozenset()),
        "get_user_info": ToolPolicy("profile:read", False, PROFILE_FIELDS),
        "send_money": ToolPolicy("payments:send", True, PAYMENT_FIELDS),
        "schedule_transaction": ToolPolicy("payments:schedule", True, PAYMENT_FIELDS),
        "update_scheduled_transaction": ToolPolicy("payments:update", True, PAYMENT_FIELDS),
        "update_password": ToolPolicy("profile:password", True, frozenset({"password"})),
        "update_user_info": ToolPolicy("profile:write", True, PROFILE_FIELDS),
    }
)
