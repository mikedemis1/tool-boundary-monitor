"""Local scripted matrix execution and artifact verification."""

import hashlib
import json
import platform
import secrets
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite
from pydantic import BaseModel

from tbm.audit import AuditContext, AuditWriter, Event
from tbm.cases import (
    context_from_public,
    environment_from_public,
    generate_cases,
    proposals_from_public,
    public_case,
)
from tbm.gateway import Gateway
from tbm.oracle import evaluate_outcome

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODES = ("none", "scopes", "hard")


def safe_project_path(value) -> Path:
    supplied = Path(value)
    if ".." in supplied.parts:
        raise ValueError("PATH_TRAVERSAL")
    path = (PROJECT_ROOT / supplied).resolve() if not supplied.is_absolute() else supplied.resolve()
    if path == PROJECT_ROOT or not path.is_relative_to(PROJECT_ROOT):
        raise ValueError("PATH_OUTSIDE_PROJECT")
    return path


def _json_default(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    raise TypeError("UNSUPPORTED_ARTIFACT_VALUE")


def _write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(
            json.dumps(
                value,
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
                default=_json_default,
            )
            + "\n"
        )


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_inventory():
    files = list(PROJECT_ROOT.glob("src/tbm/*.py")) + list(PROJECT_ROOT.glob("tests/*.py"))
    files += [
        PROJECT_ROOT / p
        for p in (
            "pyproject.toml",
            "requirements.in",
            "requirements.lock.txt",
            "scripts/injection_candidates.py",
        )
    ]
    return {p.relative_to(PROJECT_ROOT).as_posix(): _hash(p) for p in sorted(files)}


def _git(*args):
    result = subprocess.run(
        ["git", "-c", f"safe.directory={PROJECT_ROOT.as_posix()}", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def run_case(public: dict, oracle: dict, mode: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=False)
    env = environment_from_public(public)
    context = context_from_public(public)
    before = env.model_dump()
    audit = AuditWriter(
        output_dir / "audit.jsonl",
        AuditContext(
            run_id=output_dir.parent.parent.name, case_id=output_dir.name, configuration=mode
        ),
    )
    gateway = Gateway(
        FunctionsRuntime(get_suite("v1.2.2", "banking").tools),
        env,
        audit,
        secrets.token_bytes(32),
        mode=mode,
    )
    proposals = proposals_from_public(public)
    decisions = []
    for proposal in proposals:
        result = gateway.submit(proposal, context)
        decisions.append(result)
        if result.decision == "approve" or result.error_code or gateway.state.halted:
            break
    after = env.model_dump()
    infrastructure_error = any(r.error_code for r in decisions) or any(
        c["before"] is None or c["after"] is None for c in gateway.executed_calls
    )
    # Preserve the actual native trace before any fallible scorer/report step.
    _write(
        output_dir / "synthetic-trace.json",
        dict(
            data_class="synthetic_private",
            before=before,
            after=after,
            executed_calls=gateway.executed_calls,
            decisions=decisions,
        ),
    )
    outcome = dict(task_succeeded=False, unauthorized_effect=None, attacker_goal_achieved=None)
    extra_errors = []
    if not infrastructure_error:
        try:
            outcome = evaluate_outcome(oracle, before, after, gateway.executed_calls)
        except Exception:
            infrastructure_error = True
            extra_errors.append("SCORING_FAILED")
    events = []
    try:
        if audit.path.exists():
            events = [
                json.loads(line) for line in audit.path.read_text(encoding="utf-8").splitlines()
            ]
    except (ValueError, OSError):
        infrastructure_error = True
        extra_errors.append("AUDIT_READ_FAILED")
    result = dict(
        **outcome,
        proposed=len(proposals),
        attempted=len(decisions),
        executed=len(gateway.executed_calls),
        blocked=sum(r.decision == "block" for r in decisions),
        approval_requests=sum(r.decision == "approve" for r in decisions),
        unattempted=len(proposals) - len(decisions),
        infrastructure_error=bool(infrastructure_error),
        error_codes=sorted({r.error_code for r in decisions if r.error_code} | set(extra_errors)),
        gateway_timings_ns=[
            e["gateway_duration_ns"]
            for e in events
            if e["event_type"] == "outcome" and e["gateway_duration_ns"] is not None
        ],
        tool_timings_ns=[
            e["tool_duration_ns"]
            for e in events
            if e["event_type"] == "outcome" and e["tool_duration_ns"] is not None
        ],
    )
    return result


def _aggregate(rows):
    benign = [r for r in rows if r["variant"] == "benign"]
    attacks = [r for r in rows if r["variant"] == "attack"]
    return dict(
        executions=len(rows),
        benign_cases=len(benign),
        attack_cases=len(attacks),
        benign_successes=sum(r["task_succeeded"] is True for r in benign),
        attacker_goals=sum(r["attacker_goal_achieved"] is True for r in attacks),
        scripted_attack_goal_rate=sum(r["attacker_goal_achieved"] is True for r in attacks)
        / len(attacks)
        if attacks
        else None,
        unauthorized_effects=sum(r["unauthorized_effect"] is True for r in rows),
        blocked_calls=sum(r["blocked"] or 0 for r in rows),
        approval_requests=sum(r["approval_requests"] or 0 for r in rows),
        unknown_execution_count_cases=sum(r["executed"] is None for r in rows),
        incomplete_benign=sum(r["task_succeeded"] is not True for r in benign),
        infrastructure_errors=sum(r["infrastructure_error"] for r in rows),
        gateway_timing_samples=sum(len(r["gateway_timings_ns"]) for r in rows),
        tool_timing_samples=sum(len(r["tool_timings_ns"]) for r in rows),
    )


def summarize(rows, modes):
    return dict(
        experiment_kind="scripted_boundary",
        split="development",
        executions=len(rows),
        modes={m: _aggregate([r for r in rows if r["mode"] == m]) for m in modes},
        families={
            m: {
                f: _aggregate([r for r in rows if r["mode"] == m and r["family"] == f])
                for f in sorted({r["family"] for r in rows})
            }
            for m in modes
        },
    )


def run_matrix(cases_path: Path, modes: list[str], output: Path) -> dict:
    if not modes or len(set(modes)) != len(modes) or not set(modes) <= set(MODES):
        raise ValueError("MODES_INVALID")
    cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines()]
    if cases != generate_cases():
        raise ValueError("DATASET_DIFFERS_FROM_DECLARED_DEVELOPMENT_CASES")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise FileExistsError("RUN_EXISTS")
    output.mkdir(parents=True, exist_ok=True)
    (output / "cases.jsonl").write_bytes(cases_path.read_bytes())
    manifest = dict(
        schema_version="tbm.run.v1",
        experiment_kind="scripted_boundary",
        split="development",
        started_utc=datetime.now(UTC).isoformat(),
        modes=modes,
        case_ids=[c["case_id"] for c in cases],
        dataset_sha256=_hash(cases_path),
        source_commit=_git("rev-parse", "HEAD"),
        dirty_worktree=bool(_git("status", "--porcelain")),
        source_hashes=_source_inventory(),
        python=platform.python_version(),
        platform=platform.platform(),
        agentdojo=version("agentdojo"),
        suite="banking",
        suite_version="v1.2.2",
        dependency_lock_sha256=_hash(PROJECT_ROOT / "requirements.lock.txt"),
    )
    rows = []
    for mode in modes:
        for case in cases:
            directory = output / mode / case["case_id"]
            try:
                result = run_case(public_case(case), case["oracle"], mode, directory)
            except Exception:
                directory.mkdir(parents=True, exist_ok=True)
                result = dict(
                    task_succeeded=False,
                    unauthorized_effect=None,
                    attacker_goal_achieved=None,
                    proposed=len(case["public"]["proposals"]),
                    attempted=None,
                    executed=None,
                    blocked=None,
                    approval_requests=None,
                    unattempted=None,
                    infrastructure_error=True,
                    error_codes=["RUN_CASE_FAILED"],
                    gateway_timings_ns=[],
                    tool_timings_ns=[],
                )
            result.update(
                case_id=case["case_id"],
                family=case["family"],
                variant=case["variant"],
                mode=mode,
                experiment_kind="scripted_boundary",
            )
            _write(directory / "result.json", result)
            rows.append(result)
    summary = summarize(rows, modes)
    _write(output / "summary.json", summary)
    lines = [
        "# Local scripted boundary results",
        "",
        "Development fixtures, not live-model ASR.",
        "",
        "| Mode | Benign complete | Scripted attacker goals | Unauthorized effects | Errors |",
        "|---|---:|---:|---:|---:|",
    ]
    for mode, counts in summary["modes"].items():
        lines.append(
            f"| {mode} | {counts['benign_successes']}/{counts['benign_cases']} | {counts['attacker_goals']}/{counts['attack_cases']} | {counts['unauthorized_effects']} | {counts['infrastructure_errors']} |"
        )
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest["artifacts"] = {
        p.relative_to(output).as_posix(): _hash(p) for p in sorted(output.rglob("*")) if p.is_file()
    }
    _write(output / "manifest.json", manifest)
    return summary


def verify_run(root: Path) -> list[str]:
    errors = []
    try:
        manifest = _read(root / "manifest.json")
        modes = manifest["modes"]
        cases = generate_cases()
        ids = [c["case_id"] for c in cases]
        if (
            manifest["case_ids"] != ids
            or not modes
            or len(set(modes)) != len(modes)
            or not set(modes) <= set(MODES)
        ):
            return ["MANIFEST_MATRIX_INVALID"]
        if _hash(root / "cases.jsonl") != manifest["dataset_sha256"]:
            errors.append("DATASET_HASH_MISMATCH")
        if [
            json.loads(line)
            for line in (root / "cases.jsonl").read_text(encoding="utf-8").splitlines()
        ] != cases:
            errors.append("DATASET_CONTENT_MISMATCH")
        for name, digest in manifest["artifacts"].items():
            path = (root / name).resolve()
            if (
                not path.is_relative_to(root.resolve())
                or not path.is_file()
                or _hash(path) != digest
            ):
                errors.append(f"ARTIFACT_INVALID:{name}")
        expected = {f"{m}/{i}/result.json" for m in modes for i in ids}
        actual = {p.relative_to(root).as_posix() for p in root.glob("*/*/result.json")}
        for name in sorted(expected - actual):
            errors.append(f"MISSING_RESULT:{name}")
        for name in sorted(actual - expected):
            errors.append(f"UNEXPECTED_RESULT:{name}")
        rows = []
        for mode in modes:
            for case in cases:
                identifier = f"{mode}/{case['case_id']}"
                directory = root / identifier
                if not (directory / "result.json").exists():
                    continue
                try:
                    result = _read(directory / "result.json")
                    rows.append(result)
                    if (
                        result["case_id"] != case["case_id"]
                        or result["mode"] != mode
                        or result["variant"] != case["variant"]
                    ):
                        raise ValueError("RESULT_IDENTITY_MISMATCH")
                    if result["infrastructure_error"]:
                        errors.append(f"INFRASTRUCTURE_ERROR:{identifier}")
                        continue
                    trace = _read(directory / "synthetic-trace.json")
                    if trace["before"] != case["public"]["initial_environment"]:
                        raise ValueError("INITIAL_STATE_MISMATCH")
                    verdict = evaluate_outcome(
                        case["oracle"], trace["before"], trace["after"], trace["executed_calls"]
                    )
                    if any(result[k] != v for k, v in verdict.items()):
                        raise ValueError("ORACLE_MISMATCH")
                    events = [
                        Event.model_validate_json(line)
                        for line in (directory / "audit.jsonl")
                        .read_text(encoding="utf-8")
                        .splitlines()
                    ]
                    if (
                        len(events) != 2 * result["attempted"]
                        or len(trace["decisions"]) != result["attempted"]
                    ):
                        raise ValueError("AUDIT_PAIR_COUNT")
                    for a, b in zip(events[::2], events[1::2]):
                        if (
                            a.event_type != "decision"
                            or b.event_type != "outcome"
                            or a.event_id != b.event_id
                            or a.request_id != b.request_id
                        ):
                            raise ValueError("AUDIT_PAIR_MISMATCH")
                        if (
                            a.case_id != case["case_id"]
                            or b.case_id != case["case_id"]
                            or a.configuration != mode
                            or b.configuration != mode
                        ):
                            raise ValueError("AUDIT_IDENTITY_MISMATCH")
                        if b.error_code or b.execution_status in ("tool_error", "audit_incomplete"):
                            raise ValueError("AUDIT_EXECUTION_ERROR")
                    if (
                        result["executed"] != len(trace["executed_calls"])
                        or result["unattempted"] + result["attempted"] != result["proposed"]
                    ):
                        raise ValueError("TRACE_COUNT_MISMATCH")
                except (ValueError, KeyError, TypeError, OSError):
                    errors.append(f"INVALID_CASE_ARTIFACTS:{identifier}")
        if _read(root / "summary.json") != summarize(rows, modes):
            errors.append("SUMMARY_MISMATCH")
    except (ValueError, KeyError, TypeError, OSError):
        errors.append("RUN_MANIFEST_INVALID")
    return errors
