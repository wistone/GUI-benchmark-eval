# OSWorld Smoke Test Plan

## Purpose

The smoke test should answer three questions before any full benchmark run:

1. Can the local environment execute OSWorld tasks end to end?
2. Can Codex/API produce usable GUI actions under the harness?
3. What are the real token, time, and failure profiles?

## Initial Subset

Start with 20 tasks. The subset should cover common desktop workflows and avoid being dominated by one app.

| Domain | Count | Why |
| --- | ---: | --- |
| LibreOffice Calc | 3 | Spreadsheet formatting, formulas, saving |
| LibreOffice Writer / Impress | 4 | Office document editing |
| Chrome | 4 | Web browsing and form-like interaction |
| VS Code | 3 | Editor and file operations |
| OS / file system | 2 | Basic desktop control |
| multi_apps | 3 | Long-horizon cross-app tasks |
| Thunderbird / VLC / GIMP | 1 | Edge application coverage |

## Baseline Run

Use one simple baseline before optimization:

- fixed model
- fixed max steps
- fixed screen resolution
- fixed observation type
- fixed action schema
- no task-specific rescue logic

Record:

- pass/fail
- steps used
- input/output tokens
- wall-clock time
- final screenshot
- trajectory jsonl
- failure category

## Expansion Gates

- Expand to 50 tasks after the 20-task set can run without environment instability.
- Expand to 100 tasks after the first optimization comparison is completed.
- Run full 361/369 tasks only after storage, cost, and run-time estimates are validated.

