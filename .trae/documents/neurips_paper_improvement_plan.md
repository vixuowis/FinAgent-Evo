# NeurIPS 主会改进计划（论文 + 实验脚本）

## Summary（目标概述）
为 FinAgent-Evo 的 NeurIPS 主会投稿把“审稿可防守点”落实到**论文叙述 + 可复现实验**两端：  
1) 复杂编排 benchmark 的定义与评测协议达到可复验标准；  
2) 成功口径采用**双指标并报**：Hard-success（运行硬成功）+ Judge-success（裁判达标成功）；  
3) 复杂编排 benchmark 采用 **每任务 R=3 次重复**，并在任务层面做 bootstrap CI；  
4) baseline 公平性（tool/budget parity）与 recursion_limit 敏感性用实验支撑；  
5) 输出 paper-ready 结果表、失败模式统计与可发布资产（缓存/日志/benchmark card/工具 schema）。

## Current State Analysis（现状）
### 论文（`neurips_paper/main.tex` & `main.pdf`）
- 新版 PDF 已包含：
  - 复杂编排 benchmark：N=20、cache-at-time、QVeris MCP 工具、judge=Qwen3.6-plus temperature=0、消融表（w/o Memory / w/o Evolution / w/o Orchestration）、case studies、FinBen N=82、InvestorBench 表。
- 仍存在 NeurIPS 审稿风险点：
  - 复杂编排评测目前是“每任务跑一次”的口径需要升级为 **R=3 + CI**；
  - success 定义需升级为**双指标并报**（hard-success + judge-success）并与代码一致；
  - ReAct baseline 的 recursion_limit 需要“预算约束统一化”与敏感性扫描，避免被认为人为卡 baseline；
  - w/o Memory 出现 success 更高但分数更低等现象需要在论文解释 success 与 score 的关系。

### 代码与评测
关键实现点已具备但需扩展：
- `src/evaluation/complex_runner.py`：已有 Full/ablation/react baseline 变体、QVeris cache stats、judge logs；当前每任务单次 trial。
- `src/evaluation/judge.py`：有结构化输出解析与兜底，但需确保 `fabrication_detected` 等字段稳定存在，以便计算 judge-success。
- `src/core/qveris_cache.py`：存在 cache-at-time 机制（文件 cache keyed by tool_id+params）。
- `src/scripts/summarize_neurips_runs.py`：已有 bootstrap 工具函数雏形，但需要改成“按 task 聚合 + 双成功指标 + CI”。

### 相关 specs
- 评测基础设施补强：`.trae/specs/strengthen-neurips-evaluation/*`（消融入口、judge 透明度、失败模式与成本统计等）
- 主会改稿执行清单：`.trae/specs/neurips-main-paper-improvement/*`

## Assumptions & Decisions（已确认的关键决策）
- 交付范围：**论文 + 实验脚本**（用户选择）。
- success 指标：**双指标并报**（hard-success + judge-success）。
- 复杂编排重复：**每任务 R=3**。
- 非确定性控制：沿用新版 PDF 的 **cache-at-time**，并导出 cache/log 以便复现。

## Proposed Changes（改动方案：文件级别）

### A. 评测执行与结果 schema（R=3 + 双 success）
**文件：**
- `src/evaluation/complex_runner.py`

**做什么：**
1. 增加 CLI/配置参数：
   - `--repeat`（默认 3）
   - `--judge-success-threshold`（默认值需在论文中固定，例如 60 或 70）
   - `--react-recursion-limit`（覆盖 env `REACT_RECURSION_LIMIT`，用于敏感性实验）
2. 将 “每任务一次” 改为 “每任务 R 次 trial”：
   - 每个 trial 生成独立 judge log（task_id + trial_idx 可定位）
   - 结果落盘为 trial-level + task-level 聚合结构（保持旧字段兼容，schema version bump）
3. 在 run 结果中显式写入派生字段（防止后处理口径漂移）：
   - `derived.hard_success = run.success`
   - `derived.judge_success = (judge.score >= threshold) AND (fabrication_detected == False)`
4. 统一预算约束字段落盘：timeout、retry、cache enabled、recursion_limit 等，用于论文 parity audit 表。

**为什么：**
- 满足 NeurIPS 对统计稳健性与口径一致性的基本要求；
- 让 “success 与 score” 的关系可被解释与复验；
- 支撑后续 CI/显著性/敏感性实验。

### B. Judge 输出字段稳定化（支持 judge-success）
**文件：**
- `src/evaluation/judge.py`

**做什么：**
- 在解析成功/失败兜底中强制补齐字段：
  - `fabrication_detected`（缺省 False）
  - （如 rubric 里有）`unverified_numbers/unsupported_claims` 等字段缺省为空列表
- 在日志中记录 judge 配置（model、temperature、prompt hash、threshold）以便复验。

**为什么：**
- judge-success 依赖这些字段，缺失会导致统计口径漂移；
- 便于将 judge 可靠性写入论文并支撑 rebuttal。

### C. 汇总统计：按 task 聚合 + bootstrap CI（双指标）
**文件：**
- `src/scripts/summarize_neurips_runs.py`
- （可选）新增/扩展 `src/scripts/aggregate_results.py` 输出 paper-ready markdown 表

**做什么：**
1. 兼容两代 schema：
   - v1：每任务单次（保持旧逻辑）
   - v2：每任务 R 次 trial（新逻辑）
2. 新逻辑统计口径（避免把 trial 当独立样本夸大 N）：
   - 先对每个 task 聚合得到：`hard_success_rate_task`、`judge_success_rate_task`、`judge_score_mean_task`
   - 再对 tasks 做 bootstrap（N=任务数）得到 CI
3. 输出 paper-ready 汇总 JSON/markdown：
   - hard-success rate（mean + CI）
   - judge-success rate（mean + CI）
   - judge score（mean + CI）
   - cost 指标（latency/tool_calls/qveris_calls/token_usage）可选 CI

**为什么：**
- NeurIPS 审稿会关注方差与统计意义；
- 统一产物输出，减少“论文表格手填”带来的不一致风险。

### D. Baseline parity audit + recursion_limit 敏感性实验
**文件：**
- `src/evaluation/complex_runner.py`（支持把不同 recursion_limit 作为 variant 跑）
- `neurips_paper/main.tex`（正文/附录加入 parity 表与敏感性结果）

**做什么：**
1. Baseline parity audit（paper + logs）：
   - 明确并落盘：工具集合、tool IDs、cache、timeout/retry、judge 配置、输出 schema、token budget（如可）
   - 论文增加 parity 表（Full vs ReAct vs ablations）
2. recursion_limit 扫描：
   - 选择集合 `{10,15,25,50}`（以论文主表固定一个默认值，其余进附录敏感性表/图）
   - 每个 limit：N=20 tasks × R=3 trials，报告 hard/judge success + score CI

**为什么：**
- 防止审稿人认为 baseline 被“人为卡死”；
- 把“baseline 失败来源（loop/递归）”从叙述变成数据证据。

### E. 论文改写：双 success + R=3 + CI + 关键解释补强
**文件：**
- `neurips_paper/main.tex`

**做什么：**
1. Abstract / Evaluation Protocol 中把 “run once” 改为：
   - “每任务 R=3，报告任务层 bootstrap CI”
2. 明确 success 双指标定义与阈值：
   - hard-success：执行成功（无 timeout/exception）
   - judge-success：score≥threshold 且 fabrication_detected=False
3. 解释 w/o Memory 出现 success 更高但 score 更低：
   - 明确 success 与 score 的关系（例如 success 为硬约束通过；score 反映 completeness/quality）
4. 把 judge reliability 写成可防守口径：
   - temperature=0 + 人审抽检（数量与抽样策略）+ （可选）多 judge/多 seed
5. 在附录中加入：
   - baseline parity 表
   - recursion_limit 敏感性结果表/图

**为什么：**
- 论文叙述必须与代码产物完全一致，否则审稿会抓“口径漂移”；
- 明确 success/score 关系可化解“w/o Memory 反直觉”质疑。

### F. 可复现资产导出与发布计划（submission-ready）
**文件：**
- `benchmarks/*`（现有 benchmark + stats）
- 新增脚本（可选）：`src/scripts/export_neurips_artifacts.py`
- 论文附录/README（可选）：复现说明与 release plan

**做什么：**
1. 导出最小可复现包：
   - benchmark JSON + benchmark card（stats）
   - run.json + judge_logs.jsonl
   - cache dump（QVeris cache dir）或 tool response logs
2. 写 release plan（匿名/延期）：
   - 双盲期：说明“accept 后 release”
   - 若允许：提供匿名链接/哈希校验

**为什么：**
- QVeris/real-time API 的可得性会被审稿人质疑；提供 replay 资产能显著加分。

## Verification（验收与验证步骤）
1. **schema 校验**
   - v2 结果中每 task 的 `trials == R`，judge_logs 行数约等于 `N*R`
2. **双 success 可计算**
   - 所有 trial 都包含 `derived.hard_success` 与 `derived.judge_success`（且 judge 输出包含 `fabrication_detected`）
3. **统计输出正确**
   - `summarize_neurips_runs.py` 输出 hard/judge success + score 的 mean 与 CI（bootstrap 在 task 维度）
4. **parity audit 可复述**
   - run.json 记录工具集合、预算、cache、judge 配置；论文 parity 表可直接由 run.json 生成
5. **recursion_limit 敏感性**
   - 在至少 2 个 limit 点上复现 baseline 指标随 limit 变化趋势（与论文叙述一致）
6. **论文一致性**
   - main.tex 的 success/score/CI 表述与脚本输出字段逐一对应；不再出现“每任务一次”的旧口径。

---

## 附录：NeurIPS 主会 Review 记录（新版 main.pdf）
> 说明：以下为对 `neurips_paper/main.pdf`（新版，含 N=20、cache-at-time、judge=Qwen3.6-plus、消融表、FinBen N=82、InvestorBench、附录 tool IDs 与 rubric）按 NeurIPS 主会口径的文字版 review 记录，用于后续迭代与对外沟通（rebuttal/内部评审）。

### 1) Summary（工作概述）
论文提出 FinAgent-Evo：面向金融多工具工作流的鲁棒 agent 框架。核心由三部分组成：  
(1) Skill evolution：把技能视为 prompt genotype，用执行反馈驱动 meta-model 变异提示，并设置 replay buffer 防回归；  
(2) Hierarchical memory → procedural rules：将失败/成功轨迹写入 episodic memory，触发规则抽象并注入规划；  
(3) Verified DAG orchestration：plan 表达为带依赖的 JSON DAG，执行时做 schema 校验、重试、Python 数值交叉验证、citation binding。  
实验包括复杂编排 benchmark（N=20）、FinanceReasoning hard（93.7%）、InvestorBench（Sharpe 等）与 FinBen（N=82，28.05%）。

### 2) Strengths（优点）
1. 评测协议透明度显著提升：N=20、cache-at-time、QVeris MCP 工具、judge 模型与温度、消融表与 case study，使叙事更可防守。  
2. 消融结果能够支撑“组件贡献”：w/o evolution / w/o memory / w/o orchestration 均出现性能退化趋势。  
3. baseline 失败原因有解释（recursion-limit/loop），比仅报 0% 更可信。  
4. FinBen（N=82）揭示真实短板（NER/TAP），InvestorBench 增加外部维度评测，整体可信度提升。

### 3) Weaknesses / Risks（主要风险点）
1. 统计稳健性仍不足：复杂编排目前“每任务仅 1 次运行”的口径不满足主会常见期望（建议每任务 R≥3 并报告 CI）。  
2. baseline 公平性易被抓：recursion_limit 属预算约束但需要统一化（max tool calls / max time / max tokens）并做敏感性扫描。  
3. w/o Memory 出现“成功率更高但分数更低”的反直觉现象，需要在论文明确 success 的定义与 score 的关系。  
4. 复现性仍可能被质疑：QVeris/实时 API 即便 pinned tool IDs 也需要 cache dump / replay logs 与 release plan。  
5. 强 baseline 仍偏少：除 ReAct 外，建议增加 structured planning baseline（有 plan+execute，但无 evolution/memory），用于归因。
6. InvestorBench 缺少 baseline 对照且 Alpha vs B&H 为负，需要解释指标口径与意义，或补充对照策略。

### 4) Questions（审稿人会问的问题）
1. success 的严格定义是什么？是否与 score 阈值绑定？如何解释 w/o Memory success 更高？  
2. 是否能报告 R 次重复与 CI？agent 是否 deterministic？cache 是否对所有方法共享？  
3. baseline 的 recursion_limit 为何设为 X？在 X 扫描下 baseline 指标如何变化？  
4. evolution 是否在评测任务上在线更新？若是，如何保证对 baseline 公平？  
5. cache-at-time 的 cache 构建、warm 顺序、覆盖范围与可公开性？

### 5) Actionable Suggestions（可执行改进建议）
P0：
- 在复杂编排 benchmark 上每任务 R=3（用户已确认），报告 mean±std/或 task-level bootstrap CI；  
- success 双指标并报：hard-success（硬约束通过）+ judge-success（score≥阈值且无 fabrication）；  
- baseline parity audit 表 + recursion_limit 扫描 `{10,15,25,50}`；  
- 提供可复现资产：cache dump / tool response logs / benchmark card。  
P1：
- 增加 1 个强 baseline（structured planning baseline）；  
- 增加鲁棒性实验（timeout/rate limit/missing field 注入）；  
- 失败类型统计 + 3–5 个 case study。

### 6) Rating（内部参考）
相对上一版，整体更接近可投，但若缺少 R 次重复/CI 与 baseline 敏感性，仍存在被主会审稿抓住的高风险点。
