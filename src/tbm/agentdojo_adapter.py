"""Native dispatcher interface. No model client or unprotected execution path."""

from copy import deepcopy
from itertools import count

from tbm.contracts import ConfigurationError, InputRejected, Proposal, TrustedContext
from tbm.gateway import Gateway
from tbm.registry import TOOL_POLICIES


class ProtectedRuntime:
    def __init__(self, gateway: Gateway, context: TrustedContext, functions: dict):
        if set(functions) != set(TOOL_POLICIES):
            raise ConfigurationError("REGISTRY_MISMATCH")
        self._gateway = gateway
        self._context = context.model_copy(deep=True)
        self.functions = dict(functions)
        self._requests = count()

    def run_function(self, env, function, kwargs, raise_on_error=False):
        if env is not self._gateway.env:
            if raise_on_error:
                raise InputRejected("ENVIRONMENT_MISMATCH")
            return "", "TBMBlocked:ENVIRONMENT_MISMATCH"
        # Preserve unsafe native argument objects until the gateway rejects them;
        # no native nested-call resolution is reached before that check.
        proposal = Proposal.model_construct(
            request_id=f"adapter-{next(self._requests)}",
            tool_name=function,
            arguments=deepcopy(kwargs),
        )
        result = self._gateway.submit(proposal, self._context)
        if result.execution_status == "succeeded":
            return result.value, None
        code = result.error_code or result.reason_codes[0]
        if raise_on_error:
            raise InputRejected(code)
        if result.decision == "approve":
            return "", f"TBMApprovalRequired:{result.pending_id}"
        return "", f"TBMBlocked:{code}"
