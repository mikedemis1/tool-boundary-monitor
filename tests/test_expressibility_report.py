import pytest

from tbm.expressibility import (
    AnnotationSet,
    AuthorityFact,
    AuthoritySource,
    Expressibility,
    TaskAnnotation,
)
from tbm.expressibility_report import (
    cohens_kappa,
    compare_annotators,
    compute_rates,
    decision,
)


def _set(annotator_id: str, contaminated: bool, verdicts: list[Expressibility]):
    annotations = tuple(
        TaskAnnotation(
            task_id=f"user_task_{index}",
            verdict=verdict,
            facts=(AuthorityFact(name="amount", source=AuthoritySource.USER_EXPLICIT),),
            rationale="fixture",
        )
        for index, verdict in enumerate(verdicts)
    )
    return AnnotationSet(
        annotator_id=annotator_id,
        contaminated=contaminated,
        preregistration_sha256="c" * 64,
        created_utc="2026-09-18T00:00:00+00:00",
        annotations=annotations,
    )


def test_rates_count_partial_and_inexpressible_as_unresolved():
    annotations = _set(
        "B",
        False,
        [
            Expressibility.EXPRESSIBLE,
            Expressibility.PARTIALLY_EXPRESSIBLE,
            Expressibility.INEXPRESSIBLE,
            Expressibility.EXPRESSIBLE,
        ],
    )
    rates = compute_rates(annotations)
    assert rates["total"] == 4
    assert rates["expressibility_rate"] == 0.5
    assert rates["unresolved_authority_rate"] == 0.5


def test_untrusted_provenance_counts_a_task_once():
    annotations = AnnotationSet(
        annotator_id="B",
        contaminated=False,
        preregistration_sha256="c" * 64,
        created_utc="2026-09-18T00:00:00+00:00",
        annotations=(
            TaskAnnotation(
                task_id="user_task_0",
                verdict=Expressibility.PARTIALLY_EXPRESSIBLE,
                facts=(
                    AuthorityFact(name="amount", source=AuthoritySource.UNTRUSTED_DOCUMENT),
                    AuthorityFact(name="recipient", source=AuthoritySource.UNTRUSTED_DOCUMENT),
                ),
                rationale="both from the file",
            ),
        ),
    )
    assert compute_rates(annotations)["untrusted_provenance_rate"] == 1.0


def test_agent_judgment_is_not_counted_as_untrusted_provenance():
    annotations = AnnotationSet(
        annotator_id="B",
        contaminated=False,
        preregistration_sha256="c" * 64,
        created_utc="2026-09-18T00:00:00+00:00",
        annotations=(
            TaskAnnotation(
                task_id="user_task_14",
                verdict=Expressibility.INEXPRESSIBLE,
                facts=(AuthorityFact(name="trigger", source=AuthoritySource.AGENT_JUDGMENT),),
                rationale="subjective condition",
            ),
        ),
    )
    rates = compute_rates(annotations)
    assert rates["untrusted_provenance_rate"] == 0.0
    assert rates["unresolved_authority_rate"] == 1.0


def test_kappa_is_one_for_identical_labels():
    assert cohens_kappa(["a", "b", "a"], ["a", "b", "a"]) == pytest.approx(1.0)


def test_kappa_is_zero_at_chance_agreement():
    labels_a = ["a", "a", "b", "b"]
    labels_b = ["a", "b", "a", "b"]
    assert cohens_kappa(labels_a, labels_b) == pytest.approx(0.0)


def test_kappa_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        cohens_kappa(["a"], ["a", "b"])


def test_contaminated_annotator_never_contributes_to_agreement():
    contaminated = _set("A", True, [Expressibility.EXPRESSIBLE])
    clean = _set("B", False, [Expressibility.EXPRESSIBLE])
    result = compare_annotators([contaminated, clean])
    assert result["uncontaminated_annotators"] == ["B"]
    assert result["agreement_verdict"] is None


def test_decision_follows_the_preregistered_rule():
    assert decision(2, 16) == "not_supported"
    assert decision(5, 16) == "inconclusive"
    assert decision(8, 16) == "supported"
