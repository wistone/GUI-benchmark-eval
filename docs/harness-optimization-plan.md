# Harness 优化计划

## 核心假设

对 GUI Agent 来说，非模型层系统设计会显著影响 benchmark 成功率。所有优化都应该在同一任务子集上做 paired comparison，而不是只看单次总分。

## 优化阶梯

| 版本 | 改动 | 预期收益 | 主要风险 |
| --- | --- | --- | --- |
| v0 | 最小 baseline | 建立参考线 | 分数偏低 |
| v1 | 清理 prompt 和 action schema | 减少无效动作和 no-op | 对模型约束过强 |
| v2 | 对比 screenshot、a11y tree、OCR 等观测形式 | 提升 grounding 和 UI 理解 | token 用量上升 |
| v3 | 每个动作后做状态检查 | 捕捉点击失败、状态未变化、旧截图 | 调用次数和耗时增加 |
| v4 | 通用恢复策略 | 从弹窗、焦点错误、保存对话框中恢复 | 可能滑向 benchmark hack |
| v5 | 历史压缩 | 降低 token 成本，减少上下文污染 | 丢失有用历史 |
| v6 | 通用 app recipe | 提升 Office、浏览器、编辑器任务稳定性 | 设计过于 hand-crafted |
| v7 | 任务结束前自检 | 减少过早 DONE | 步数增加 |

## 失败类型 taxonomy

报告中使用这些失败类型：

- 环境或安装失败
- 模型理解任务错误
- 视觉 grounding 错误
- 应用或窗口焦点错误
- 无效动作或 no-op
- 滚动/导航遗漏
- 弹窗或对话框处理失败
- 文件保存/导出失败
- 过早宣布 DONE
- evaluator 不匹配或任务歧义
- token、时间或步数预算耗尽

## 报告规则

每个优化版本都需要报告：

- 任务集合版本
- baseline 分数
- optimized 分数
- 从 pass 变 fail、从 fail 变 pass 的任务 id
- token 和耗时变化
- 主要变化的失败类型
