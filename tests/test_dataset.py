from pathlib import Path
import unittest

from krengjai import load_examples, preference_margin, summarize_dataset


ROOT = Path(__file__).resolve().parents[1]
SEED_DATA = ROOT / "data" / "evals" / "jai_bench_seed.jsonl"


class SeedDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.examples = load_examples(SEED_DATA)

    def test_seed_dataset_has_expected_size(self) -> None:
        self.assertEqual(len(self.examples), 10)

    def test_every_reference_margin_is_positive(self) -> None:
        for example in self.examples:
            with self.subTest(example=example["id"]):
                self.assertGreater(preference_margin(example), 0)

    def test_status_counterfactual_has_two_variants(self) -> None:
        variants = {
            example.get("counterfactual_variant")
            for example in self.examples
            if example.get("counterfactual_group")
            == "workplace_status_correction_001"
        }
        self.assertEqual(
            variants, {"junior_corrects_senior", "senior_corrects_junior"}
        )

    def test_summary_exposes_review_and_language_coverage(self) -> None:
        summary = summarize_dataset(self.examples)
        self.assertEqual(summary["needs_native_review"], 10)
        self.assertEqual(summary["positive_reference_margins"], 10)
        self.assertEqual(summary["counterfactual_groups"], 1)
        self.assertEqual(set(summary["languages"]), {"en", "th", "th-en"})
        self.assertGreaterEqual(len(summary["categories"]), 8)


if __name__ == "__main__":
    unittest.main()

