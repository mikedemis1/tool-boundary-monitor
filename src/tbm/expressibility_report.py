"""Rates and inter-annotator agreement for the expressibility study."""

from __future__ import annotations

from collections import Counter

from tbm.expressibility import (
    NON_USER_SOURCES,
    AnnotationSet,
    Expressibility,
)

_UNRESOLVED = frozenset({Expressibility.PARTIALLY_EXPRESSIBLE, Expressibility.INEXPRESSIBLE})


def compute_rates(annotations: AnnotationSet) -> dict:
    total = len(annotations.annotations)
    if total == 0:
        raise ValueError("cannot compute rates over an empty annotation set")
    counts = Counter(a.verdict.value for a in annotations.annotations)
    expressible = counts.get(Expressibility.EXPRESSIBLE.value, 0)
    unresolved = sum(1 for a in annotations.annotations if a.verdict in _UNRESOLVED)
    untrusted = sum(
        1
        for a in annotations.annotations
        if any(fact.source in NON_USER_SOURCES for fact in a.facts)
    )
    return {
        "total": total,
        "counts": dict(counts),
        "expressibility_rate": expressible / total,
        "unresolved_authority_rate": unresolved / total,
        "unresolved_authority_count": unresolved,
        "untrusted_provenance_rate": untrusted / total,
    }


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    if len(labels_a) != len(labels_b):
        raise ValueError("label sequences must have the same length")
    n = len(labels_a)
    if n == 0:
        raise ValueError("cannot compute kappa over zero pairs")
    observed = sum(1 for a, b in zip(labels_a, labels_b, strict=True) if a == b) / n
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    expected = sum(
        (counts_a[label] / n) * (counts_b[label] / n) for label in set(counts_a) | set(counts_b)
    )
    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)


def compare_annotators(sets: list[AnnotationSet]) -> dict:
    clean = [s for s in sets if not s.contaminated]
    result: dict = {
        "uncontaminated_annotators": [s.annotator_id for s in clean],
        "agreement_verdict": None,
        "agreement_source": None,
    }
    if len(clean) < 2:
        result["note"] = "fewer than two uncontaminated annotators; agreement unavailable"
        return result

    first, second = clean[0], clean[1]
    shared = sorted(
        {a.task_id for a in first.annotations} & {a.task_id for a in second.annotations}
    )
    by_id_first = {a.task_id: a for a in first.annotations}
    by_id_second = {a.task_id: a for a in second.annotations}
    result["agreement_verdict"] = cohens_kappa(
        [by_id_first[t].verdict.value for t in shared],
        [by_id_second[t].verdict.value for t in shared],
    )

    fact_labels_first: list[str] = []
    fact_labels_second: list[str] = []
    for task_id in shared:
        facts_first = {f.name: f.source.value for f in by_id_first[task_id].facts}
        facts_second = {f.name: f.source.value for f in by_id_second[task_id].facts}
        for name in sorted(set(facts_first) & set(facts_second)):
            fact_labels_first.append(facts_first[name])
            fact_labels_second.append(facts_second[name])
    if fact_labels_first:
        result["agreement_source"] = cohens_kappa(fact_labels_first, fact_labels_second)
    return result


def decision(unresolved_authority_rate_count: int, total: int) -> str:
    if total != 16:
        raise ValueError("the pre-registered rule is defined for 16 tasks")
    if unresolved_authority_rate_count <= 2:
        return "not_supported"
    if unresolved_authority_rate_count >= 8:
        return "supported"
    return "inconclusive"
