# NeurIPS Advanced Experiments and Rigor Spec

## Why
NeurIPS 审稿人需要更强的 baseline、更公平的预算控制、统计显著性证明（R=3 + CI）以及对核心机制（Evolution/Memory/Orchestration）的精细归因。本 Spec 旨在补齐实验缺口，从“跑通”转向“严谨证明”。

## What Changes
- **新增 Baseline 变体**: 实现 Plan-only, SOP (MetaGPT-style), Review-Revise (AFlow-style) 三类强基线。
- **故障注入机制**: 支持模拟 Timeout/Rate Limit 等环境异常，验证系统鲁棒性。
- **单技能回归评测**: 建立专门针对 Evolution 和 Memory 的细粒度评测集。
- **统计方法升级**: 强制 R=3 重复运行，并在汇总脚本中实现 Task-level Bootstrap 置信区间计算。
- **敏感性分析**: 支持对 ReAct baseline 进行 recursion_limit 扫描。

## Impact
- **Affected specs**: `strengthen-neurips-evaluation` (继承其基础开关，但扩展了更多变体)。
- **Affected code**: 
    - `src/agent.py`: 新增 baseline 逻辑与故障注入钩子。
    - `src/evaluation/complex_runner.py`: 支持多轮重复、故障注入模式与新变体环境。
    - `src/scripts/summarize_neurips_runs.py`: 升级统计口径。
    - `src/evaluation/skill_runner.py` (New): 单技能评测引擎。

## ADDED Requirements
### Requirement: 强 Baseline 体系
系统应支持以下对比项：
1. **Plan-only**: 保留 DAG 编排与验证，但禁用进化技能与记忆。
2. **SOP (MetaGPT-style)**: 顺序多角色工作流。
3. **Review-Revise (AFlow-style)**: 包含自省与修正环节的反馈循环。

### Requirement: 统计稳健性 (R=3 + CI)
- **WHEN**: 运行 complex benchmark。
- **THEN**: 每个任务必须独立重复 3 次，且汇总报告需基于任务维度进行 Bootstrap 抽样计算 95% 置信区间。

### Requirement: 鲁棒性注入
- **WHEN**: 启用 `FINAGENT_FAULT_INJECTION` 环境变量。
- **THEN**: 工具调用应有一定概率返回超时或限流错误，验证 Agent 的自愈与重试逻辑。

## MODIFIED Requirements
### Requirement: 消融实验口径统一
所有消融实验（Full, w/o Evo, w/o Mem）必须共享相同的工具集、预算限制与评测阈值（Judge Score >= 70）。
