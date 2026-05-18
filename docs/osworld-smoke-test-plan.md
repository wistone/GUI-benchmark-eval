# OSWorld Smoke Test 计划

## 目的

在 full benchmark 前，smoke test 需要先回答三个问题：

1. 本地环境能否端到端执行 OSWorld 任务？
2. Codex/API 在当前 harness 下能否产出可用的 GUI 动作？
3. 真实 token、耗时和失败类型是什么样？

## 初始任务子集

先从 20 个任务开始。任务子集要覆盖常见桌面 workflow，避免被单一应用主导。

| Domain | 数量 | 选择理由 |
| --- | ---: | --- |
| LibreOffice Calc | 3 | 表格格式、公式、保存文件 |
| LibreOffice Writer / Impress | 4 | 文档和幻灯片编辑 |
| Chrome | 4 | 网页浏览、表单和信息查找 |
| VS Code | 3 | 编辑器和文件操作 |
| OS / file system | 2 | 基础桌面控制能力 |
| multi_apps | 3 | 长时序跨应用任务 |
| Thunderbird / VLC / GIMP | 1 | 覆盖边缘应用 |

## Baseline Run

优化前先跑一个简单 baseline：

- 固定模型
- 固定最大步数
- 固定屏幕分辨率
- 固定 observation type
- 固定 action schema
- 不加入 task-specific rescue logic

记录内容：

- pass/fail
- 使用步数
- input/output tokens
- wall-clock time
- 最终截图
- trajectory jsonl
- 失败类型

## 扩展门槛

- 20-task set 能稳定运行且没有明显环境问题后，再扩展到 50 个任务。
- 第一次优化对比完成后，再扩展到 100 个任务。
- 只有在存储、成本、耗时估算都验证后，才运行完整 361/369 任务。
