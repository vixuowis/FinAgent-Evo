# Strengthen NeurIPS Evaluation Spec

## Why
当前论文评审指出实验验证不足、消融缺失、LLM-as-a-Judge 不透明、可复现性弱且对 ReAct baseline 的对比可能存在偏差。需要补齐实验与评估基础设施，使结果可解释、可复现、可对比，并支持论文后续补写。

## What Changes
- 增加针对复杂多技能编排任务的**系统性消融**：W/O Evolution、W/O Hierarchical Memory、W/O Dynamic Orchestration
- 增加**评测基准描述与统计信息**导出能力（任务数量、技能依赖分布、任务类型分布、难度分桶）
- 规范并固化 **LLM-as-a-Judge**：明确 judge 模型、prompt、输出 schema，记录 judge 输入/输出，支持复验
- 增加 **Judge 校准**：小样本人评对齐（人类评分/一致性）与 judge 相关性分析（例如 Spearman）
- 修订并固化 **ReAct baseline** 设置，确保对比公平（工具集、递归限制、错误处理、重试策略一致化）
- 增加 **成本与稳定性度量**：token/耗时/API 次数、失败模式分类、非确定性来源记录（实时 API 时间戳/缓存）
- 将上述实验产物输出为结构化结果文件，便于论文表格/图表复用

## Impact
- Affected specs: 复杂编排评测、消融研究、judge 评估协议、可复现性与成本分析
- Affected code: `src/agent.py`（开关/变体注入）、`src/tests/evaluate_complex_orchestration.py`（评测与记录增强）、`src/scripts/*`（批量跑分/统计/对比）

## ADDED Requirements

### Requirement: Ablation Variants
系统 SHALL 支持对复杂多技能编排评测运行以下变体，并输出独立结果文件：
- W/O Evolution（禁用 `evolve_skill` / skill mutation 路径，不新增变异技能）
- W/O Hierarchical Memory（不写入/不抽象 procedural rules，planner 不注入 rules）
- W/O Dynamic Orchestration（跳过 `multi_skill_orchestrator` 的 JSON plan + 执行链路，改为固定顺序或单次 agent 直接回答的 baseline 变体）

#### Scenario: Success case
- **WHEN** 用户以相同任务集运行 4 种配置（Full / 三个 ablation）
- **THEN** 产出 4 份结构一致的结果 JSON，包含每个任务的输出、轨迹、评分、耗时与失败原因

### Requirement: Benchmark Statistics Export
系统 SHALL 为指定任务集输出可复现的统计信息：
- 任务数、平均步骤数（或计划步数）、所需技能集合分布
- DAG 依赖深度/宽度分布（若任务定义含 DAG 或可从 plan/trajectory 推断）
- 任务类型标签分布（若任务定义包含标签；否则从 required_skills / query pattern 进行轻量归类）

#### Scenario: Success case
- **WHEN** 用户对 `benchmarks/complex_tasks*.json` 运行统计脚本
- **THEN** 输出 JSON/Markdown 统计摘要，并可用于论文 “Benchmark” 小节

### Requirement: Judge Protocol Transparency
系统 SHALL 固化并记录 judge 配置与可复验材料：
- judge 模型名、base_url、temperature、seed（如可用）
- judge prompt 模板版本号（hash）
- 每个任务的 judge 输入（task、criteria、agent output）与 judge 输出（原文与解析后 JSON）

#### Scenario: Success case
- **WHEN** 跑 complex orchestration 评测
- **THEN** 每个任务都生成对应的 judge 日志条目，且可离线重放解析

### Requirement: Judge Calibration (Human Alignment)
系统 SHALL 支持抽样任务进行人类评分，并计算与 judge 分数的一致性/相关性。

#### Scenario: Success case
- **WHEN** 用户提供一份人评标注文件（任务 id → 分数/标签）
- **THEN** 输出相关性指标与偏差分析摘要

### Requirement: Fair Baseline Configuration
系统 SHALL 明确并固定 ReAct baseline 的配置，并与 Full/ablation 在以下维度保持可比：
- 工具可用性（同一组数据工具 + python 计算工具）
- 统一的重试/超时策略与错误记录
- 一致的输入任务集、相同的输出 schema

#### Scenario: Success case
- **WHEN** 用户运行 baseline
- **THEN** baseline 结果文件与 FinAgent-Evo 结果文件字段对齐，可直接对比与聚合统计

### Requirement: Cost & Failure Mode Reporting
系统 SHALL 在每次评测中记录并汇总：
- 任务级别：耗时、工具调用次数、失败阶段（规划/执行/计算/汇总/judge）
- 汇总级别：成功率、平均耗时、P50/P90、主要失败类型 Top-K

#### Scenario: Success case
- **WHEN** 评测结束
- **THEN** 生成 summary 段落与结构化 summary JSON

## MODIFIED Requirements

### Requirement: Complex Orchestration Evaluation Output
现有复杂编排评测输出 SHALL 扩展为可复验格式（包含 judge 配置、任务统计、失败模式与成本度量），且保持向后兼容（旧字段不删除）。

## REMOVED Requirements

### Requirement: Reporting Tiny FinBen Samples as “Benchmark”
**Reason**: 3 条样本不具统计意义，容易被 reviewer 视为误导性结果。
**Migration**: 将其降级为 “sanity check”，或替换为 `FinBen-100`/更大样本并报告置信区间。
