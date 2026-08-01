"""Reproducible Typhoon baseline generation for JAI-Bench prompts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .prompts import BASELINE_CONDITIONS, BaselineCondition, build_messages
from .schemas import load_examples


DEFAULT_MODEL_ID = "typhoon-ai/llama3.2-typhoon2-1b-instruct"


@dataclass(frozen=True)
class GenerationConfig:
    """Generation settings recorded with every baseline response."""

    max_new_tokens: int = 256
    temperature: float = 0.4
    top_p: float = 0.9
    seed: int = 42

    def validate(self) -> None:
        if self.max_new_tokens <= 0:
            raise ValueError("max_new_tokens must be positive")
        if self.temperature < 0:
            raise ValueError("temperature cannot be negative")
        if not 0 < self.top_p <= 1:
            raise ValueError("top_p must be in (0, 1]")


class GenerationBackend(Protocol):
    """Minimal interface that keeps tests independent of model downloads."""

    model_id: str

    def generate(
        self, messages: Sequence[Mapping[str, str]], config: GenerationConfig
    ) -> str: ...


class TransformersBackend:
    """Local Hugging Face backend loaded only when a real run is requested."""

    def __init__(self, model_id: str = DEFAULT_MODEL_ID, device: str = "auto") -> None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                'baseline dependencies are missing; install with pip install -e ".[baseline]"'
            ) from exc

        self._torch = torch
        self.model_id = model_id
        self.device = self._resolve_device(device)
        dtype = self._resolve_dtype()

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=dtype)
        self.model.to(self.device)
        self.model.eval()

    def _resolve_device(self, requested: str) -> str:
        if requested != "auto":
            return requested
        if self._torch.cuda.is_available():
            return "cuda"
        if hasattr(self._torch.backends, "mps") and self._torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def _resolve_dtype(self):
        if self.device == "cuda":
            if self._torch.cuda.is_bf16_supported():
                return self._torch.bfloat16
            return self._torch.float16
        return self._torch.float32

    def generate(
        self, messages: Sequence[Mapping[str, str]], config: GenerationConfig
    ) -> str:
        config.validate()
        self._torch.manual_seed(config.seed)
        if self.device == "cuda":
            self._torch.cuda.manual_seed_all(config.seed)

        input_ids = self.tokenizer.apply_chat_template(
            list(messages), add_generation_prompt=True, return_tensors="pt"
        ).to(self.device)

        terminators = [self.tokenizer.eos_token_id]
        end_of_turn = self.tokenizer.convert_tokens_to_ids("<|eot_id|>")
        if end_of_turn is not None and end_of_turn != self.tokenizer.unk_token_id:
            terminators.append(end_of_turn)

        do_sample = config.temperature > 0
        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": config.max_new_tokens,
            "do_sample": do_sample,
            "eos_token_id": terminators,
            "pad_token_id": self.tokenizer.eos_token_id,
        }
        if do_sample:
            generation_kwargs.update(
                temperature=config.temperature,
                top_p=config.top_p,
            )

        with self._torch.inference_mode():
            output_ids = self.model.generate(input_ids, **generation_kwargs)

        response_ids = output_ids[0, input_ids.shape[-1] :]
        return self.tokenizer.decode(response_ids, skip_special_tokens=True).strip()


def run_baseline(
    examples: Sequence[Mapping[str, Any]],
    backend: GenerationBackend,
    condition: BaselineCondition,
    config: GenerationConfig,
    output_path: str | Path,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Generate responses and write contamination-resistant JSONL records."""

    config.validate()
    if condition not in BASELINE_CONDITIONS:
        raise ValueError(f"unknown baseline condition: {condition}")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive when supplied")

    selected = list(examples[:limit] if limit is not None else examples)
    records: list[dict[str, Any]] = []

    for example in selected:
        messages = build_messages(str(example["prompt"]), condition)
        response = backend.generate(messages, config)
        if not isinstance(response, str) or not response.strip():
            raise ValueError(f"backend returned an empty response for {example['id']}")

        records.append(
            {
                "example_id": example["id"],
                "category": example["category"],
                "language": example["language"],
                "condition": condition,
                "model_id": backend.model_id,
                "prompt": example["prompt"],
                "response": response.strip(),
                "generation": asdict(config),
            }
        )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a native or KrengJAI-prompted Typhoon baseline."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--condition", choices=BASELINE_CONDITIONS, required=True)
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    examples = load_examples(args.dataset)
    config = GenerationConfig(
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        seed=args.seed,
    )
    backend = TransformersBackend(model_id=args.model_id, device=args.device)
    records = run_baseline(
        examples=examples,
        backend=backend,
        condition=args.condition,
        config=config,
        output_path=args.output,
        limit=args.limit,
    )
    print(
        json.dumps(
            {
                "written": len(records),
                "condition": args.condition,
                "model_id": args.model_id,
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

