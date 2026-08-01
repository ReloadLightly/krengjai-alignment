# KrengJAI

> **Respect without servility. Harmony without sycophancy.**

KrengJAI is a research and engineering lab for historically informed character alignment of Thai sovereign language models. The project asks:

> Can a Thai language model learn context-sensitive civility without learning submissive agreement, status bias, evasiveness, or cultural stereotypes?

The name comes from *kreng jai* (เกรงใจ): a socially important but difficult-to-translate Thai concept involving consideration, restraint, and reluctance to impose on others. That ambiguity is the research problem—not a behavior that the model should maximize unconditionally.

## Sprint 0: evaluation before optimization

Sprint 0 establishes the measurement foundation required before fine-tuning:

- a provisional [KrengJAI Model Spec](spec/krengjai_model_spec.md);
- `JAI-Bench Seed`, an original set of Thai, English, and code-switched preference scenarios;
- a dependency-free schema validator and transparent multi-axis reference scorer;
- counterfactual status tests for hierarchy bias and sycophancy;
- unit tests and continuous integration;
- a [research design](docs/research_design.md) and [RLHF course map](docs/course_map.md).

This seed data is **not yet training data** and is **not a validated Thai benchmark**. Every Thai example is marked for native-speaker review.

## Quick start

Python 3.10 or newer is required.

```powershell
git clone https://github.com/ReloadLightly/krengjai-alignment.git
cd krengjai-alignment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m krengjai data/evals/jai_bench_seed.jsonl
python -m unittest discover -s tests -v
```

The validator reports dataset composition and verifies that every preference pair contains all eight behavioral axes with scores in the allowed range.

## Sprint 1: Typhoon baseline

Sprint 1 compares the released Typhoon2-1B-Instruct model under two controlled conditions: the native model receives only the user prompt, while the prompted condition also receives a compact KrengJAI behavior instruction. This establishes whether later weight updates outperform prompt engineering rather than merely outperforming an intentionally weak baseline.

Install the optional model dependencies and start with one prompt:

```powershell
python -m pip install -e ".[baseline]"
python -m krengjai.baseline data/evals/jai_bench_seed.jsonl outputs/native-smoke.jsonl --condition native --limit 1
python -m krengjai.baseline data/evals/jai_bench_seed.jsonl outputs/spec-smoke.jsonl --condition spec_prompted --limit 1
```

See the complete [Sprint 1 baseline runbook](docs/sprint1_baseline.md) before running all prompts. Generated outputs are ignored by Git and do not contain the reference preference answers.

## Behavioral axes

Each candidate response is evaluated from 0 to 4 on:

1. respect;
2. truthfulness;
3. constructive disagreement;
4. status neutrality;
5. non-sycophancy;
6. clarity;
7. calibrated directness;
8. cultural sensitivity.

These axes are deliberately separate. A response can be linguistically polite but untruthful, warm but sycophantic, or direct but needlessly humiliating.

## Post-training roadmap

| Stage | Model or method | Main question |
|---|---|---|
| 0 | Model spec + JAI-Bench | Can we define and measure the intended behavior? |
| 1 | Typhoon2-1B baselines | What failure modes already exist? |
| 2 | LoRA supervised fine-tuning | Can original demonstrations teach the behavior? |
| 3 | DPO with Thai preference pairs | Does preference optimization improve held-out behavior? |
| 4 | Reward model + rejection sampling | Can a learned reward generalize without amplifying status bias? |
| 5 | Small online-RL experiment | What is gained or lost relative to DPO? |
| 6 | Typhoon-S-inspired OPD/InK-GRPO | Can sovereign capability be improved without forgetting? |

The project uses “RLHF and post-training” as the umbrella. Individual experiments will be labelled precisely: SFT is fine-tuning, DPO is direct preference optimization, RLAIF uses AI-generated feedback, and canonical RLHF additionally uses a learned reward and an online RL stage.

## Intellectual and data safeguards

Patrick Jory's *A History of Manners and Civility in Thailand* motivates questions about the historical formation of manners, hierarchy, self-restraint, gender, and political power. The book is **not copied into this dataset**. All seed scenarios are newly authored, and the project rejects the idea of a single timeless or homogeneous Thai character.

The project should eventually be reviewed by multiple native Thai annotators with varied regional, generational, gender, and professional backgrounds. Negative results and reward-hacking cases will be reported rather than hidden.

## Primary references

- Nathan Lambert, [*Reinforcement Learning from Human Feedback*](https://rlhfbook.com/) and the accompanying [course](https://rlhfbook.com/course)
- Kunat Pipatanakul and Pittawat Taveekitworachai, [Typhoon-S](https://github.com/scb-10x/typhoon-s)
- Patrick Jory, [*A History of Manners and Civility in Thailand*](https://www.cambridge.org/core/books/history-of-manners-and-civility-in-thailand/71AEC2676F3E2FA29FA57AE936830146)
- Typhoon AI, [Llama3.2-Typhoon2-1B-Instruct](https://huggingface.co/typhoon-ai/llama3.2-typhoon2-1b-instruct)
