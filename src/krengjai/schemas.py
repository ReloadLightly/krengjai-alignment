"""Schema validation for JAI-Bench preference examples."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


AXES = (
    "respect",
    "truthfulness",
    "constructive_disagreement",
    "status_neutrality",
    "non_sycophancy",
    "clarity",
    "calibrated_directness",
    "cultural_sensitivity",
)

LANGUAGES = {"th", "en", "th-en"}
REVIEW_STATUSES = {"needs_native_review", "native_reviewed", "adjudicated"}
SCORE_MIN = 0.0
SCORE_MAX = 4.0


class SchemaError(ValueError):
    """Raised when an evaluation example violates the JAI-Bench schema."""


def _require_nonempty_text(example: Mapping[str, Any], field: str) -> None:
    value = example.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SchemaError(f"{field!r} must be a non-empty string")


def _validate_score_map(scores: Any, label: str) -> None:
    if not isinstance(scores, Mapping):
        raise SchemaError(f"reference_scores.{label} must be an object")

    missing = set(AXES) - set(scores)
    extra = set(scores) - set(AXES)
    if missing or extra:
        raise SchemaError(
            f"reference_scores.{label} has missing axes {sorted(missing)} "
            f"and extra axes {sorted(extra)}"
        )

    for axis in AXES:
        value = scores[axis]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SchemaError(f"{label}.{axis} must be numeric")
        if not SCORE_MIN <= float(value) <= SCORE_MAX:
            raise SchemaError(
                f"{label}.{axis}={value} is outside [{SCORE_MIN}, {SCORE_MAX}]"
            )


def validate_example(example: Mapping[str, Any]) -> None:
    """Validate one preference example, raising :class:`SchemaError` on failure."""

    if not isinstance(example, Mapping):
        raise SchemaError("each JSONL row must be an object")

    for field in ("id", "category", "prompt", "chosen", "rejected"):
        _require_nonempty_text(example, field)

    if example.get("chosen") == example.get("rejected"):
        raise SchemaError("chosen and rejected responses must differ")

    language = example.get("language")
    if language not in LANGUAGES:
        raise SchemaError(f"language must be one of {sorted(LANGUAGES)}")

    review_status = example.get("review_status")
    if review_status not in REVIEW_STATUSES:
        raise SchemaError(f"review_status must be one of {sorted(REVIEW_STATUSES)}")

    risk_tags = example.get("risk_tags")
    if (
        not isinstance(risk_tags, list)
        or not risk_tags
        or any(not isinstance(tag, str) or not tag.strip() for tag in risk_tags)
    ):
        raise SchemaError("risk_tags must be a non-empty list of strings")

    scores = example.get("reference_scores")
    if not isinstance(scores, Mapping) or set(scores) != {"chosen", "rejected"}:
        raise SchemaError("reference_scores must contain exactly chosen and rejected")
    _validate_score_map(scores["chosen"], "chosen")
    _validate_score_map(scores["rejected"], "rejected")

    group = example.get("counterfactual_group")
    variant = example.get("counterfactual_variant")
    if (group is None) != (variant is None):
        raise SchemaError(
            "counterfactual_group and counterfactual_variant must appear together"
        )
    if group is not None:
        if not isinstance(group, str) or not group.strip():
            raise SchemaError("counterfactual_group must be a non-empty string")
        if not isinstance(variant, str) or not variant.strip():
            raise SchemaError("counterfactual_variant must be a non-empty string")


def validate_dataset(examples: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Validate dataset-wide invariants and return a materialized list."""

    materialized = list(examples)
    if not materialized:
        raise SchemaError("dataset must contain at least one example")

    for index, example in enumerate(materialized, start=1):
        try:
            validate_example(example)
        except SchemaError as exc:
            raise SchemaError(f"example {index}: {exc}") from exc

    ids = [str(example["id"]) for example in materialized]
    duplicates = sorted(key for key, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise SchemaError(f"duplicate ids: {duplicates}")

    groups = Counter(
        str(example["counterfactual_group"])
        for example in materialized
        if example.get("counterfactual_group") is not None
    )
    singletons = sorted(group for group, count in groups.items() if count < 2)
    if singletons:
        raise SchemaError(f"counterfactual groups need at least two variants: {singletons}")

    return materialized


def load_examples(path: str | Path) -> list[Mapping[str, Any]]:
    """Load and validate a UTF-8 JSONL dataset."""

    dataset_path = Path(path)
    examples: list[Mapping[str, Any]] = []

    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SchemaError(
                    f"{dataset_path}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc

    try:
        return validate_dataset(examples)
    except SchemaError as exc:
        raise SchemaError(f"{dataset_path}: {exc}") from exc

