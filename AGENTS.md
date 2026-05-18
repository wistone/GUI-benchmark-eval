# 项目 Agent 说明

这个仓库用于管理一个基于 Codex / API 的 GUI Agent 评测项目。短期目标是跑通 OSWorld / OSWorld-Verified 的 smoke test；长期目标是形成可复用的 GUI Agent 评测框架，并验证非模型层 harness 优化是否能稳定提升指标。

## 项目目标

1. 构建一个可复现的本地评测 harness，能够让 Codex/API-based agent 在 OSWorld 风格的 GUI 任务上运行，并生成接近官方报告形态的评测结果。
2. 评估完整系统，而不是只评估基础模型：包括 prompt、观测设计、动作格式、恢复逻辑、状态检查、历史管理和 evaluator 集成。
3. 保持优化方式诚实：优先做通用 harness 改进，不做基于 task id 的特化脚本或 benchmark hack。
4. 让每次运行都可审计：保留任务列表、模型版本、最大步数、prompt、轨迹、截图、分数、token 用量、耗时和失败原因。

## 仓库结构

- `README.md`：项目入口和当前状态。
- `docs/`：目标、实验设计、benchmark 笔记、运行报告和分析。
- `configs/`：小型配置文件，例如任务子集、模型设置和 harness 变体。
- `scripts/`：可复用脚本，例如环境检查、任务子集生成、报告聚合和分析。
- `datasets/`：只放轻量 manifest 和来源链接，不提交下载后的 benchmark 数据。
- `results/`：本地评测输出目录，只把很小的示例或摘要纳入 Git。
- `logs/`：临时日志目录，不提交原始长日志。
- `external/`：第三方仓库、VM 镜像、缓存和其他大型外部资产，不提交内容。

## Git 管理规则

- 提交规划文档、配置、脚本和小型汇总报告。
- 不提交 VM 镜像、模型 checkpoint、完整数据集、截图、视频、完整轨迹、API key 或原始结果目录。
- 如果某个大文件很重要，用 manifest 记录它的本地路径、来源 URL、checksum 和生成命令。
- 一旦某个 benchmark 子集用于对比，就要保持固定；如果要改任务组成，创建新的版本化子集。

## 评测原则

- 先建立 baseline：在优化前先跑一个最小可复现 harness。
- 尽量一次只改一个变量。
- 优先做 paired comparison：baseline 和优化版跑同一批任务。
- 同时记录成功率和运行指标：平均步数、token 用量、耗时、重试次数和失败类型。
- 区分 smoke test 结果和 leaderboard 风格结果。
- 明确标注人工检查或人工修复过的 run。

## 非模型优化范围

允许的优化例子：

- 改进 system prompt 和 action schema。
- 对比 screenshot、accessibility tree、OCR 等观测形式。
- 每个动作后做状态检查。
- 对弹窗、保存失败、窗口焦点错误、无效点击、滚动失败、卡死状态做通用恢复。
- 压缩历史和总结 trajectory。
- 为办公软件、浏览器、文件管理器、编辑器提供通用 app-level recipe。

为了公平评测，不允许：

- 根据精确 task id 分支，执行记忆化解法。
- 绕过 GUI/action 接口，直接编辑任务输出文件。
- 在 agent 执行过程中读取 gold/evaluator 文件。
- 把精挑细选的成功重试伪装成 first-attempt success。

## 当前工作假设

- 主 benchmark：OSWorld / OSWorld-Verified。
- 初始执行平台：MacBook Pro 14 英寸 2021，Apple M1 Pro，16GB RAM。
- 本地虚拟化优先路径：Apple Silicon 上使用 VMware Fusion。
- 正式实验推荐存储：外置 2TB SSD，格式化为 APFS。
- 初始实验规模：20-task smoke subset，稳定后再扩展到 50/100/full run。
