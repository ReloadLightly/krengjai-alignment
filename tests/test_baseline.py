import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from krengjai.baseline import GenerationConfig, run_baseline


class FakeBackend:
    model_id = "fake/typhoon"

    def __init__(self) -> None:
        self.messages = []

    def generate(self, messages, config) -> str:
        self.messages.append(messages)
        return f"response-{len(self.messages)}"


EXAMPLES = [
    {
        "id": "one",
        "category": "respectful_disagreement",
        "language": "th",
        "prompt": "คำถามหนึ่ง",
    },
    {
        "id": "two",
        "category": "status_neutrality",
        "language": "en",
        "prompt": "Question two",
    },
]


class BaselineTests(unittest.TestCase):
    def test_native_condition_has_no_system_message(self) -> None:
        backend = FakeBackend()
        with TemporaryDirectory() as directory:
            output = Path(directory) / "native.jsonl"
            records = run_baseline(
                EXAMPLES,
                backend,
                "native",
                GenerationConfig(),
                output,
            )
        self.assertEqual(len(records), 2)
        self.assertEqual([message["role"] for message in backend.messages[0]], ["user"])

    def test_spec_condition_adds_system_message_and_respects_limit(self) -> None:
        backend = FakeBackend()
        with TemporaryDirectory() as directory:
            output = Path(directory) / "spec.jsonl"
            records = run_baseline(
                EXAMPLES,
                backend,
                "spec_prompted",
                GenerationConfig(seed=7),
                output,
                limit=1,
            )
            written = [json.loads(line) for line in output.read_text("utf-8").splitlines()]

        self.assertEqual(len(records), 1)
        self.assertEqual(
            [message["role"] for message in backend.messages[0]], ["system", "user"]
        )
        self.assertEqual(written[0]["condition"], "spec_prompted")
        self.assertEqual(written[0]["generation"]["seed"], 7)
        self.assertNotIn("chosen", written[0])
        self.assertNotIn("rejected", written[0])

    def test_invalid_generation_config_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            GenerationConfig(top_p=0).validate()


if __name__ == "__main__":
    unittest.main()

