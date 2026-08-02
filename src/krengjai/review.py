"""Blind and summarize human review of controlled Typhoon baselines.

The reviewer sees prompts and two anonymous responses.  Model identity,
condition labels, generation settings, dataset metadata, and the unblinding key
remain in a separate file so they cannot influence the ratings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Mapping, Sequence

from .prompts import BASELINE_CONDITIONS
from .schemas import AXES, SCORE_MAX, SCORE_MIN


REVIEW_SCHEMA_VERSION = 1
REVIEW_SIDES = ("a", "b")
OVERALL_PREFERENCES = {"a", "b", "tie"}
REFERENCE_LEAK_FIELDS = {"chosen", "rejected", "reference_scores"}
PACKET_FIELDS = {
    "blind_id",
    "prompt",
    "response_a",
    "response_b",
    "ratings",
    "overall_preference",
    "rationale",
    "reviewer_id",
}


class ReviewError(ValueError):
    """Raised when baseline or review records would invalidate the experiment."""


def load_jsonl(path: str | Path) -> list[Mapping[str, Any]]:
    """Load a UTF-8 JSONL file and report precise parse errors."""

    source = Path(path)
    records: list[Mapping[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ReviewError(
                    f"{source}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            if not isinstance(record, Mapping):
                raise ReviewError(f"{source}:{line_number}: row must be an object")
            records.append(record)
    if not records:
        raise ReviewError(f"{source}: file contains no records")
    return records


def _write_jsonl(path: str | Path, records: Iterable[Mapping[str, Any]]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_json(path: str | Path, value: Mapping[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _require_text(record: Mapping[str, Any], field: str, context: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ReviewError(f"{context}: {field} must be a non-empty string")
    return value


def _validate_baseline_metadata(record: Mapping[str, Any], context: str) -> None:
    risk_tags = record.get("risk_tags")
    if not isinstance(risk_tags, list) or any(
        not isinstance(tag, str) or not tag.strip() for tag in risk_tags
    ):
        raise ReviewError(f"{context}: risk_tags must be a list of strings")

    group = record.get("counterfactual_group")
    variant = record.get("counterfactual_variant")
    if (group is None) != (variant is None):
        raise ReviewError(
            f"{context}: counterfactual_group and counterfactual_variant "
            "must appear together"
        )
    if group is not None:
        if not isinstance(group, str) or not group.strip():
            raise ReviewError(
                f"{context}: counterfactual_group must be a non-empty string"
            )
        if not isinstance(variant, str) or not variant.strip():
            raise ReviewError(
                f"{context}: counterfactual_variant must be a non-empty string"
            )


def _content_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _index_baseline(
    records: Sequence[Mapping[str, Any]], expected_condition: str
) -> dict[str, Mapping[str, Any]]:
    if expected_condition not in BASELINE_CONDITIONS:
        raise ReviewError(f"unknown baseline condition: {expected_condition}")

    indexed: dict[str, Mapping[str, Any]] = {}
    for position, record in enumerate(records, start=1):
        context = f"{expected_condition} record {position}"
        leaked = sorted(REFERENCE_LEAK_FIELDS.intersection(record))
        if leaked:
            raise ReviewError(f"{context}: reference fields leaked into output: {leaked}")

        example_id = _require_text(record, "example_id", context)
        _require_text(record, "prompt", context)
        _require_text(record, "response", context)
        _require_text(record, "category", context)
        _require_text(record, "language", context)
        _require_text(record, "model_id", context)
        _validate_baseline_metadata(record, context)

        if record.get("condition") != expected_condition:
            raise ReviewError(
                f"{context}: condition must be {expected_condition!r}, "
                f"got {record.get('condition')!r}"
            )
        if not isinstance(record.get("generation"), Mapping):
            raise ReviewError(f"{context}: generation must be an object")
        if example_id in indexed:
            raise ReviewError(f"{expected_condition}: duplicate example_id {example_id!r}")
        indexed[example_id] = record
    return indexed


def _blind_digest(seed: int, example_id: str) -> bytes:
    material = f"krengjai-review-v1\0{seed}\0{example_id}".encode("utf-8")
    return hashlib.sha256(material).digest()


def build_review_pack(
    native_records: Sequence[Mapping[str, Any]],
    prompted_records: Sequence[Mapping[str, Any]],
    seed: int = 42,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Create a deterministic blinded packet and a separate unblinding key."""

    native = _index_baseline(native_records, "native")
    prompted = _index_baseline(prompted_records, "spec_prompted")
    if set(native) != set(prompted):
        native_only = sorted(set(native) - set(prompted))
        prompted_only = sorted(set(prompted) - set(native))
        raise ReviewError(
            "conditions must contain identical example ids; "
            f"native_only={native_only}, spec_prompted_only={prompted_only}"
        )

    packet_with_order: list[tuple[str, dict[str, Any]]] = []
    key_records: dict[str, dict[str, Any]] = {}

    for example_id in sorted(native):
        native_record = native[example_id]
        prompted_record = prompted[example_id]
        for field in (
            "prompt",
            "category",
            "language",
            "risk_tags",
            "counterfactual_group",
            "counterfactual_variant",
        ):
            if native_record.get(field) != prompted_record.get(field):
                raise ReviewError(f"{example_id}: {field} differs between conditions")
        if native_record["model_id"] != prompted_record["model_id"]:
            raise ReviewError(f"{example_id}: model_id differs between conditions")
        if dict(native_record["generation"]) != dict(prompted_record["generation"]):
            raise ReviewError(f"{example_id}: generation settings differ between conditions")

        digest = _blind_digest(seed, example_id)
        blind_id = f"KJ-{digest.hex()[:12].upper()}"
        if blind_id in key_records:
            raise ReviewError(f"blind id collision for {example_id}")

        native_is_a = digest[0] % 2 == 0
        a_record = native_record if native_is_a else prompted_record
        b_record = prompted_record if native_is_a else native_record

        packet = {
            "blind_id": blind_id,
            "prompt": native_record["prompt"],
            "response_a": a_record["response"],
            "response_b": b_record["response"],
            "ratings": {
                side: {axis: None for axis in AXES} for side in REVIEW_SIDES
            },
            "overall_preference": None,
            "rationale": "",
            "reviewer_id": "",
        }
        packet_with_order.append((digest.hex(), packet))

        key_records[blind_id] = {
            "example_id": example_id,
            "category": native_record["category"],
            "language": native_record["language"],
            "risk_tags": list(native_record.get("risk_tags", [])),
            "counterfactual_group": native_record.get("counterfactual_group"),
            "counterfactual_variant": native_record.get("counterfactual_variant"),
            "a_condition": a_record["condition"],
            "b_condition": b_record["condition"],
            "prompt_sha256": _content_digest(native_record["prompt"]),
            "response_a_sha256": _content_digest(a_record["response"]),
            "response_b_sha256": _content_digest(b_record["response"]),
            "model_id": native_record["model_id"],
            "generation": dict(native_record["generation"]),
        }

    packet_with_order.sort(key=lambda item: item[0])
    packet = [record for _, record in packet_with_order]
    key = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "seed": seed,
        "conditions": list(BASELINE_CONDITIONS),
        "records": key_records,
    }
    return packet, key


def write_review_bundle(
    native_path: str | Path,
    prompted_path: str | Path,
    packet_path: str | Path,
    key_path: str | Path,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build and write a blinded review packet and its private key."""

    packet, key = build_review_pack(
        load_jsonl(native_path), load_jsonl(prompted_path), seed=seed
    )
    _write_jsonl(packet_path, packet)
    _write_json(key_path, key)
    return packet, key


def _validated_score_map(value: Any, context: str) -> dict[str, float]:
    if not isinstance(value, Mapping) or set(value) != set(AXES):
        raise ReviewError(f"{context}: ratings must contain exactly the eight axes")
    scores: dict[str, float] = {}
    for axis in AXES:
        score = value[axis]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ReviewError(f"{context}: {axis} must be numeric")
        numeric = float(score)
        if not SCORE_MIN <= numeric <= SCORE_MAX:
            raise ReviewError(
                f"{context}: {axis}={score} is outside [{SCORE_MIN}, {SCORE_MAX}]"
            )
        scores[axis] = numeric
    return scores


def _mean(values: Sequence[float]) -> float:
    return round(fmean(values), 4) if values else 0.0


def summarize_reviews(
    review_records: Sequence[Mapping[str, Any]], key: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate completed reviews, unblind conditions, and compute diagnostics."""

    if key.get("schema_version") != REVIEW_SCHEMA_VERSION:
        raise ReviewError("unsupported or missing review-key schema_version")
    key_records = key.get("records")
    if not isinstance(key_records, Mapping) or not key_records:
        raise ReviewError("review key must contain records")

    axis_values: dict[str, dict[str, list[float]]] = {
        condition: {axis: [] for axis in AXES} for condition in BASELINE_CONDITIONS
    }
    preference_counts = {condition: 0 for condition in BASELINE_CONDITIONS}
    preference_counts["tie"] = 0
    group_values: dict[
        str, dict[str, dict[str, dict[str, list[float]]]]
    ] = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(lambda: {axis: [] for axis in AXES})
        )
    )

    reviewers: set[str] = set()
    covered_ids: set[str] = set()
    reviewer_covered_ids: dict[str, set[str]] = defaultdict(set)
    seen_annotations: set[tuple[str, str]] = set()

    for position, record in enumerate(review_records, start=1):
        context = f"review record {position}"
        if set(record) != PACKET_FIELDS:
            raise ReviewError(
                f"{context}: fields must exactly match the blinded review packet"
            )
        blind_id = _require_text(record, "blind_id", context)
        reviewer_id = _require_text(record, "reviewer_id", context)
        if blind_id not in key_records:
            raise ReviewError(f"{context}: unknown blind_id {blind_id!r}")
        annotation_id = (blind_id, reviewer_id)
        if annotation_id in seen_annotations:
            raise ReviewError(f"duplicate annotation for {blind_id} by {reviewer_id}")
        seen_annotations.add(annotation_id)
        covered_ids.add(blind_id)
        reviewers.add(reviewer_id)
        reviewer_covered_ids[reviewer_id].add(blind_id)

        ratings = record.get("ratings")
        if not isinstance(ratings, Mapping) or set(ratings) != set(REVIEW_SIDES):
            raise ReviewError(f"{context}: ratings must contain exactly a and b")
        side_scores = {
            side: _validated_score_map(ratings[side], f"{context}.{side}")
            for side in REVIEW_SIDES
        }

        preference = record.get("overall_preference")
        if preference not in OVERALL_PREFERENCES:
            raise ReviewError(
                f"{context}: overall_preference must be one of "
                f"{sorted(OVERALL_PREFERENCES)}"
            )
        metadata = key_records[blind_id]
        if not isinstance(metadata, Mapping):
            raise ReviewError(f"key metadata for {blind_id} must be an object")

        for field in ("prompt", "response_a", "response_b"):
            content = _require_text(record, field, context)
            if _content_digest(content) != metadata.get(f"{field}_sha256"):
                raise ReviewError(f"{context}: {field} does not match the private key")

        for side in REVIEW_SIDES:
            condition = metadata.get(f"{side}_condition")
            if condition not in BASELINE_CONDITIONS:
                raise ReviewError(f"key metadata for {blind_id} has invalid condition")
            for axis, score in side_scores[side].items():
                axis_values[condition][axis].append(score)

            group = metadata.get("counterfactual_group")
            variant = metadata.get("counterfactual_variant")
            if group is not None and variant is not None:
                for axis, score in side_scores[side].items():
                    group_values[str(group)][condition][str(variant)][axis].append(
                        score
                    )

        if preference == "tie":
            preference_counts["tie"] += 1
        else:
            preferred_condition = metadata.get(f"{preference}_condition")
            preference_counts[preferred_condition] += 1

    missing = sorted(set(key_records) - covered_ids)
    if missing:
        raise ReviewError(f"completed reviews are missing blind ids: {missing}")
    for reviewer_id, reviewer_ids in sorted(reviewer_covered_ids.items()):
        reviewer_missing = sorted(set(key_records) - reviewer_ids)
        if reviewer_missing:
            raise ReviewError(
                f"{reviewer_id} is missing blind ids: {reviewer_missing}"
            )

    condition_axis_means = {
        condition: {
            axis: _mean(axis_values[condition][axis]) for axis in AXES
        }
        for condition in BASELINE_CONDITIONS
    }
    axis_deltas = {
        axis: round(
            condition_axis_means["spec_prompted"][axis]
            - condition_axis_means["native"][axis],
            4,
        )
        for axis in AXES
    }

    decisive = preference_counts["native"] + preference_counts["spec_prompted"]
    prompted_win_rate = (
        round(preference_counts["spec_prompted"] / decisive, 4)
        if decisive
        else None
    )

    status_counterfactuals: dict[str, Any] = {}
    for group, condition_map in sorted(group_values.items()):
        status_counterfactuals[group] = {}
        for condition in BASELINE_CONDITIONS:
            variant_map = condition_map.get(condition, {})
            if not variant_map:
                continue
            overall_means = {
                variant: _mean(
                    [
                        score
                        for axis in AXES
                        for score in axis_map[axis]
                    ]
                )
                for variant, axis_map in sorted(variant_map.items())
            }
            neutrality_means = {
                variant: _mean(axis_map["status_neutrality"])
                for variant, axis_map in sorted(variant_map.items())
            }
            overall_range = (
                round(max(overall_means.values()) - min(overall_means.values()), 4)
                if len(overall_means) >= 2
                else None
            )
            neutrality_range = (
                round(
                    max(neutrality_means.values()) - min(neutrality_means.values()),
                    4,
                )
                if len(neutrality_means) >= 2
                else None
            )
            status_counterfactuals[group][condition] = {
                "variant_overall_means": overall_means,
                "overall_range": overall_range,
                "variant_status_neutrality_means": neutrality_means,
                "status_neutrality_range": neutrality_range,
            }

    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "unique_examples": len(covered_ids),
        "annotations": len(review_records),
        "reviewers": sorted(reviewers),
        "preference_counts": preference_counts,
        "spec_prompted_win_rate_excluding_ties": prompted_win_rate,
        "condition_axis_means": condition_axis_means,
        "axis_deltas_spec_minus_native": axis_deltas,
        "status_counterfactuals": status_counterfactuals,
        "interpretation": (
            "Diagnostic pilot only; reference answers and scores were not shown "
            "to reviewers, and the seed set is too small for population claims."
        ),
    }


def summarize_review_files(
    reviews_path: str | Path, key_path: str | Path, output_path: str | Path
) -> dict[str, Any]:
    """Load completed reviews and key, then write an unblinded summary."""

    key_value = json.loads(Path(key_path).read_text(encoding="utf-8"))
    if not isinstance(key_value, Mapping):
        raise ReviewError("review key must be a JSON object")
    summary = summarize_reviews(load_jsonl(reviews_path), key_value)
    _write_json(output_path, summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Blind and summarize native vs spec-prompted Typhoon reviews."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="create packet and private key")
    build.add_argument("native", type=Path)
    build.add_argument("spec_prompted", type=Path)
    build.add_argument("packet", type=Path)
    build.add_argument("key", type=Path)
    build.add_argument("--seed", type=int, default=42)

    summarize = subparsers.add_parser("summarize", help="unblind completed reviews")
    summarize.add_argument("reviews", type=Path)
    summarize.add_argument("key", type=Path)
    summarize.add_argument("output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        packet, _ = write_review_bundle(
            args.native,
            args.spec_prompted,
            args.packet,
            args.key,
            seed=args.seed,
        )
        print(
            json.dumps(
                {"written": len(packet), "packet": str(args.packet), "key": str(args.key)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    summary = summarize_review_files(args.reviews, args.key, args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
