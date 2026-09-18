"""Taxonomy for the contract expressibility study.

Deliberately imports nothing from the gateway or from agentdojo: annotation
must not be able to reach environment or ground-truth data.
"""

from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AuthoritySource(StrEnum):
    USER_EXPLICIT = "user_explicit"
    USER_IMPLICIT = "user_implicit"
    ACCOUNT_HISTORY = "account_history"
    UNTRUSTED_DOCUMENT = "untrusted_document"
    DELEGATED = "delegated"
    AGENT_JUDGMENT = "agent_judgment"


class Expressibility(StrEnum):
    EXPRESSIBLE = "expressible"
    PARTIALLY_EXPRESSIBLE = "partially_expressible"
    INEXPRESSIBLE = "inexpressible"


NON_USER_SOURCES = frozenset(
    {
        AuthoritySource.ACCOUNT_HISTORY,
        AuthoritySource.UNTRUSTED_DOCUMENT,
        AuthoritySource.DELEGATED,
    }
)


class AuthorityFact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    source: AuthoritySource
    note: str = ""


class TaskAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    verdict: Expressibility
    facts: tuple[AuthorityFact, ...]
    rationale: str


class AnnotationSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    annotator_id: str
    contaminated: bool
    preregistration_sha256: str
    created_utc: str
    annotations: tuple[TaskAnnotation, ...]

    @field_validator("preregistration_sha256")
    @classmethod
    def _check_hash(cls, value: str) -> str:
        if not _SHA256.match(value):
            raise ValueError("preregistration_sha256 must be 64 lowercase hex characters")
        return value

    @model_validator(mode="after")
    def _check_unique_task_ids(self) -> AnnotationSet:
        seen = [a.task_id for a in self.annotations]
        if len(seen) != len(set(seen)):
            raise ValueError("duplicate task_id in annotations")
        return self
