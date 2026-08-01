# JAI-Bench Seed data card

## Purpose

`data/evals/jai_bench_seed.jsonl` is a machine-readable seed set for developing KrengJAI's schema, scoring tools, and human annotation protocol.

## Current contents

- 10 original preference examples;
- Thai, English, and Thai–English code-switching;
- eight 0–4 reference axes for each chosen and rejected response;
- one paired senior/junior status counterfactual;
- scenarios involving workplace, family, public service, gender, religion, safety, and cross-cultural explanation.

## Provenance

The scenarios are newly authored for this repository. They are conceptually informed by research questions arising from Patrick Jory's history of Thai manners and from the RLHF/post-training literature. No passage from Jory's book is included or paraphrased as training material.

## Critical limitation

The Thai text and all reference ratings require native-speaker review. The seed set must not be represented as a validated benchmark, a survey of Thai values, or production training data.

## Intended use

- schema and tooling development;
- annotation-pilot design;
- baseline model-error discovery;
- counterfactual test development.

## Out-of-scope use

- claims about a homogeneous Thai culture;
- production deployment decisions;
- high-stakes automated judgments about individuals;
- training before contamination-safe evaluation splits exist.

