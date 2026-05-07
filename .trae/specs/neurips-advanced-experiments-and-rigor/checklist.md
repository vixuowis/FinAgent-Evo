# Checklist
- [x] Plan-only baseline 运行成功且确认禁用了进化与记忆 (is_plan_only = True)
- [x] SOP baseline 成功调用 Planner -> Executor -> Reviewer -> Writer 完整链路
- [x] Review-Revise baseline 成功执行 Self-review 与修正逻辑
- [x] ReAct baseline 支持通过 `react_limit_N` 变体进行步数敏感性测试
- [x] 故障注入模式 (`fault_injection`) 下有 10--20% 概率触发超时/限流错误
- [x] Complex Runner 能够稳定执行 R=3 次 Trial 并记录到同一 run.json
- [x] Summarize 脚本成功输出 Task-level Bootstrap 95% 置信区间 (± N.N%)
- [x] 单技能评测引擎能够区分 Static 与 Evolved 技能并汇报 Schema Pass Rate
- [x] 论文中的核心指标 (Hard/Judge Success, Score) 已更新为 Mean ± CI 格式
