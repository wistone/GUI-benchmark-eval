# Project Goals

## Background

GUI agents are evaluated as systems, not just as base models. A useful OSWorld-style result depends on model capability, observation representation, action schema, execution environment, recovery logic, and evaluator reliability.

This project aims to make those pieces visible and measurable.

## Goal 1: Reproduce an Official-Style Report

Build a local Codex/API-based evaluation flow that can produce a report similar in shape to public benchmark reports:

- benchmark and task subset
- model and harness version
- observation and action settings
- max steps and retry policy
- success rate
- average steps per task
- token usage per task
- wall-clock time per task
- failure categories
- representative trajectories

The first target is not leaderboard equivalence. The first target is reproducibility and interpretability.

## Goal 2: Improve Scores Without Changing the Model

Investigate whether non-model harness changes can improve success rate:

- better observation packaging
- more reliable grounding and action formats
- state validation after each action
- generic recovery policies
- history compression
- app-level recipes
- end-of-task verification

This is a realistic direction because many GUI-agent failures are system failures: wrong focus, no-op click, missed popup, save dialog, scroll state, stale observation, or overlong history.

## Boundary

Fair optimization means improving the general agent system. It does not mean memorizing benchmark task ids, reading gold answers during execution, or bypassing the GUI interaction interface.

