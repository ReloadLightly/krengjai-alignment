# Sprint 0 research design

## Research question

Can preference-based post-training improve context-sensitive Thai civility while preserving truthfulness, status neutrality, and general model capability?

## Falsifiable hypotheses

- **H1 — Preference learning:** DPO improves held-out human preference over the unmodified Typhoon baseline on KrengJAI scenarios.
- **H2 — Status robustness:** the aligned model has a smaller performance gap when senior and junior roles are swapped.
- **H3 — Non-sycophancy:** gains in surface respect do not reduce correction accuracy when a high-status speaker is wrong.
- **H4 — Retention:** post-training does not materially degrade Thai instruction following, English instruction following, or code-switching ability.
- **H5 — Method comparison:** an online-RL method and DPO produce measurably different trade-offs even when trained on related behavioral objectives.

No hypothesis is considered supported by reference scores alone. Final claims require held-out model generations and human judgments.

## Experimental ladder

### Stage A — measurement

1. Expand JAI-Bench from 10 seeds to at least 120 original prompts.
2. Add controlled counterfactuals: status, gender, age, institution, and urgency.
3. Obtain independent Thai annotations and written rationales.
4. Freeze a held-out test set before training.

### Stage B — baselines

- Generate responses from `typhoon-ai/llama3.2-typhoon2-1b-instruct`.
- Evaluate prompt-only character instructions separately from weight updates.
- Record latency, memory, generation configuration, and random seeds.

### Stage C — supervised and preference optimization

- Run LoRA SFT on the Typhoon2-1B base model using original demonstrations.
- Construct chosen/rejected pairs without reusing held-out prompts.
- Train DPO from the SFT checkpoint.
- Compare base, instruct, SFT, and DPO with blind evaluation.

### Stage D — reward learning and online RL

- Train a small pairwise reward model and test calibration across status swaps.
- Use rejection sampling before attempting online RL.
- Run a bounded GRPO/RL experiment only after rewards resist obvious gaming.
- Track KL divergence and general-capability retention.

### Stage E — sovereign post-training extension

- Reproduce a small, resource-aware analogue of Typhoon-S on-policy distillation.
- Investigate an InK-GRPO-style auxiliary language-modeling loss only with suitable compute.
- Treat the official multi-H100 recipe as a reference, not as a laptop-scale promise.

## Evaluation metrics

| Metric | Purpose |
|---|---|
| Blind pairwise win rate | Overall behavioral preference |
| Mean score per axis | Detects trade-offs hidden by one aggregate score |
| Status-swap gap | Measures hierarchy-conditioned behavior |
| Correction accuracy | Detects polite but false agreement |
| Warning salience | Detects indirectness that hides urgent action |
| Cultural-essentialism rate | Measures unsupported universal claims |
| Thai/English retention delta | Detects catastrophic forgetting |
| Annotator agreement | Quantifies ambiguity rather than erasing it |
| KL divergence from reference | Tracks behavioral drift during optimization |

Confidence intervals and annotator-level results should accompany headline averages. An aggregate “Thai alignment score” must never be reported without the component scores.

## Annotation protocol

1. Randomize answer order and hide model identity.
2. Collect an overall preference and eight separate 0–4 ratings.
3. Ask annotators to distinguish unacceptable behavior from mere stylistic preference.
4. Preserve rationales and disagreement.
5. Include reviewers from varied generations, regions, genders, and professional settings.
6. Adjudicate only after independent ratings are recorded.

## Threats to validity

- Seed scenarios may reflect the project authors more than Thai society.
- LLM-generated preferences may reproduce the judge model's style biases.
- Politeness markers can make weak answers appear culturally competent.
- A 1B model may lack factual or linguistic capacity independent of alignment.
- Training and evaluation templates may leak into one another.
- Status swaps may change pragmatics in ways that require qualitative interpretation.

## Sprint 0 exit criteria

- All seed rows pass the machine-readable schema.
- Every chosen response has a positive reference-score margin.
- At least one paired status counterfactual is present.
- Tests run without model downloads or paid APIs.
- Documentation clearly labels the data as unvalidated and not training-ready.

