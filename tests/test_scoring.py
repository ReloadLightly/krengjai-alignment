from copy import deepcopy
import unittest

from krengjai import AXES, SchemaError, validate_example, weighted_score


def valid_example() -> dict:
    scores = {axis: 4 for axis in AXES}
    return {
        "id": "example_001",
        "language": "th",
        "category": "test",
        "prompt": "ทดสอบ",
        "chosen": "คำตอบที่ดีกว่า",
        "rejected": "คำตอบที่แย่กว่า",
        "risk_tags": ["test"],
        "review_status": "needs_native_review",
        "reference_scores": {
            "chosen": scores,
            "rejected": {axis: 0 for axis in AXES},
        },
    }


class ScoringTests(unittest.TestCase):
    def test_equal_weight_score_is_axis_mean(self) -> None:
        scores = {axis: index % 5 for index, axis in enumerate(AXES)}
        self.assertAlmostEqual(weighted_score(scores), sum(scores.values()) / 8)

    def test_missing_axis_is_rejected(self) -> None:
        scores = {axis: 3 for axis in AXES[:-1]}
        with self.assertRaises(ValueError):
            weighted_score(scores)

    def test_out_of_range_reference_score_is_rejected(self) -> None:
        example = deepcopy(valid_example())
        example["reference_scores"]["chosen"]["respect"] = 5
        with self.assertRaises(SchemaError):
            validate_example(example)

    def test_orphan_counterfactual_field_is_rejected(self) -> None:
        example = deepcopy(valid_example())
        example["counterfactual_group"] = "group_without_variant"
        with self.assertRaises(SchemaError):
            validate_example(example)


if __name__ == "__main__":
    unittest.main()

