# GUI Benchmark Eval

这个仓库用于整理和推进一个基于 Codex / API 的 GUI Agent 评测项目。第一阶段重点是 OSWorld / OSWorld-Verified；长期目标是通过可复现实验理解 GUI Agent 系统，并探索非模型层 harness 优化。

## 为什么建这个项目

项目有两个核心目标：

1. 在本地复现一个接近官方报告形态的评测流程：固定任务集合、固定模型设置、保存 trajectory、分数、token 用量、耗时和失败类型。
2. 探索不改模型参数的系统优化是否能提升 GUI 任务成功率：包括观测设计、prompt/action schema、状态检查、恢复策略、历史管理和通用 app recipe。

## 当前计划

1. 构建一个 20-task OSWorld smoke subset。
2. 先跑最小 baseline harness。
3. 生成第一份报告：成功率、平均步数、token、耗时、失败分类。
4. 每次只加入一个 harness 优化，并做 paired comparison。
5. 在 smoke subset 稳定后，再扩展到 50、100，最后考虑 full benchmark。

## 重要路径

- `docs/project-goals.md`：项目目标和边界。
- `docs/osworld-smoke-test-plan.md`：第一批任务子集和迭代设计。
- `docs/harness-optimization-plan.md`：非模型 harness 优化路线。
- `configs/`：任务子集和运行配置。
- `scripts/`：环境检查、报告聚合等辅助脚本。
- `datasets/`、`results/`、`logs/`、`external/`：本地工作目录，大文件默认被 Git 忽略。

## 大文件规则

不要提交 benchmark 下载文件、VM 镜像、截图、录屏、完整 trajectory 或原始结果目录。需要追踪来源时，用 manifest 记录来源链接、本地路径和 checksum。
