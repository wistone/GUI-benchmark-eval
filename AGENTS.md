# Project Agent Notes

This repo tracks a Codex-based GUI agent evaluation project. The near-term target is OSWorld / OSWorld-Verified smoke testing; the broader target is reusable GUI agent evaluation and non-model harness optimization.

## Project Goals

1. Build a reproducible local evaluation harness that can run Codex/API-based agents on OSWorld-style GUI tasks and produce an official-report-like summary.
2. Measure the full system, not only the base model: prompt, observation design, action schema, recovery logic, state checking, history management, and evaluator integration.
3. Keep the optimization honest: prefer general harness improvements over task-id-specific scripts or benchmark hacks.
4. Make every run auditable: preserve task list, model version, max steps, prompts, trajectories, screenshots, scores, token usage, wall-clock time, and failure reason.

## Repo Structure

- `README.md`: project entrypoint and current status.
- `docs/`: goals, experiment design, benchmark notes, run reports, and analysis.
- `configs/`: small config files for task subsets, model settings, and harness variants.
- `scripts/`: reusable scripts for setup, subset generation, report aggregation, and analysis.
- `datasets/`: lightweight manifests and links only. Do not commit downloaded benchmark data.
- `results/`: local evaluation outputs. Keep only tiny examples or summaries in Git.
- `logs/`: transient logs. Do not commit raw long logs.
- `external/`: cloned third-party repos, VM images, caches, and other large external assets. Do not commit.

## Git Policy

- Commit plans, configs, scripts, and small summary reports.
- Do not commit VM images, model checkpoints, dataset dumps, screenshots, videos, full trajectories, API keys, or raw result folders.
- If a large artifact is important, store its path, source URL, checksum, and generation command in a manifest.
- Keep benchmark subsets fixed once used for comparisons; create a new versioned subset when changing task composition.

## Evaluation Principles

- Baseline first: run a minimal, reproducible harness before adding optimizations.
- Change one variable at a time when possible.
- Prefer paired comparison: run baseline and optimized harness on the same task set.
- Track both success rate and operational metrics: average steps, token usage, wall time, retry count, and failure type.
- Separate smoke-test results from leaderboard-style results.
- Mark any manually inspected or manually repaired run clearly.

## Non-Model Optimization Scope

Allowed examples:

- Better system prompt and action schema.
- Screenshot plus accessibility tree or OCR observation variants.
- State checks after actions.
- Generic recovery for popups, failed saves, wrong focus, no-op clicks, scroll failures, and stuck states.
- History compression and trajectory summarization.
- Generic app-level recipes for office apps, browsers, file managers, and editors.

Disallowed for fair evaluation:

- Branching on exact task id to run a memorized solution.
- Directly editing task output files outside the intended GUI/action interface.
- Using gold/evaluator files during the agent run.
- Reporting cherry-picked successful retries as first-attempt success.

## Current Working Assumptions

- Primary benchmark: OSWorld / OSWorld-Verified.
- Initial execution platform: MacBook Pro 14-inch 2021, Apple M1 Pro, 16GB RAM.
- Preferred local virtualization path: VMware Fusion on Apple Silicon.
- Preferred storage for serious experiments: external 2TB SSD formatted as APFS.
- Initial experiment size: 20-task smoke subset before expanding to 50/100/full runs.

