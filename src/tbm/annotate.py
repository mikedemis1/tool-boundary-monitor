"""Blinded annotation harness for the contract expressibility study.

`agentdojo` is imported inside build_prompt_fixture only. Importing this
module must not make suite data reachable from an annotator's process.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tbm.expressibility import AnnotationSet

_ALLOWED_KEYS = {"task_id", "prompt"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _serialize(payload: object) -> bytes:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    return (text + "\n").encode("utf-8")


def build_prompt_fixture(out_path: Path) -> str:
    from agentdojo.task_suite.load_suites import get_suite

    suite = get_suite("v1.2.2", "banking")
    records = [
        {"task_id": task_id, "prompt": task.PROMPT} for task_id, task in suite.user_tasks.items()
    ]
    records.sort(key=lambda record: int(record["task_id"].rsplit("_", 1)[1]))
    data = _serialize(records)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return _sha256(data)


def load_prompt_fixture(path: Path) -> list[dict]:
    records = json.loads(path.read_text(encoding="utf-8"))
    for record in records:
        extra = set(record) - _ALLOWED_KEYS
        if extra:
            raise ValueError(f"unexpected key in prompt fixture: {sorted(extra)}")
    return records


def save_annotation_set(path: Path, annotations: AnnotationSet) -> str:
    data = _serialize(annotations.model_dump(mode="json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return _sha256(data)


def load_annotation_set(path: Path) -> AnnotationSet:
    return AnnotationSet.model_validate_json(path.read_text(encoding="utf-8"))
