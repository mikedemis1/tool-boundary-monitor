"""Predict the pinned native effect from a snapshot, without tool execution."""

from copy import deepcopy

from tbm.contracts import Effect, InputRejected, NormalizedCall
from tbm.normalize import amount_to_minor
from tbm.registry import TOOL_POLICIES


def resolve_effect(call: NormalizedCall, snapshot: dict) -> Effect:
    name, args = call.tool_name, call.arguments
    policy = TOOL_POLICIES[name]
    fields, changes = {}, {}
    resources = ("account:self",)
    if name == "read_file":
        resources = (f"file:{args['file_path']}",)
    elif name == "get_user_info":
        resources = ("profile:self",)
        fields = {k: snapshot["user_account"][k] for k in policy.effect_field_names}
    elif name in ("send_money", "schedule_transaction"):
        fields = deepcopy(args)
        fields.setdefault("recurring", False)
        changes = deepcopy(fields)
        resources = (f"payment:{fields['recipient']}",)
    elif name == "update_scheduled_transaction":
        old = next(
            (
                t
                for t in snapshot["bank_account"]["scheduled_transactions"]
                if t["id"] == args["id"]
            ),
            None,
        )
        if old is None:
            raise InputRejected("RESOURCE_NOT_FOUND")
        fields = {k: args.get(k) or old[k] for k in policy.effect_field_names}
        changes = {k: v for k, v in fields.items() if old[k] != v}
        resources = (f"scheduled:{args['id']}", f"payment:{fields['recipient']}")
    elif name in ("update_password", "update_user_info"):
        old = snapshot["user_account"]
        fields = (
            {"password": args["password"]}
            if name == "update_password"
            else {k: args.get(k) or old[k] for k in policy.effect_field_names}
        )
        changes = {k: v for k, v in fields.items() if old[k] != v}
        resources = ("profile:self",)
    amount = amount_to_minor(fields["amount"]) if "amount" in fields else None
    return Effect(
        tool_name=name,
        resource_ids=resources,
        fields=fields,
        changes=changes,
        amount_minor=amount,
        is_write=policy.is_write,
    )
