# Tasks
- [x] Task 1: 实现新 Baseline 变体 (Plan-only, SOP, Review-Revise)
  - [x] 在 `src/agent.py` 中新增 `FINAGENT_PLAN_ONLY` 环境支持，旁路进化技能库与记忆注入。
  - [x] 在 `src/agent.py` 中实现 MetaGPT-style SOP 流程 (Planner -> Executor -> Reviewer -> Writer)。
  - [x] 在 `src/agent.py` 中实现 AFlow-style 反馈流程 (Plan -> Execute -> Self-review -> Revise)。
  - [x] 在 `src/evaluation/complex_runner.py` 中注册对应变体名与环境变量映射。

- [x] Task 2: 实现故障注入与鲁棒性实验支持
  - [x] 在 `src/agent.py` 的工具调用核心层 (`execute_qveris_tool`, `tavily_search`) 中引入 `maybe_inject_fault` 钩子.
  - [x] 实现故障注入逻辑：按约 15% 概率随机触发 Timeout, Rate Limit, Invalid Output 等。
  - [x] 在 `complex_runner.py` 中支持 `fault_injection` 变体运行。

- [x] Task 3: 升级 Complex Runner 实现 R=3 与 统计一致性
  - [x] 确保 `complex_runner.py` 支持 `--repeat 3` 且正确生成 3 次 Trial 的 JSON 记录。
  - [x] 在 `run.json` 中完整记录每轮 Trial 的预算参数（recursion_limit, token_limit）。
  - [x] 确保解析失败、超时等 Failure Mode 统一归类（Planning/Execution/Analysis）。

- [x] Task 4: 实现单技能评测引擎 (Evolution & Memory)
  - [x] 创建 `benchmarks/skill_unit/` 目录，并构建 Evolution (Snapshot -> Schema) 与 Memory (错误复发场景) 评测样本。
  - [x] 实现 `src/evaluation/skill_runner.py`：支持对单个技能进行静态与进化后的对比测试。
  - [x] 统计指标：Schema Pass Rate、重复错误复发率。

- [x] Task 5: 升级汇总脚本并实现 Bootstrap CI
  - [x] 在 `src/scripts/summarize_neurips_runs.py` 中实现 Task-level Bootstrap 抽样（n=1000）。
  - [x] 统一导出 Paper-ready 格式的表格：Hard Success, Judge Success, Score (Mean ± CI)。
  - [x] 实现 ReAct 敏感性扫描的汇总展示。

# Task Dependencies
- Task 1 depends on `src/agent.py` 结构。
- Task 3 depends on Task 1。
- Task 5 depends on Task 3 的输出 Schema 统一。
