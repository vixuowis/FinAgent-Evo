# 需要补的实验 TODO Plan（100-task 主表）

## Summary
在已具备 **SOP baseline + 消融** 的基础上，补齐 NeurIPS 主会最关键的“可防守实验链路”：**R=3 重复 + task-level CI**、**预算敏感性**、**错误类型统计**、**鲁棒性注入**、以及 **FinanceReasoning/FinBen 外部基准**；并按你的要求新增 **FinAgent(DVampire)/FinMem 适配对比**（同 100-task 主表任务空间）。

## Current State Analysis
- 论文 `neurips_paper/main.pdf` 已包含：N=100 主表、ReAct baseline、SOP baseline、消融、FinanceReasoning/FinBen 段落与部分结果描述。
- 目前缺口（用户确认“都未完成”）：
  1) 100-task 主表尚未做 **每任务 R=3** 与 **task-level bootstrap CI**；
  2) 未给出 **预算统一/敏感性曲线**（max tool calls/timeout/retries/recursion limit 等）；
  3) 未形成可复用的 **Error taxonomy 统计表/图**；
  4) 未做 **鲁棒性（故障注入/扰动）**；
  5) **FinanceReasoning/FinBen** 需要跑通全量、并与主表口径对齐；
  6) 需把 **FinAgent(DVampire)/FinMem** 适配到“金融复杂分析任务”并对比（允许 coverage + case 的呈现方式）。

## Assumptions & Decisions
- 主表任务集：你们自建 **100 个 complex financial analysis tasks**（同一任务空间对比）。
- Baselines：保留 **ReAct(parity)** 与 **MetaGPT-style SOP**（已存在），不再新增 plan-only。
- 统计：核心对比项（Full/ReAct/SOP/关键 ablations/FinAgent-adapt/FinMem-adapt）采用 **每任务 R=3**；CI 使用 **task-level bootstrap**（不把 trial 当独立样本）。
- 适配对比：FinAgent/FinMem 默认按 **strict-adapt**（同工具/同预算/同 cache/同输出 schema）；若 strict 跑不通，可降级为 **best-effort-adapt**，但必须在 parity 表中标注差异，并报告 coverage。

## Proposed Changes（实验 TODO 列表 + 产出）

### P0-1：R=3 重复 + task-level CI（主表升级为可发表）
**要做什么**
1. 对以下方法在 100 tasks 上跑 **R=3**：
   - FinAgent-Evo (Full)
   - ReAct (tool-parity)
   - SOP baseline
   - 关键消融（w/o Evolution, w/o Memory, w/o Orchestration）
2. 汇总时：
   - 先按 task 聚合 trial 得到每 task 的均值（hard-success、judge-success、judge score、成本等）
   - 再对 tasks 做 bootstrap（建议 10,000 次）输出 95% CI

**产出**
- Table：`Main Results (N=100, R=3, CI)`（替换现有主表或在主表上补 CI 列）
- Figure：带 95% CI 的柱状图（Full vs ReAct vs SOP vs ablations）
- Figure：成本-效果散点图（x=cost，y=score/success）

**涉及文件（实现入口）**
- `src/evaluation/complex_runner.py`（确保支持 repeat=3、并输出 task-level summary）
- `src/scripts/summarize_neurips_runs.py`（task-level bootstrap CI）
- `neurips_paper/main.tex`（将“run once per task”改为 R=3+CI，并引用产出表/图）

### P0-2：预算公平性与敏感性（Budget/Recursion Sensitivity）
**要做什么**
1. 统一预算约束（至少记录并对齐）：max tool calls、timeout、retries、recursion/tool-call limit
2. 做敏感性扫描（最小集合）：
   - 对 ReAct 与 SOP（至少 ReAct）扫描 `{low, mid, high}` 三档预算（例如 max tool calls/recursion limit）
   - 可选：对 Full 也扫 1–2 档以展示曲线形态

**产出**
- Table：`Budget Parity & Sensitivity`（含各方法预算设置、以及敏感性点的指标）
- Figure：性能-预算曲线（y=score/hard-success，x=预算）

**涉及文件**
- `src/evaluation/complex_runner.py`（记录预算参数到 run.json；支持批量 variants）
- `neurips_paper/main.tex`（加入 parity 表与敏感性结果）

### P1-1：错误类型统计（Error Taxonomy）
**要做什么**
1. 定义错误分类（建议至少覆盖）：format/schema、tool order、missing prerequisite、unverified numbers、unsupported claims、tool failure not recovered、loop/recursion
2. 生成自动统计：
   - schema 校验失败率
   - judge 输出中的 unsupported/unverified 字段计数（若你们 rubric 已输出）
   - failure_mode（timeout/tool error/loop）计数
3. 为“Other”或无法自动判定的错误抽样人工复核（例如每方法 30 条失败样本）

**产出**
- Table：`Error Taxonomy Distribution`（Full vs ReAct vs SOP vs FinAgent/FinMem-adapt）
- Figure：热力图/堆叠柱状图
- Appendix：每类 3–5 个典型案例（含 tool logs 片段）

**涉及文件**
- `src/scripts/summarize_neurips_runs.py` 或新增 `src/scripts/error_taxonomy.py`
- `neurips_paper/main.tex`（新增错误分析小节/附录）

### P1-2：鲁棒性（Failure Injection / Stress Tests）
**要做什么**
1. 从 100 tasks 中按类型分层抽样一个子集（例如 20 tasks）
2. 注入扰动（至少两类）：
   - 工具层：timeout/rate limit/empty response（模拟）
   - 数据层：关键字段缺失/冲突数字（输入扰动）
3. 对比 Full vs ReAct vs SOP（至少这三条）在扰动前后的 Δscore/Δsuccess 与额外成本

**产出**
- Table：`Robustness Matrix`（扰动类型 × 指标退化）
- Figure：paired difference（扰动前后差值分布）

**涉及文件**
- benchmark 侧：为 20 tasks 生成扰动版本（或 runner 注入开关）
- `neurips_paper/main.tex`（鲁棒性小节/附录）

### P0-3：外部基准全量跑通（FinanceReasoning / FinBen）
**要做什么**
1. FinanceReasoning（hard split）：
   - Full vs ReAct(parity) vs SOP（如 SOP 可用）
   - 输出 accuracy（若可，补 CI 或至少 N）
2. FinBen：
   - 输出 overall + 分任务（重点：NER/TAP 等你们弱项）
   - 同时输出错误类型（为什么弱：抽取边界/格式/实体归一）

**产出**
- Table：`FinanceReasoning Results`
- Table：`FinBen Overall + Breakdown`
- Appendix：失败样例（各 3–5 个）

**涉及文件**
- 你们现有对应 runner/脚本（待确认路径）；最终写回 `neurips_paper/main.tex`

### P2-1：FinAgent(DVampire) / FinMem 适配对比（同 100-task 任务空间）
**要做什么**
1. **Strict-adapt**：同工具/同 cache/同预算/同输出 schema，把 FinAgent 与 FinMem 接入 100-task runner
2. 若 strict 跑不通，降级为 **best-effort-adapt**（但：
   - 必须在 parity 表中标注差异；
   - 必须报告 coverage：可完成任务比例；
   - 必须提供失败类型统计与 case）

**产出**
- Table：`Framework Adaptation Comparison`（Full vs ReAct vs SOP vs FinAgent-adapt vs FinMem-adapt；含 coverage）
- Table：`Parity Audit`（明确哪些条件不一致）
- Appendix：适配失败的典型原因（任务不匹配、输出格式、工具依赖等）

**涉及文件**
- 新增 adapter 层（建议单独目录 `src/baselines/adapters/*`）
- `src/evaluation/complex_runner.py` 增加 variants：`finagent_adapted`, `finmem_adapted`
- `neurips_paper/main.tex`：将适配结果放在主表或附录（建议附录/补充表，避免喧宾夺主）

## Verification Steps（验收/校验）
1. **R=3 生效**：每个 task 有 3 个 trial；汇总时按 task 聚合后再 bootstrap。
2. **CI 合理**：CI 通过重复运行脚本（同 seed）可复现；不把 trial 当独立样本。
3. **预算公平**：run.json 中记录并能生成 parity 表；敏感性扫描曲线可重现。
4. **错误分类覆盖**：≥80% 的失败能落到非 Other 类；每类至少有代表性样例可展示。
5. **鲁棒性实验可复验**：扰动版本任务/开关可重复生成；对比结果稳定。
6. **FinAgent/FinMem 适配可解释**：无论成败，均有 coverage、parity 标注、失败原因与案例。

