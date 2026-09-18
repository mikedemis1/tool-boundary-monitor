import socket

import pytest


@pytest.fixture(autouse=True)
def forbid_test_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network access is forbidden in milestone-1 tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)


@pytest.fixture
def gateway_factory(tmp_path):
    from itertools import count

    from agentdojo.functions_runtime import FunctionsRuntime
    from agentdojo.task_suite.load_suites import get_suite

    from tbm.audit import AuditContext, AuditWriter
    from tbm.cases import context_from_public, environment_from_public
    from tbm.gateway import Gateway

    counter = count()

    def factory(public, mode="hard", shadow_allowed=False, clock_ns=None):
        env = environment_from_public(public)
        context = context_from_public(public)
        audit = AuditWriter(
            tmp_path / f"audit-{next(counter)}.jsonl",
            AuditContext(run_id="test", case_id="fixture", configuration=mode),
        )
        options = {} if clock_ns is None else {"clock_ns": clock_ns}
        gateway = Gateway(
            FunctionsRuntime(get_suite("v1.2.2", "banking").tools),
            env,
            audit,
            b"synthetic-test-key",
            mode=mode,
            shadow_allowed=shadow_allowed,
            **options,
        )
        return gateway, context, env

    return factory
