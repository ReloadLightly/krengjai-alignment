# Sprint 1: Typhoon baseline experiment

## Question

How does an unmodified Thai sovereign model behave on JAI-Bench before any SFT, DPO, reward modeling, or online RL?

## Controlled conditions

| Condition | Messages sent to Typhoon | What it measures |
|---|---|---|
| `native` | user prompt only | model behavior as released |
| `spec_prompted` | compact KrengJAI system instruction + identical user prompt | improvement available from prompting alone |

Future weight-updated models must be compared with both conditions. Beating only the native condition would not show that training was necessary.

## Installation on Windows

Start with a fresh virtual environment. The baseline extra installs PyTorch and Transformers, so the download is much larger than Sprint 0.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[baseline]"
```

The model is approximately one billion parameters. CPU execution is possible but slow; a supported GPU is preferable. The runner chooses CUDA automatically when available and otherwise falls back to CPU.

## Smoke test

Generate one response in each condition before running the entire seed set:

```powershell
python -m krengjai.baseline data/evals/jai_bench_seed.jsonl outputs/native-smoke.jsonl --condition native --limit 1
python -m krengjai.baseline data/evals/jai_bench_seed.jsonl outputs/spec-smoke.jsonl --condition spec_prompted --limit 1
```

Inspect both JSONL files before continuing.

## Full seed run

```powershell
python -m krengjai.baseline data/evals/jai_bench_seed.jsonl outputs/native-seed42.jsonl --condition native
python -m krengjai.baseline data/evals/jai_bench_seed.jsonl outputs/spec-seed42.jsonl --condition spec_prompted
```

Defaults follow the model card's low-temperature guidance for the 1B model:

- model: `typhoon-ai/llama3.2-typhoon2-1b-instruct`
- temperature: `0.4`
- top-p: `0.9`
- maximum new tokens: `256`
- random seed: `42`

All settings are stored in each output record.

## Why outputs omit reference answers

The generated records contain the prompt and model response but not the JAI-Bench `chosen`, `rejected`, or reference scores. This prevents accidental answer leakage into a later judge or human-review interface.

## Evaluation sequence

1. Confirm that all 20 generations complete: 10 native and 10 spec-prompted.
2. Use `python -m krengjai.review build` to blind condition and answer order.
3. Rate both responses on the eight Sprint 0 axes.
4. Record whether the factual correction or warning was preserved.
5. Compare the two status-counterfactual variants.
6. Document qualitative failures such as excessive particles, verbosity, deference, humiliation, or cultural essentialism.

With only 10 seed prompts, results are diagnostic rather than statistically conclusive. Their purpose is to reveal failure modes and improve the benchmark before expansion.

Follow the complete [blinded human-evaluation protocol](sprint1_evaluation.md).
It defines the scoring anchors, packet/key separation, integrity checks,
multi-reviewer procedure, unblinding command, and reporting limits.
