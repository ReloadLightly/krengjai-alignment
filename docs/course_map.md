# Nathan Lambert course → KrengJAI implementation map

KrengJAI follows the concepts in the [RLHF Book and course](https://rlhfbook.com/course) while keeping each method's name precise.

| Course material | Pen-and-paper focus | KrengJAI artifact |
|---|---|---|
| Lecture 0: ML foundations | probabilities, log-probabilities, entropy, cross-entropy, KL | calculate tiny token examples; later inspect SFT loss and KL drift |
| Lecture 1: overview | post-training pipeline and terminology | experimental ladder and method labels |
| Lecture 2: IFT, reward models, rejection sampling | pairwise likelihood and reward ranking | SFT demonstrations, preference schema, small reward model |
| Lectures 3–4: RL math and implementation | return, advantage, policy gradient, loss aggregation | bounded online-RL experiment after reward validation |
| Lecture 5: reasoning and RLVR | verifiable versus subjective rewards | separate factual correction from subjective tone ratings |
| Lecture 6: DPO | chosen/rejected log-probability ratios | Typhoon LoRA-DPO experiment |
| Lecture 7: synthetic data and modern post-training | RLAIF, rubrics, on-policy distillation | rubric-guided candidates and a small OPD reproduction |
| Lecture 8: preference data | whose preferences and which aggregation rule | Thai annotation protocol and disagreement analysis |
| Lecture 9: overoptimization | Goodhart's law, reward hacking, sycophancy | status-swap, verbosity, particle-stuffing, and judge-bias tests |
| Lecture 10: regularization | KL penalty and capability retention | KL/retention dashboard across checkpoints |

## Learning rule

Each stage should produce four things:

1. one worked numerical example on paper;
2. one small implementation;
3. one empirical result;
4. one explanation of how the method can fail.

The repository should never present DPO as online RL or AI preferences as human feedback. The umbrella is modern LLM post-training; the experiment label must state the actual data and optimizer used.

