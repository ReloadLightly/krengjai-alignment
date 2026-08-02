import copy
import unittest

from krengjai.review import ReviewError, build_review_pack, summarize_reviews
from krengjai.schemas import AXES


GENERATION = {
    "max_new_tokens": 256,
    "temperature": 0.4,
    "top_p": 0.9,
    "seed": 42,
}


def baseline_records(condition):
    return [
        {
            "example_id": "status-a",
            "category": "respectful_disagreement",
            "language": "th",
            "risk_tags": ["status_bias"],
            "counterfactual_group": "status-pair",
            "counterfactual_variant": "junior_corrects_senior",
            "condition": condition,
            "model_id": "fake/typhoon",
            "prompt": "Prompt A",
            "response": f"{condition} response A",
            "generation": dict(GENERATION),
        },
        {
            "example_id": "status-b",
            "category": "respectful_disagreement",
            "language": "th",
            "risk_tags": ["status_bias"],
            "counterfactual_group": "status-pair",
            "counterfactual_variant": "senior_corrects_junior",
            "condition": condition,
            "model_id": "fake/typhoon",
            "prompt": "Prompt B",
            "response": f"{condition} response B",
            "generation": dict(GENERATION),
        },
    ]


class ReviewTests(unittest.TestCase):
    def test_review_pack_is_deterministic_and_blinded(self) -> None:
        packet, key = build_review_pack(
            baseline_records("native"), baseline_records("spec_prompted"), seed=7
        )
        repeated_packet, repeated_key = build_review_pack(
            baseline_records("native"), baseline_records("spec_prompted"), seed=7
        )

        self.assertEqual(packet, repeated_packet)
        self.assertEqual(key, repeated_key)
        self.assertEqual(len(packet), 2)
        for row in packet:
            self.assertEqual(
                set(row),
                {
                    "blind_id",
                    "prompt",
                    "response_a",
                    "response_b",
                    "ratings",
                    "overall_preference",
                    "rationale",
                    "reviewer_id",
                },
            )
            self.assertEqual(set(row["ratings"]), {"a", "b"})
            self.assertEqual(set(row["ratings"]["a"]), set(AXES))
            self.assertNotIn("condition", row)
            self.assertNotIn("model_id", row)
            self.assertNotIn("generation", row)
            self.assertNotIn("example_id", row)

        for metadata in key["records"].values():
            self.assertEqual(
                {metadata["a_condition"], metadata["b_condition"]},
                {"native", "spec_prompted"},
            )

    def test_reference_answer_leak_is_rejected(self) -> None:
        native = baseline_records("native")
        native[0]["chosen"] = "reference answer"
        with self.assertRaisesRegex(ReviewError, "reference fields leaked"):
            build_review_pack(native, baseline_records("spec_prompted"))

    def test_uncontrolled_generation_mismatch_is_rejected(self) -> None:
        prompted = baseline_records("spec_prompted")
        prompted[0]["generation"]["temperature"] = 0.8
        with self.assertRaisesRegex(ReviewError, "generation settings differ"):
            build_review_pack(baseline_records("native"), prompted)

    def test_orphan_counterfactual_metadata_is_rejected(self) -> None:
        native = baseline_records("native")
        native[0]["counterfactual_variant"] = None
        with self.assertRaisesRegex(ReviewError, "must appear together"):
            build_review_pack(native, baseline_records("spec_prompted"))

    def test_completed_reviews_are_unblinded_and_summarized(self) -> None:
        packet, key = build_review_pack(
            baseline_records("native"), baseline_records("spec_prompted")
        )
        completed = copy.deepcopy(packet)
        for row in completed:
            metadata = key["records"][row["blind_id"]]
            for side in ("a", "b"):
                condition = metadata[f"{side}_condition"]
                value = 4 if condition == "spec_prompted" else 2
                row["ratings"][side] = {axis: value for axis in AXES}
            row["overall_preference"] = (
                "a" if metadata["a_condition"] == "spec_prompted" else "b"
            )
            row["reviewer_id"] = "reviewer-01"
            row["rationale"] = "The preferred response was clearer."

        summary = summarize_reviews(completed, key)
        self.assertEqual(summary["unique_examples"], 2)
        self.assertEqual(summary["annotations"], 2)
        self.assertEqual(summary["reviewers"], ["reviewer-01"])
        self.assertEqual(summary["preference_counts"]["spec_prompted"], 2)
        self.assertEqual(summary["spec_prompted_win_rate_excluding_ties"], 1.0)
        self.assertEqual(
            set(summary["axis_deltas_spec_minus_native"].values()), {2.0}
        )
        status = summary["status_counterfactuals"]["status-pair"]
        self.assertEqual(status["native"]["overall_range"], 0.0)
        self.assertEqual(status["spec_prompted"]["status_neutrality_range"], 0.0)

    def test_incomplete_reviews_are_rejected(self) -> None:
        packet, key = build_review_pack(
            baseline_records("native"), baseline_records("spec_prompted")
        )
        completed = copy.deepcopy(packet)
        for row in completed:
            row["reviewer_id"] = "reviewer-01"
            row["overall_preference"] = "tie"
            for side in ("a", "b"):
                row["ratings"][side] = {axis: 2 for axis in AXES}
        completed[0]["ratings"]["a"]["respect"] = None

        with self.assertRaisesRegex(ReviewError, "respect must be numeric"):
            summarize_reviews(completed, key)

    def test_edited_response_is_rejected_before_unblinding(self) -> None:
        packet, key = build_review_pack(
            baseline_records("native"), baseline_records("spec_prompted")
        )
        completed = copy.deepcopy(packet)
        for row in completed:
            row["reviewer_id"] = "reviewer-01"
            row["overall_preference"] = "tie"
            for side in ("a", "b"):
                row["ratings"][side] = {axis: 2 for axis in AXES}
        completed[0]["response_a"] += " edited"

        with self.assertRaisesRegex(ReviewError, "does not match the private key"):
            summarize_reviews(completed, key)

    def test_every_reviewer_must_complete_the_full_packet(self) -> None:
        packet, key = build_review_pack(
            baseline_records("native"), baseline_records("spec_prompted")
        )
        completed = copy.deepcopy(packet)
        for row in completed:
            row["reviewer_id"] = "reviewer-01"
            row["overall_preference"] = "tie"
            for side in ("a", "b"):
                row["ratings"][side] = {axis: 2 for axis in AXES}

        partial_second_reviewer = copy.deepcopy(completed[0])
        partial_second_reviewer["reviewer_id"] = "reviewer-02"
        completed.append(partial_second_reviewer)

        with self.assertRaisesRegex(ReviewError, "reviewer-02 is missing blind ids"):
            summarize_reviews(completed, key)


if __name__ == "__main__":
    unittest.main()
