# 后续实验与文章改进计划（技能编排主线）

## Summary（摘要）
本计划以“**单技能证明 Evolution/Memory 的自我改进优势 + 多技能证明动态编排的鲁棒性优势**”为主线，补齐 NeurIPS 主会审稿最关心的：强 baseline、公平预算、R=3 重复与 task-level CI、以及将 workflow/agentic 相关工作（MetaGPT/AFlow）纳入对比叙事与 baseline 设计。

## Current State Analysis（现状分析）
### 论文现状
- 新版 PDF 已具备：N=20 complex orchestration、cache-at-time（QVeris cache）、LLM-as-judge（Qwen3.6-plus, T=0）、工具 ID/Schema、消融与 case study、FinBen N=82、InvestorBench 指标。
- 主要缺口（按审稿风险排序）：
  1) 复杂编排仍存在“单次运行口径/统计不稳”的风险：需要明确并落地 **每任务 R=3 + task-level bootstrap CI**（且确保论文、run.json、汇总脚本三者口径一致）。
  2) 需要更强 baseline 来归因：至少加入 **Plan-only baseline**（保留 plan+execute+verification，去掉 evolution/memory/skill library）。
  3) 需要把“单技能上不显著”从弱点变成叙事：单技能实验专门衡量 **Evolution/Memory** 的收益；多技能实验衡量 **Orchestration** 的收益。
  4) baseline 的预算/recursion_limit 容易被攻击：需统一预算约束并做敏感性扫描。

### 代码/评测现状（关键文件）
- 复杂编排评测：`src/evaluation/complex_runner.py`（支持 variants、QVeris cache stats、judge logs，但默认每任务单次）。
- Judge：`src/evaluation/judge.py`（需确保 judge-success 计算字段稳定，如 `fabrication_detected`）。
- 汇总与 CI：`src/scripts/summarize_neurips_runs.py`（已有 task-level bootstrap 思路，但需要与 runner 输出 schema 对齐，避免论文数字矛盾）。
- Agent：`src/agent.py`（实现 orchestrator、evolution、memory；需要新增 plan-only / SOP baseline 等入口）。

### 外部相关工作（用于 baseline/叙事）
- MetaGPT：将 SOP/多角色装配线式 workflow 用于提升复杂任务一致性与降低级联错误（https://arxiv.org/abs/2308.00352；https://github.com/FoundationAgents/MetaGPT）。
- AFlow：把 workflow 优化视为“可组合 operator 的搜索”，用反馈驱动迭代改进 workflow（https://arxiv.org/abs/2410.10762；https://github.com/FoundationAgents/AFlow）。

## Assumptions & Decisions（假设与决策）
- 评测范围：同时覆盖 **单技能**（Evolution/Memory）与 **多技能**（Orchestration）。
- 模型可用性：可稳定跑 **Qwen + GPT-4o**（用于强 baseline/上界对比），judge 固定一个模型以减少口径漂移。
- 复杂编排：采用 **每任务 R=3**；统计使用 **task-level bootstrap CI**（避免把 trial 当独立样本夸大 N）。
- baseline 方向：主 baseline 为 **Plan-only**；并在相关工作对齐 MetaGPT/AFlow 的 workflow 思路（不要求复现其完整框架，但 baseline 设计要“同类可比”）。

## Proposed Changes（拟做改动：文件级 + 实验级）

### A) 多技能实验：Complex orchestration（动态编排优势）
**目标**：在多技能任务上证明动态编排（plan+DAG+verification）带来 success/robustness 的主要增益，并把 evolution/memory 的增益分离出来。

**需要新增/完善的对比项**
1) **Plan-only baseline（必须）**  
   - 定义：保留 JSON plan + DAG 执行 + verification（Python 数值核验、schema 校验、retry），但禁用 evolution 与 procedural memory 注入，并避免调用自定义“skill prompt genotype”路径（只用工具/固定提示）。
   - 产出：与 Full/ablation 同 schema 的 run.json + judge_logs + 表格。
2) **Recursion/budget sensitivity（必须）**  
   - 对 ReAct baseline 做 recursion_limit 扫描（例如 10/15/25/50）或改成统一预算（max tool calls / max wall-clock / max tokens），报告敏感性表/图。
3) **鲁棒性注入（建议）**  
   - 在 N=20 中选 5–10 个任务做故障注入（timeout/rate limit/missing field），比较 Full vs Plan-only vs ReAct 的恢复能力与成本。

**涉及文件**
- `src/agent.py`：新增 `run_plan_only_orchestrator_with_logs()` 或 baseline 分支（不走 evolve/memory/skill library）。
- `src/evaluation/complex_runner.py`：新增/扩展 Variant（plan_only_baseline），并支持 `--repeat 3`、记录预算参数、写入 task-level 汇总。
- `src/scripts/summarize_neurips_runs.py`：确保对 v2 schema 做 task-level bootstrap CI，并生成 paper-ready 表（hard/judge success + score + cost）。
- `neurips_paper/main.tex`：表格与叙述中加入 Plan-only baseline；将 orchestration 优势归因写清楚。

### B) 单技能实验：Evolution / Memory（自我改进优势）
**目标**：在“单技能/短链路”场景中，证明 evolution 和 memory 的收益主要体现在：格式合规、数值可信、错误恢复与重复错误减少，而不是端到端长链 success。

**单技能实验设计（最小可发表集）**
1) **Evolution 单技能 regression suite**  
   - 选 1–2 个关键 skill（或 1 个 data/analysis + 1 个 execution），构建固定输入（来自工具输出 snapshot）→固定输出 schema（JSON）的小任务集。
   - 对比：static vs evolution（迭代 0/1/2 轮）  
   - 指标：schema pass rate、缺字段率、unverified numbers、judge score（可选）。
2) **Memory 单技能重复失败模式任务**  
   - 构造一组连续任务，刻意触发同类失败（缺字段/需要 fallback/单位不一致/需 python 计算），比较 memory on/off 在后续任务上的“复发率”和成本。
   - 指标：hard-success、错误复发率、平均工具调用数、平均耗时、抽象出的 procedural rules 数量与示例。

**涉及文件**
- 新增评测脚本（建议）：`src/evaluation/skill_runner.py`（仿 complex_runner，但不调用实时 API；只读取本地 snapshot）。
- 新增/扩展数据：`benchmarks/skill_unit/*.json`（固定输入/固定期望 schema）。
- `src/core/memory.py` / `src/core/evolution.py`：确保抽象阈值与日志可追踪（规则文本、触发条件、使用次数）。
- `neurips_paper/main.tex`：新增 “Single-skill Improvement” 小节（2 个小表 + 1 个 case）。

### C) workflow 强 baseline（对齐 MetaGPT / AFlow）
**目标**：回应“workflow/agentic 编排”领域的强方法，至少提供一个“同类可比”的 baseline，不一定复现其全系统，但在工作流形态上对齐。

1) **MetaGPT-style SOP baseline（建议）**  
   - 串行多角色：Planner→Executor→Reviewer→Writer（同工具集同预算），不含 evolution/memory。  
2) **AFlow-inspired review&revise baseline（建议）**  
   - Generate plan→Execute→Self-review→Revise（允许一次局部重规划或 best-of-k 计划选择）。  

**涉及文件**
- `src/agent.py`：新增 `run_sop_baseline_with_logs()`、`run_review_revise_baseline_with_logs()`。
- `src/evaluation/complex_runner.py`：新增 baseline 变体并纳入统一表格汇总。
- `neurips_paper/main.tex`：Related Work 与 Baselines 段落补充 MetaGPT/AFlow 引用，并解释我们与其差异（技能演化/程序规则/验证执行）。

### D) 统计与口径（全篇统一，避免“数字打架”）
**目标**：让论文中所有核心数字都能从同一份 run.json/summary 自动导出，避免口径漂移。

1) 统一 success 双指标并报：  
   - hard-success（运行成功）  
   - judge-success（score≥阈值且 fabrication_detected=False）  
2) 强制 R=3 并在 run.json 写入 task-level summary（均值+CI），脚本只做二次汇总而非重新定义口径。  
3) judge 输出字段兜底：确保 `fabrication_detected` 等字段永远存在（解析失败也给默认值），避免 judge-success 无法计算。

**涉及文件**
- `src/evaluation/complex_runner.py`、`src/evaluation/judge.py`、`src/scripts/summarize_neurips_runs.py`、`neurips_paper/main.tex`

## Assumptions & Decisions（可选项，需要执行前确定）
- judge-success 阈值：建议在论文固定为一个值（例如 60 或 70），并在附录说明敏感性（可选）。
- “工具层确定性 vs LLM 层随机性”：推荐保持工具输出确定（cache-at-time），而在 LLM 侧通过 seed/温度或 best-of-k 体现稳定性（需要与成本预算匹配）。

## Verification（验证步骤）
1) **口径一致性**：论文表格中的 success/score 与 run.json 的 task-level summary 一致，且脚本导出可复现。
2) **R=3 生效**：每个 task 记录 3 个 trial；judge_logs 行数约等于 N×R（在 judge enabled 时）。
3) **CI 正确**：bootstrap 在 task 维度做，不把 trial 当独立样本；输出 hard/judge success 与 score 的 CI。
4) **baseline 公平性**：所有 baseline 与 Full 共享工具集合、cache、timeout/retry 预算；recursion_limit 作为预算的一部分写入 run.json。
5) **归因清晰**：  
   - 单技能实验：展示 evolution/memory 的提升曲线或复发率下降；  
   - 多技能实验：展示 Plan-only 与 Full 的差距归因于 evolution/memory；w/o orchestration 归因于动态编排缺失。

