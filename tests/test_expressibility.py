import pytest
from pydantic import ValidationError

from tbm.expressibility import (
    AnnotationSet,
    AuthorityFact,
    AuthoritySource,
    Expressibility,
    TaskAnnotation,
)


def _annotation(task_id: str) -> TaskAnnotation:
    return TaskAnnotation(
        task_id=task_id,
        verdict=Expressibility.EXPRESSIBLE,
        facts=(AuthorityFact(name="recipient", source=AuthoritySource.USER_EXPLICIT),),
        rationale="stated in the task text",
    )


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        TaskAnnotation(
            task_id="user_task_0",
            verdict=Expressibility.EXPRESSIBLE,
            facts=(),
            rationale="",
            confidence=0.9,
        )


def test_verdict_must_be_a_known_member():
    with pytest.raises(ValidationError):
        TaskAnnotation(
            task_id="user_task_0",
            verdict="probably_fine",
            facts=(),
            rationale="",
        )


def test_duplicate_task_ids_are_rejected():
    with pytest.raises(ValidationError):
        AnnotationSet(
            annotator_id="B",
            contaminated=False,
            preregistration_sha256="0" * 64,
            created_utc="2026-09-18T00:00:00+00:00",
            annotations=(_annotation("user_task_0"), _annotation("user_task_0")),
        )


def test_preregistration_hash_must_look_like_sha256():
    with pytest.raises(ValidationError):
        AnnotationSet(
            annotator_id="B",
            contaminated=False,
            preregistration_sha256="not-a-hash",
            created_utc="2026-09-18T00:00:00+00:00",
            annotations=(_annotation("user_task_0"),),
        )


def test_valid_set_round_trips_through_json():
    original = AnnotationSet(
        annotator_id="B",
        contaminated=False,
        preregistration_sha256="a" * 64,
        created_utc="2026-09-18T00:00:00+00:00",
        annotations=(_annotation("user_task_0"),),
    )
    restored = AnnotationSet.model_validate_json(original.model_dump_json())
    assert restored == original
