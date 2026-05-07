# Tasks（NeurIPS 主会论文改进）

> 状态说明：这里的任务是“接下来要做”的 paper+研发计划；评测基础设施相关的已完成项见 `.trae/specs/strengthen-neurips-evaluation/tasks.md`。

## P0（必须做）
- [x] Task P0-1：Complex benchmark 规范化（paper-ready）
  - [x] 明确非确定性控制协议：cache-at-time 或 log-and-replay（择一并写入论文）
  - [x] 写 task taxonomy（类别/典型 tool chain/失败模式/judge 关注点）
  - [x] 给出任务数 N、每类占比、难度分级（如有）
  - [x] 附录加入 2–3 个完整任务实例（instruction + required fields + allowed tools + constraints）
  - [x] 附录加入 tool schema/版本说明（字段、单位、错误码/缺失值策略）

- [ ] Task P0-2：LLM-as-judge 协议固化与可靠性
  - [x] 明确 judge 模型/版本、温度、seed（如可）、rubric prompt
  - [ ] 每任务重复 R 次（或 judge 多次评分）并报告 mean±std / CI
  - [x] 选择一种可靠性方案并落地：多 seed / judge ensemble / 人审抽检
  - [ ] 附录放 judge prompt + 2–3 个 calibration 示例（输入/输出/评分解释）

- [ ] Task P0-3：Baseline parity audit（可防守）
  - [ ] 明确 ReAct baseline 的工具集合与 FinAgent-Evo 一致（或解释差异并补强 baseline）
  - [ ] 对齐 token budget、重试/超时、错误处理与输出 schema
  - [ ] 写一段 baseline audit（论文正文或附录），解释为何对比公平
  - [ ] 将“0% success”改写为更可防守表述，并提供失败类型统计支撑

- [ ] Task P0-4：消融实验（核心贡献证明）
  - [ ] w/o evolution（结果表 + 失败分析）
  - [ ] w/o procedural memory（结果表 + 失败分析）
  - [ ] 可选：w/o verification（不强制 python 计算）以证明“verified computation”价值

- [ ] Task P0-5：引用时间线修复
  - [x] 移除/替换未来年份（2025/2026）引用
  - [ ] Related Work 覆盖必引工作并时间线自洽

## P1（强烈建议）
- [ ] Task P1-1：强 baseline（至少 1 个）
  - [ ] structured planning baseline（JSON plan + 执行，但无 evolution/memory）
  - [ ] 或 controller-style baseline（类似 HuggingGPT 的 planner/router）

- [ ] Task P1-2：稳健性实验
  - [ ] 工具失败注入：timeout / rate limit / missing field
  - [ ] 跨时间/缓存重放对比（证明非确定性控制有效）

- [ ] Task P1-3：错误类型分析（paper-ready）
  - [ ] 失败模式分类统计（format/tool selection/tool order/numeric unverified/grounding）
  - [ ] 典型 case study 3–5 个（含轨迹片段与修复点）

## P2（加分项）
- [ ] Task P2-1：资产释放计划（匿名/延期）
  - [ ] release plan：任务集、tool schema、judge prompt、logs
  - [ ] 说明脱敏策略与可复现范围

- [ ] Task P2-2：更完整统计与显著性
  - [ ] bootstrap CI / 显著性检验
  - [ ] judge vs 人评相关性曲线与偏差分解
