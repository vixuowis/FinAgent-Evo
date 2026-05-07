# 需要补的实验 TODO（升级到 300 题主表，需全量重跑）

## Summary
你已将主表任务集从 100 题升级到 **300 题**，因此所有“主表相关”的结果（含 baseline、SOP、消融、CI、错误统计、鲁棒性、FinAgent/FinMem 适配）都需要按 **同一套 300 题**重新跑一遍，确保口径一致、统计可比、论文可防守。

## Current State Change（变更点）
- 主表任务集：**N=300**（新任务集）。
- 影响：此前基于 N=100 的所有主表结论只能作为开发阶段参考，**论文表格/图必须以 N=300 重新生成**。
- 你当前已具备：方法实现、SOP baseline、消融开关、judge & tools 配置（以现有工程为准）。

## Assumptions & Decisions（固定决策）
- 主表：N=300 complex financial analysis tasks（同任务空间对比）。
- Baselines：ReAct(parity) + MetaGPT-style SOP（已存在）；消融继续保留（w/o Evolution / w/o Memory / w/o Orchestration）。
- 统计：核心对比项采用 **每任务 R=3**，并报告 **task-level bootstrap 95% CI**（不把 trial 当独立样本）。
- 适配对比：FinAgent(DVampire) / FinMem 继续纳入（允许 coverage + case 形式；strict-adapt 优先）。

---

## P0：必须重跑的“主会主结论链路”（N=300）

### P0-1 运行健康度与配置冻结（先做）
**目标**：确保 300 题全量可评分、可复现，避免跑到一半发现格式/超时问题导致返工。

**TODO**
- [x] 修复 Tavily API 限额问题：在 `src/agent.py` 中增加了对 QVeris Brave Search 的自动降级逻辑。
- [x] 修复 Python 解释器语法注入问题：在 Orchestrator 中增加了对 `<output_step_N>` 占位符的自动递归替换逻辑。
- [ ] 冻结并记录统一配置：模型版本、temperature、max tokens、timeout、retries、max tool calls/steps、cache 设置、judge 设置（model+prompt hash+阈值）。
- 跑一次 **smoke run**：随机抽 30 题，Full/ReAct/SOP 各跑 1 次，验证：
  - 解析/打分无崩溃
  - tool logs 完整
  - judge 输出字段齐全（含 fabrication/unsupported/unverified 等）

**验收**
- 30 题 smoke run 可评分率 ≥ 95%，且失败原因可归类（不是“系统性崩溃”）。

---

### P0-2 主表全量：Full + ReAct + SOP + 消融（N=300, R=3, CI）
**TODO**
- 对以下方法在 300 题上跑 **R=3**（不同 seed/不同 run id）：
  - FinAgent-Evo (Full)
  - ReAct (tool-parity)
  - SOP baseline
  - w/o Evolution
  - w/o Memory
  - w/o Orchestration
- 汇总口径：
  - 先按 task 聚合 3 次 trial 得到 task-level mean
  - 再对 300 tasks 做 bootstrap（建议 10,000 次）得到 95% CI

**产出（论文主表必需）**
- Table 1：Main results（Hard-success / Judge-success / Judge score / cost，含 CI）
- Figure：带 CI 的柱状图（Full vs ReAct vs SOP vs ablations）
- Figure：成本-效果散点图（x=cost，y=score 或 success）

**验收**
- 主结论在 task-level paired difference 上显著（bootstrap CI 不跨 0 或配对检验通过）。

---

### P0-3 预算公平性 + 敏感性（N=300 子集即可）
**TODO**
- 统一预算约束并写入日志（至少记录 max tool calls/timeout/retries/recursion limit）。
- 做敏感性扫描（建议先用 60 题分层抽样子集）：
  - ReAct：budget 3 档（low/mid/high）
  - SOP：budget 2 档（mid/high，控制成本）
  - Full：可选 1–2 档（证明“不是靠更大预算赢”）

**产出**
- Table：Budget parity & sensitivity（含指标与成本）
- Figure：性能-预算曲线（带 CI 或至少误差条）

**验收**
- 明确“推荐预算区间”，并能回答审稿人“baseline 是否被卡死/是否预算不公平”。

---

## P1：强烈建议重跑/补齐（N=300）

### P1-1 错误类型统计（Error taxonomy）——在 N=300 上做
**TODO**
- 定义并落地错误分类（format/schema、tool order、missing prerequisite、unverified numbers、unsupported claims、tool failure not recovered、loop）。
- 全量统计 Full/ReAct/SOP/关键消融（至少这几条）。

**产出**
- Table：Error taxonomy distribution（系统×错误类型占比）
- Figure：热力图/堆叠条形图
- Appendix：每类 3–5 个案例

**验收**
- “Other” ≤ 20%；且能指出 Top-3 错误与对应修复方向。

---

### P1-2 鲁棒性（Failure injection / stress tests）——用 N=300 的分层子集
**TODO**
- 从 300 题中分层抽 30–60 题（覆盖类型/难度）。
- 注入扰动（至少两类）：工具超时/空返回；关键字段缺失/冲突信息。
- 对比 Full vs ReAct vs SOP（R=1 或关键点 R=3）。

**产出**
- Table：Robustness matrix（扰动类型×指标退化）
- Figure：paired difference 分布图

---

## P2：外部基准（不依赖 300 题，但建议重跑对齐版本）

### P2-1 FinanceReasoning（hard split）
**TODO**
- Full vs ReAct(parity) vs SOP（若 SOP 适用）
- 报告 accuracy（可选 CI）

### P2-2 FinBen（overall + breakdown）
**TODO**
- 全量跑通并输出 overall + 关键子任务（NER/TAP 等）
- 结合错误类型给出短板解释

---

## P3：FinAgent / FinMem 适配对比（N=300，允许 coverage 形式）

### P3-1 FinAgent(DVampire) strict-adapt → best-effort（如需）
**TODO**
- 优先 strict-adapt：同工具/同 cache/同预算/同输出 schema。
- 若跑不通，降级 best-effort，并强制报告：
  - coverage（可完成任务比例）
  - parity 差异（工具/预算/输出）
  - 失败类型统计 + case

### P3-2 FinMem strict-adapt → best-effort（如需）
同上。

**产出**
- Table：Framework adaptation comparison（含 coverage）
- Table：Parity audit（明确不一致点）
- Appendix：适配失败原因与案例

---

## Verification（最终验收）
1) 300 题主表（Full/ReAct/SOP/消融）全部具备 R=3 + task-level CI 的可复现结果。  
2) 预算敏感性曲线能解释 baseline 被卡死/预算公平性问题。  
3) Error taxonomy 与 robustness 能回答“错在哪、抗不抗扰动”。  
4) FinAgent/FinMem 适配即便效果一般，也能以 coverage+case 的方式“可防守”呈现。  

