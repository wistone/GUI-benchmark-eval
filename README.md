# Codex GUI Agent Eval

This repo is for organizing a Codex/API-based GUI agent evaluation project. The first benchmark focus is OSWorld / OSWorld-Verified; the longer-term focus is understanding and improving GUI agent systems through reproducible harness experiments.

## Why This Exists

The project has two goals:

1. Reproduce an official-report-like evaluation flow locally: fixed task set, fixed model settings, trajectories, scores, token usage, run time, and failure taxonomy.
2. Explore non-model improvements that can improve GUI task success rate: observation design, prompt/action schema, state checks, recovery, history management, and generic app recipes.

## Current Plan

1. Build a 20-task OSWorld smoke subset.
2. Run a minimal baseline harness.
3. Produce a first report with success rate, average steps, tokens, wall time, and failure categories.
4. Add one harness improvement at a time and run paired comparisons.
5. Expand to 50, 100, then full benchmark only after the smoke subset is stable.

## Important Paths

- `docs/project-goals.md`: goal statement and project boundaries.
- `docs/osworld-smoke-test-plan.md`: first subset and iteration design.
- `docs/harness-optimization-plan.md`: non-model optimization roadmap.
- `configs/`: task subset and run configs.
- `scripts/`: setup/reporting helpers.
- `datasets/`, `results/`, `logs/`, `external/`: local working directories with large files ignored by Git.

## Large Files

Do not commit benchmark downloads, VM images, screenshots, recordings, full trajectories, or raw result directories. Store source links and manifests instead.

