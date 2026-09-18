import json

import pytest

from tbm.annotate import (
    build_prompt_fixture,
    load_annotation_set,
    load_prompt_fixture,
    save_annotation_set,
)
from tbm.expressibility import (
    AnnotationSet,
    AuthorityFact,
    AuthoritySource,
    Expressibility,
    TaskAnnotation,
)


def test_fixture_contains_only_task_id_and_prompt(tmp_path):
    path = tmp_path / "task-prompts.json"
    build_prompt_fixture(path)
    records = json.loads(path.read_text(encoding="utf-8"))
    assert len(records) == 16
    for record in records:
        assert set(record) == {"task_id", "prompt"}


def test_fixture_leaks_no_environment_identifiers(tmp_path):
    path = tmp_path / "task-prompts.json"
    build_prompt_fixture(path)
    raw = path.read_text(encoding="utf-8")
    for forbidden in ("GOAL", "ground_truth", "injection", "US133000000121212121212"):
        assert forbidden not in raw


def test_fixture_is_byte_stable(tmp_path):
    first = build_prompt_fixture(tmp_path / "a.json")
    second = build_prompt_fixture(tmp_path / "b.json")
    assert first == second


def test_loader_rejects_an_extra_key(tmp_path):
    path = tmp_path / "tainted.json"
    path.write_text(
        json.dumps([{"task_id": "user_task_0", "prompt": "x", "ground_truth": "leak"}]),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unexpected key"):
        load_prompt_fixture(path)


def test_importing_the_module_does_not_import_agentdojo():
    import subprocess
    import sys

    code = "import tbm.annotate, sys; print('agentdojo' in sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "False"


def test_annotation_set_round_trips(tmp_path):
    original = AnnotationSet(
        annotator_id="B",
        contaminated=False,
        preregistration_sha256="b" * 64,
        created_utc="2026-09-18T00:00:00+00:00",
        annotations=(
            TaskAnnotation(
                task_id="user_task_0",
                verdict=Expressibility.PARTIALLY_EXPRESSIBLE,
                facts=(AuthorityFact(name="amount", source=AuthoritySource.UNTRUSTED_DOCUMENT),),
                rationale="the amount is inside the named file",
            ),
        ),
    )
    path = tmp_path / "annotator-B.json"
    save_annotation_set(path, original)
    assert load_annotation_set(path) == original
