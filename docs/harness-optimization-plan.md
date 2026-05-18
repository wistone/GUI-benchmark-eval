# Harness Optimization Plan

## Core Hypothesis

For GUI agents, non-model system choices can materially affect benchmark success rate. Improvements should be measured by paired comparisons against the same task subset.

## Optimization Ladder

| Version | Change | Expected Benefit | Main Risk |
| --- | --- | --- | --- |
| v0 | Minimal baseline | Establish reference | Low score |
| v1 | Prompt and action schema cleanup | Fewer invalid/no-op actions | Over-constraining model |
| v2 | Observation variants: screenshot, a11y tree, OCR | Better grounding and UI understanding | More tokens |
| v3 | State check after each action | Catch failed clicks and stale states | Extra calls/time |
| v4 | Generic recovery policies | Recover from popups, wrong focus, save dialogs | Hidden benchmark hacks |
| v5 | History compression | Lower token cost and reduce confusion | Losing useful context |
| v6 | Generic app recipes | More stable office/browser/editor workflows | Too much hand design |
| v7 | End-of-task self-check | Reduce premature DONE | More steps |

## Failure Taxonomy

Use these categories in reports:

- environment/setup failure
- model instruction misunderstanding
- visual grounding failure
- wrong app/window focus
- no-op or invalid action
- missing scroll/navigation
- dialog/popup handling failure
- file save/export failure
- premature done
- evaluator mismatch or ambiguous task
- token/time/step budget exhaustion

## Reporting Rule

For each optimization, report:

- task set version
- baseline score
- optimized score
- pass-to-fail and fail-to-pass task ids
- token and time delta
- top changed failure modes

