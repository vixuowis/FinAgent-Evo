# NeurIPS Review（基于 main.pdf）

文档：`neurips_paper/main.pdf`（包含：N=20 complex orchestration、cache-at-time、QVeris MCP 工具、LLM-as-judge=Qwen3.6-plus (T=0)、消融表与 case study、FinBen N=82、InvestorBench 表、附录含 tool IDs 与 rubric）。

## Summary
论文提出 **FinAgent-Evo**：面向金融多工具工作流的鲁棒 agent 框架，将技能视为可演化的 prompt genotype（用反馈驱动变异），将经验抽象为 procedural rules 注入规划，并用可验证的 DAG 计划执行（schema 校验、重试、Python 数值核验、引用绑定）来降低长链任务中的错误传播与数值幻觉；在 N=20 真实 API 复杂编排任务上显著优于 ReAct baseline，并在 FinanceReasoning、FinBen、InvestorBench 上给出补充结果与分析。

## Strengths
1) **系统贡献闭环清晰**：evolution（技能自改进）+ memory（规则沉淀）+ verified orchestration（结构化可验证执行）三者逻辑自洽，金融场景动机充分。  
2) **评测透明度提升到主会可讲清**：N=20、难度/类型分布、缓存策略、工具 ID、judge 配置与 rubric 都有交代。  
3) **消融 + 案例分析对主张有支撑**：w/o evolution / w/o memory / w/o orchestration 的退化趋势能支持“各模块贡献”。  
4) **不仅报好看的点**：FinBen 给出真实短板（NER/TAP），这会比只报高分更可信。  

## Weaknesses / Concerns
1) **统计稳健性仍偏弱**：复杂编排仍是“每任务跑一次”的口径（即使 judge T=0），N=20 对主会来说不大，缺少 R 次重复与 CI/方差会被质疑结论稳定性。  
2) **baseline 预算与 recursion-limit 可能引发争议**：你解释了 baseline 的 loop/recursion-limit 失败，但审稿人可能认为这是“预算/限制设计导致的失败”，需要统一预算约束并给敏感性扫描结果。  
3) **success 与 score 的关系需要更明确**：表中出现类似 “w/o Memory success 更高但 score 更低” 的现象，必须定义 success 的硬标准，并解释它和打分的对应关系，否则容易被认为指标设计有问题。  
4) **强 baseline 仍不足**：目前主要对比 ReAct 与消融，缺少一个“同样结构化计划执行但无 evolution/memory”的 **Plan-only baseline** 来做归因，否则审稿人会说收益主要来自 orchestration。  
5) **InvestorBench 部分缺 baseline 对照**：指标很亮眼，但缺少 B&H/规则策略/官方 baseline，会被认为不够完整，且 Alpha vs B&H 为负需要解释。  

## Questions for Authors
1) 复杂编排的 **success** 定义是什么？和 judge score 阈值是否绑定？如何解释 w/o Memory 的现象？  
2) 是否能提供每任务 **R≥3** 的重复与 task-level bootstrap CI？工具缓存是否对所有方法共享同一份？  
3) ReAct baseline 的 recursion-limit/预算如何与 Full 对齐？如果提升 recursion-limit，性能变化如何？  
4) evolution/memory 是否在评测时在线更新？若是，是否会引入对 baseline 的不公平？  

## Suggestions (Actionable)
- **P0**：复杂编排改成每任务 R=3 并报 task-level bootstrap CI；明确并同时报告 hard-success 与 judge-success（阈值+fabrication）。  
- **P0**：加 **Plan-only baseline**（保留 plan+DAG+verification，去掉 evolution/memory/skill library）以完成归因。  
- **P0**：做 baseline 预算统一与 recursion-limit 敏感性（10/15/25/50），把“baseline 失败原因”变成数据证据。  
- **P1**：InvestorBench 补 B&H/规则策略 baseline，并解释 alpha 与 Sharpe 的口径差异。  
- **P1**：补失败模式统计（format/tool order/unverified numbers/timeout 等）与对应案例修复点。  

## Overall Rating (NeurIPS-style) & Confidence
- **Rating：6 / 10（Weak Accept 边缘）**：系统与实验叙事已成型，且比“概念稿”更接近主会标准；但统计与强 baseline/预算公平性仍是决定性风险。  
- **Confidence：4 / 5**：问题主要来自评测设计与统计报告，可从文稿直接判断。  

