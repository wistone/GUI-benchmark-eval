# Harness Iteration Log - 2026-05-25

## Target
Reach 75 overall on full OSWorld by iterating only generic harness behavior.

## Iteration V3 Quick Sanity
- Prompt version: `docs/harness_versions/harness_v3_20260525.md`
- Eval scope: `configs/osworld_harness_v3_quick_sanity_5.json`
- Sample count: 5
- Max steps: 50
- Retry on no evaluator result: 1
- Purpose: validate V3 direction before 30/100/full runs.
- Expected duration: 25-45 minutes on local single VM.

## Planned escalation
- If 5-task sanity has no environment errors and does not regress the known historical-correct Calc task, run 30-task tactical set.
- If tactical set improves V2 failure categories while keeping historical-correct retention above 90%, run 100-task stratified set.
- Full 369-task run only after 100-task result is directionally near or above 70%.

## Result - V3 Quick Sanity 5
- Run id: `harness_v3_sanity5_20260525_141415`
- Started: `2026-05-25T14:14:16+08:00`
- Finished: `2026-05-25T15:00:49.980667+08:00`
- Duration: `46.6 minutes`
- Scope: `configs/osworld_harness_v3_quick_sanity_5.json`
- Accuracy: `1.000/5 = 20.0%`
- Outcome: reject V3 for scaling. It regressed preserved infeasible detection and did not fix the known Calc regression.

| Domain | Task | Bucket | V2 | V3 | Note |
|---|---|---:|---:|---:|---|
| `libreoffice_calc` | `01b269ae-2111-4a07-81fd-3fcd711993b0` | `v2_regression_from_historical_correct` | `0.0` | `0.0` | Still over-operated on exact range fill; failed to reduce V2 regression. |
| `chrome` | `480bcfea-d68f-4aaa-a0a9-2589ef319381` | `preserve_infeasible_detection` | `1.0` | `0.0` | V3 over-corrected away from FAIL and toggled unrelated appearance setting; lost V2 infeasible win. |
| `vlc` | `8f080098-ddb1-424c-b438-4e96e5e4786e` | `media_file_verification` | `0.0` | `0.0` | Still failed media conversion; output MP3 missing after 50 steps. |
| `vs_code` | `930fdb3b-11a8-46fe-9bac-577332e2640e` | `shortcut_behavior_verification` | `0.0` | `1.0` | Improved from V2 0 to 1 by writing/testing keybindings JSON. |
| `multi_apps` | `0e5303d4-8820-42f6-b18d-daf7e633de21` | `multi_app_download_verification` | `0.0` | `0.0` | Still failed long download set; did not verify filesystem enough before max step. |

## Result - V3.1 Quick Sanity 5
- Run id: `harness_v3_1_sanity5_20260525_150547`
- Prompt version: `docs/harness_versions/harness_v3_1_20260525.md`
- Started: `2026-05-25T15:05:47+08:00`
- Finished: `2026-05-25T15:32:20.227878+08:00`
- Duration: `26.6 minutes`
- Accuracy: `1.986/5 = 39.7%`
- Outcome: better than V3 and V2 on this sanity set, but still not safe to scale to 30 tasks. It preserves infeasible FAIL and improves VLC media verification, but fails Calc exact range, VS Code shortcut, and multi-app downloads.

| Domain | Task | Bucket | V2 | V3.1 | Interpretation |
|---|---|---:|---:|---:|---|
| `libreoffice_calc` | `01b269ae-2111-4a07-81fd-3fcd711993b0` | `v2_regression_from_historical_correct` | `0.0` | `0.0` | Still fails exact range-fill; prompt alone is not inducing the correct Calc operation. |
| `chrome` | `480bcfea-d68f-4aaa-a0a9-2589ef319381` | `preserve_infeasible_detection` | `1.0` | `1.0` | Recovered V2 infeasible behavior; V3.1 correctly returns FAIL instead of changing adjacent settings. |
| `vlc` | `8f080098-ddb1-424c-b438-4e96e5e4786e` | `media_file_verification` | `0.0` | `0.9862891477068727` | Large improvement; media verification plus fallback conversion produced a near-full score. |
| `vs_code` | `930fdb3b-11a8-46fe-9bac-577332e2640e` | `shortcut_behavior_verification` | `0.0` | `0.0` | Lost the V3 win; UI shortcut editing path still unreliable without stronger keybindings-file playbook. |
| `multi_apps` | `0e5303d4-8820-42f6-b18d-daf7e633de21` | `multi_app_download_verification` | `0.0` | `0.0` | Still too long and incomplete; needs a download-set playbook and possibly lower-level filesystem verification earlier. |

## Decision after V3.1
- Do not run 30-task tactical set yet.
- Next iteration should be V3.2 with small, typed playbooks rather than more generic prose.
- V3.2 target fixes: exact-range Calc operation, VS Code keybindings JSON path, multi-file download filesystem verification. Preserve V3.1 infeasible and media gains.

## Result - V3.2 Quick Sanity 5
- Run id: `harness_v3_2_sanity5_20260525_154426`
- Prompt version: `docs/harness_versions/harness_v3_2_20260525.md`
- Scope: `configs/osworld_harness_v3_quick_sanity_5.json`
- Accuracy: `1.986/5 = 39.7%`
- Outcome: do not scale. V3.2 preserved V3.1 behavior but did not fix the three remaining failure buckets.

| Domain | Task | Bucket | V3.1 | V3.2 | Interpretation |
|---|---|---:|---:|---:|---|
| `libreoffice_calc` | `01b269ae-2111-4a07-81fd-3fcd711993b0` | `v2_regression_from_historical_correct` | `0.0` | `0.0` | The agent filled only some visible B/C runs and missed full B1:E30 coverage. |
| `chrome` | `480bcfea-d68f-4aaa-a0a9-2589ef319381` | `preserve_infeasible_detection` | `1.0` | `1.0` | Infeasible behavior remains correct. |
| `vlc` | `8f080098-ddb1-424c-b438-4e96e5e4786e` | `media_file_verification` | `0.986` | `0.986` | Media fallback remains effective. |
| `vs_code` | `930fdb3b-11a8-46fe-9bac-577332e2640e` | `shortcut_behavior_verification` | `0.0` | `0.0` | GUI JSON editing produced an invalid/uncertain file state. Needs config-file validation/repair. |
| `multi_apps` | `0e5303d4-8820-42f6-b18d-daf7e633de21` | `multi_app_download_verification` | `0.0` | `0.0` | GUI download loop hit max steps before complete file-set verification. |

## Decision after V3.2
- Do not run 30/100-task evaluation yet.
- Next iteration is V3.3: keep generic typed playbooks, but route structured file/config/download tasks toward VM-visible artifact verification and repair when GUI-only progress stalls.

## Result - V3.3 Quick Sanity 5
- Run id: `harness_v3_3_sanity5_20260525_162845`
- Prompt version: `docs/harness_versions/harness_v3_3_20260525.md`
- Scope: `configs/osworld_harness_v3_quick_sanity_5.json`
- Runtime: `34.1 minutes`
- Accuracy: `3.987/5 = 79.7%`
- Outcome: pass the 5-task sanity gate. V3.3 fixes the Calc and VS Code regressions, preserves Chrome infeasible behavior, and preserves near-full VLC media behavior. Multi-app download-set remains the main unresolved bucket.

| Domain | Task | Bucket | V3.2 | V3.3 | Interpretation |
|---|---|---:|---:|---:|---|
| `libreoffice_calc` | `01b269ae-2111-4a07-81fd-3fcd711993b0` | `v2_regression_from_historical_correct` | `0.0` | `1.0` | Structured workbook repair inside the requested range fixed the known Calc regression. |
| `chrome` | `480bcfea-d68f-4aaa-a0a9-2589ef319381` | `preserve_infeasible_detection` | `1.0` | `1.0` | Infeasible behavior remains correct. |
| `vlc` | `8f080098-ddb1-424c-b438-4e96e5e4786e` | `media_file_verification` | `0.986` | `0.987` | Media fallback remains stable and near-full. |
| `vs_code` | `930fdb3b-11a8-46fe-9bac-577332e2640e` | `shortcut_behavior_verification` | `0.0` | `1.0` | V3.3 recovered exact keybindings behavior. |
| `multi_apps` | `0e5303d4-8820-42f6-b18d-daf7e633de21` | `multi_app_download_verification` | `0.0` | `0.0` | Still spends too many steps on GUI/manual URL downloads and does not complete the expected file set. |

## Decision after V3.3
- V3.3 is good enough for a larger tactical run.
- Next unresolved iteration target: make download-set tasks switch earlier to VM Terminal link enumeration/download plus folder completeness verification.

## Planned V3.4 Quick Sanity 5
- Prompt version: `docs/harness_versions/harness_v3_4_20260525.md`
- Scope: same 5 high-signal tasks.
- Single variable changed from V3.3: stricter generic download-set rule for bulk numbered file downloads.
- Gate: preserve the four V3.3 wins and improve the multi-app download-set task, or at least avoid regression.

## Result - V3.4 Quick Sanity 5
- Run id: `harness_v3_4_sanity5_20260525_171400`
- Runtime: `23.2 minutes`
- Accuracy: `3.987/5 = 79.7%`
- Outcome: no score improvement over V3.3. It preserved Calc, Chrome, VLC, and VS Code, but still failed the multi-app download-set task.

| Domain | V3.3 | V3.4 | Interpretation |
|---|---:|---:|---|
| `libreoffice_calc` | `1.0` | `1.0` | Preserved structured workbook repair. |
| `chrome` | `1.0` | `1.0` | Preserved infeasible handling. |
| `vlc` | `0.987` | `0.987` | Preserved media fallback. |
| `vs_code` | `1.0` | `1.0` | Preserved exact keybindings result. |
| `multi_apps` | `0.0` | `0.0` | The stricter prompt was not strong enough: the agent still used browser/manual downloads and stopped early without folder completeness verification. |

## Decision after V3.4
- Keep V3.4 as the current prompt because it does not regress the sanity set, but do not claim it fixes download sets.
- Next prompt-only idea for downloads would need a hard early-switch rule, not a soft recommendation.
- For broader evaluation, V3.4 is acceptable for a 30-task tactical run, with multi-app download failures tracked as a known open category.

## Running - V3.4 Tactical 30
- Run id: `harness_v3_4_tactical30_20260525_174056`
- Prompt version: `docs/harness_versions/harness_v3_4_20260525.md`
- Scope: `configs/osworld_harness_v3_4_tactical_30.json`
- Strategy: 3 tasks per domain, mixing historical wrong/high-signal tasks, historical retention tasks, and cold-start coverage.
- Expected duration: about `2.5-3.5 hours` on single local VM.
