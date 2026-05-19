# Scripts

这里存放 GUI benchmark eval 的本地运行脚本。

## OSWorld Smoke Tests

### 1. 基础设施 smoke

验证 VMware Fusion、Ubuntu VM、截图、GUI action 和 evaluator 管道是否可用。这个测试不使用 OSWorld 原始任务。

```bash
cd /Users/shijianping/Work/GUI-benchmark-eval
source external/OSWorld/.venv/bin/activate
python scripts/osworld_vm_smoke.py \
  --headless \
  --path-to-vm external/OSWorld/vmware_vm_data/Ubuntu0/Ubuntu0.vmx
```

通过标准：

- 输出 `evaluator_score=1.0`
- 截图写入 `results/osworld_smoke/screenshot.png`

### 2. 数据集 smoke

验证真实 OSWorld JSON 任务能完成 `reset/setup -> screenshot -> action -> evaluator`。这个测试不要求 agent 解题，所以多数任务 `score=0` 是正常的；关键看每个 domain 的 `status=ok`。

```bash
cd /Users/shijianping/Work/GUI-benchmark-eval
source external/OSWorld/.venv/bin/activate
python scripts/osworld_dataset_smoke.py --headless
```

只跑部分 domain：

```bash
python scripts/osworld_dataset_smoke.py --headless --domains os,vlc,vs_code
```

结果文件：

- `results/osworld_dataset_smoke/summary.json`
- `results/osworld_dataset_smoke/<domain>/<task_id>/initial_state.png`

## OSWorld + Local Codex Agent

`scripts/osworld_codex_eval.py` 通过本机 Codex CLI 调 OSWorld 任务：

```text
OSWorld task JSON
  -> DesktopEnv.reset(task_config)
  -> screenshot
  -> codex exec predicts one pyautogui action
  -> DesktopEnv.step(action)
  -> DesktopEnv.evaluate()
```

先跑一个短任务：

```bash
cd /Users/shijianping/Work/GUI-benchmark-eval
source external/OSWorld/.venv/bin/activate
python scripts/osworld_codex_eval.py \
  --headless \
  --domains os
```

指定 Codex 模型：

```bash
python scripts/osworld_codex_eval.py \
  --headless \
  --domains os,vlc,vs_code \
  --max-steps 15 \
  --model gpt-5.4
```

结果文件：

- `results/osworld_codex_eval/summary.json`
- `results/osworld_codex_eval/<domain>/<task_id>/traj.jsonl`
- `results/osworld_codex_eval/<domain>/<task_id>/step_*.png`
- `results/osworld_codex_eval/<domain>/<task_id>/result.txt`

注意事项：

- 需要已有 VMware 快照 `init_state`。
- `score` 才是任务解题评测结果，`status=ok` 只代表运行链路没有崩。
- Codex runner 每一步调用一次 `codex exec`，速度会比内置 API agent 慢。
- 当前 Codex runner 默认每个 OSWorld domain 抽 1 个样例，共 10 个任务。
