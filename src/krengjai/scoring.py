"""Transparent reference scoring for JAI-Bench seed data."""

from __future__ import annotations

from collections import Counter
from statistics import fmean
from typing import Any, Iterable, Mapping

from .schemas import AXES


DEFAULT_WEIGHTS = {axis: 1.0 for axis in AXES}


def weighted_score(
    scores: Mapping[str, float], weights: Mapping[str, float] | None = None
) -> float:
    """Return a normalized weighted mean over all behavioral axes."""

    active_weights = DEFAULT_WEIGHTS if weights is None else weights
    if set(scores) != set(AXES):
        raise ValueError("scores must contain exactly the eight KrengJAI axes")
    if set(active_weights) != set(AXES):
        raise ValueError("weights must contain exactly the eight KrengJAI axes")

    denominator = sum(float(active_weights[axis]) for axis in AXES)
    if denominator <= 0:
        raise ValueError("weights must have a positive total")

    return sum(
        float(scores[axis]) * float(active_weights[axis]) for axis in AXES
    ) / denominator


def preference_margin(
    example: Mapping[str, Any], weights: Mapping[str, float] | None = None
) -> float:
    """Return chosen score minus rejected score for one preference example."""

    scores = example["reference_scores"]
    return weighted_score(scores["chosen"], weights) - weighted_score(
        scores["rejected"], weights
    )


def summarize_dataset(examples: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize composition and reference preference margins."""

    materialized = list(examples)
    margins = [preference_margin(example) for example in materialized]
    categories = Counter(str(example["category"]) for example in materialized)
    languages = Counter(str(example["language"]) for example in materialized)
    groups = {
        str(example["counterfactual_group"])
        for example in materialized
        if example.get("counterfactual_group") is not None
    }

    return {
        "examples": len(materialized),
        "categories": dict(sorted(categories.items())),
        "languages": dict(sorted(languages.items())),
        "counterfactual_groups": len(groups),
        "needs_native_review": sum(
            example["review_status"] == "needs_native_review"
            for example in materialized
        ),
        "positive_reference_margins": sum(margin > 0 for margin in margins),
        "mean_reference_margin": round(fmean(margins), 4) if margins else 0.0,
    }

