# NeurIPS 主会论文改进 Spec（FinAgent-Evo）

## Why
当前稿件在 NeurIPS 主会审稿标准下的主要风险点集中在：**可复现性不足、评测协议不透明、baseline 公平性存疑、核心模块缺少消融支撑、结论表述与证据不匹配、引用时间线不自洽**。  
本 spec 旨在把“审稿改进清单”落成可执行的研发计划与验收标准，并与现有评测基础设施 spec 对齐。

> 依赖：已有评测基础设施补强见 `.trae/specs/strengthen-neurips-evaluation/`（消融入口、judge 日志、失败模式、成本统计、baseline 对齐等）。

## Goals（目标）
1. **把论文补齐到主会可接受的信息密度**：方法可复现、实验可复验、结论可防守。
2. **用系统性实验回答审稿人核心质疑**：公平对比、消融证明、稳健性证明、统计意义。
3. **形成可提交资产**：benchmark card、judge rubric/prompt、轨迹与日志（匿名可发布/或录入 release plan）。

## Non-Goals（非目标）
- 不在本 spec 内解决生产部署级合规/风控（可在 Limitations 与 Future Work 讨论）。
- 不要求一次性做所有可能的强 baseline；以“可防守 + 可复现”为先。

## Scope（范围）
### Paper-side（论文内容补齐）
- Problem setting / assumptions / definitions（工具、技能、接口、验证策略）
- Method 细节（伪代码、超参表、接口 schema 示例）
- Benchmark description（taxonomy、N、示例、工具清单、非确定性控制）
- Evaluation protocol（LLM-as-judge 透明化、统计报告、可靠性）
- Baseline parity audit（tool/budget/prompt/重试策略对齐）
- Ablations（w/o evolution、w/o procedural memory、可选 w/o verification）
- Robustness（工具失败注入、跨时间/缓存重放）
- 引用时间线修复（去除未来年份/占位引用）

### Engineering-side（实验与资产）
- 复用现有 `strengthen-neurips-evaluation` 产物：统一结果 schema、judge logs、失败模式/成本统计、对比汇总。
- 新增：paper-ready 的 benchmark card / rubric prompt / calibration 样例输出。

## Prioritized Backlog（按优先级）
### P0（必须做，否则主会基本没法过）
1. **Complex benchmark 规范化**：task taxonomy + 任务数 N + 2–3 个完整示例 + tool schema/版本 + 非确定性控制协议（cache-at-time 或 log-and-replay，择一）。
2. **LLM-as-judge 透明化**：judge 模型/版本 + rubric prompt + R 次重复 + mean±std/CI + judge 可靠性（多 seed/ensemble/人审抽检至少一种）。
3. **Baseline 公平性审计**：ReAct（tool parity + budget parity）+ 明确重试/超时/错误处理；把“0% success”改成可防守表述并给出审计依据。
4. **消融结果落地**：w/o evolution、w/o procedural memory（必要）；可选 w/o verification。
5. **引用时间线修复**：移除 2025/2026 等未来年份引用或替换为可公开引用且时间线自洽的工作。

### P1（强烈建议：显著提升说服力）
1. **强 baseline**：structured planning baseline（无 evolution/memory）或 controller-style baseline；至少 1 个可复现强 baseline。
2. **稳健性实验**：rate limit/timeout/missing field 注入；缓存重放/跨时间点评测。
3. **错误类型分析**：按失败模式分类统计 + 典型 case study（3–5 个）。

### P2（加分项）
1. **释放资产（匿名/延期）**：任务集、tool schema、judge prompt、部分轨迹 logs。
2. **更完整统计**：bootstrap CI、显著性检验、judge 与人评相关性曲线等。

## Milestones（建议里程碑，按 4–6 周节奏）
- M1（Week 1）：P0-1/P0-5：benchmark card 初稿 + 引用修复；产出可复现的任务统计与示例。
- M2（Week 2）：P0-2：judge 协议固定 + 可靠性方案确定；补充 rubric 附录与校准样例。
- M3（Week 3）：P0-3/P0-4：baseline parity audit + 消融跑完 + 表格可直接用于论文。
- M4（Week 4–6）：P1：强 baseline + robustness + 失败分析；完成主会级写作打磨与补充实验。

## Definition of Done（整体验收）
- 论文 “Experimental Setup / Evaluation Protocol” 在不看代码的情况下可复验（N、R、judge、工具、缓存/重放协议齐全）。
- Full vs baseline vs ablations 结果在同一任务集上可复现，并报告均值与方差/置信信息。
- 论文不包含时间线不自洽引用；摘要/结论的 claims 都能在实验与附录中被定位与支撑。

