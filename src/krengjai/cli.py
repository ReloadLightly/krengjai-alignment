"""Command-line interface for validating JAI-Bench data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .schemas import SchemaError, load_examples
from .scoring import summarize_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and summarize a KrengJAI JSONL evaluation dataset."
    )
    parser.add_argument("dataset", type=Path, help="path to a UTF-8 JSONL file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        examples = load_examples(args.dataset)
    except (OSError, SchemaError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summarize_dataset(examples), ensure_ascii=False, indent=2))
    return 0

