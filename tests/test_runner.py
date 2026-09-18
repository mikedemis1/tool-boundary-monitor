import json
from pathlib import Path

import pytest

from tbm.__main__ import main
from tbm.cases import generate_cases, write_cases
from tbm.runner import run_matrix, safe_project_path, verify_run


def dataset(tmp_path):
    p = tmp_path / "cases.jsonl"
    write_cases(p, generate_cases())
    return p


def test_complete_native_matrix_and_denominators(tmp_path):
    root = tmp_path / "run"
    summary = run_matrix(dataset(tmp_path), ["none", "scopes", "hard"], root)
    assert not verify_run(root)
    assert summary["executions"] == 162
    assert summary["modes"]["none"]["attacker_goals"] == 27
    assert summary["modes"]["scopes"]["attacker_goals"] == 24
    assert summary["modes"]["hard"]["attacker_goals"] == 0
    assert summary["modes"]["hard"]["benign_successes"] == 24
    assert summary["modes"]["hard"]["benign_cases"] == 27
    assert summary["modes"]["hard"]["infrastructure_errors"] == 0
    assert summary["modes"]["hard"]["unauthorized_effects"] == 0
    assert (root / "hard" / "U01-s0-benign" / "result.json").exists()
    assert (
        json.loads((root / "hard" / "U01-s0-benign" / "result.json").read_text())[
            "approval_requests"
        ]
        == 1
    )
    with pytest.raises(FileExistsError):
        run_matrix(tmp_path / "cases.jsonl", ["hard"], root)


def test_verifier_reports_missing_case(tmp_path):
    root = tmp_path / "run"
    run_matrix(dataset(tmp_path), ["hard"], root)
    (root / "hard" / "F01-s0-benign" / "result.json").unlink()
    errors = verify_run(root)
    assert any("F01-s0-benign" in e for e in errors)


def test_error_case_is_retained_and_fails_verification(tmp_path, monkeypatch):
    import tbm.runner as runner

    original = runner.run_case
    count = [0]

    def broken(*args, **kwargs):
        count[0] += 1
        if count[0] == 1:
            raise RuntimeError("private details")
        return original(*args, **kwargs)

    monkeypatch.setattr(runner, "run_case", broken)
    root = tmp_path / "run"
    summary = run_matrix(dataset(tmp_path), ["hard"], root)
    assert summary["executions"] == 54
    assert summary["modes"]["hard"]["infrastructure_errors"] == 1
    errors = verify_run(root)
    assert any("F01-s0-attack" in e for e in errors)
    assert "private details" not in (root / "summary.json").read_text()


def test_cli_verification_returns_nonzero_for_errors(tmp_path, monkeypatch, capsys):
    import tbm.__main__ as cli

    root = tmp_path / "run"
    run_matrix(dataset(tmp_path), ["hard"], root)
    (root / "hard" / "F01-s0-benign" / "result.json").unlink()
    monkeypatch.setattr(cli, "safe_project_path", lambda p: Path(p))
    assert main(["verify", "--run", str(root)]) == 1
    assert "F01-s0-benign" in capsys.readouterr().out


def test_output_path_escape_rejected(tmp_path):
    with pytest.raises(ValueError):
        safe_project_path(tmp_path / "outside")
    with pytest.raises(ValueError):
        safe_project_path("runs/../bad")


def test_audit_tampering_fails_verification(tmp_path):
    root = tmp_path / "run"
    run_matrix(dataset(tmp_path), ["hard"], root)
    p = root / "hard" / "F01-s0-benign" / "audit.jsonl"
    p.write_text("", encoding="utf-8")
    assert any("F01-s0-benign" in e for e in verify_run(root))


def test_scoring_failure_retains_actual_execution_evidence(tmp_path, monkeypatch):
    import tbm.runner as runner
    from tbm.cases import build_case, public_case

    case = build_case("F01", 0, "benign")

    def failed(*args):
        raise RuntimeError("scorer failed")

    monkeypatch.setattr(runner, "evaluate_outcome", failed)
    directory = tmp_path / "run" / "none" / case["case_id"]
    result = runner.run_case(public_case(case), case["oracle"], "none", directory)
    assert result["infrastructure_error"]
    assert result["executed"] == 2 and result["attempted"] == 2
    trace = json.loads((directory / "synthetic-trace.json").read_text())
    assert len(trace["after"]["bank_account"]["transactions"]) == 2
    assert len(trace["executed_calls"]) == 2
