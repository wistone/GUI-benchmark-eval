# 项目目标

## 背景

GUI Agent 评测的是完整系统，而不只是基础模型。一个有意义的 OSWorld 风格结果，取决于模型能力、观测表示、动作格式、执行环境、恢复逻辑和 evaluator 可靠性。

这个项目的目标，就是把这些组件拆开、记录下来，并让它们可以被测量。

## 目标一：复现官方风格报告

构建一个基于本地 Codex/API 的评测流程，输出形态尽量接近公开 benchmark 报告：

- benchmark 和任务子集
- 模型版本和 harness 版本
- observation 和 action 设置
- max steps 和 retry 策略
- 成功率
- 平均每题步数
- 平均每题 token 用量
- 平均每题耗时
- 失败类型
- 代表性 trajectory

第一阶段目标不是 leaderboard 等价，而是可复现和可解释。

## 目标二：不改模型，提升系统指标

验证非模型层 harness 改动能否提升成功率：

- 更好的观测打包方式
- 更可靠的 grounding 和 action 格式
- 每个动作后的状态校验
- 通用恢复策略
- 历史压缩
- app-level recipe
- 任务结束前自检

这是一个现实方向，因为很多 GUI Agent 失败不是模型“完全不会”，而是系统层失败：窗口焦点错、无效点击、漏掉弹窗、保存对话框、滚动状态、旧截图、历史过长等。

## 边界

公平优化意味着改进通用 agent system，而不是记忆 benchmark task id、在执行时读取 gold answer，或绕过 GUI 交互接口直接修改输出文件。
