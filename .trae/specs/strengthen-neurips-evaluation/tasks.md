# Tasks
- [x] Task 1: 明确实验矩阵与输出 schema
  - [x] 定义 Full / W-O Evolution / W-O Memory / W-O Orchestration 的运行入口与配置方式（env/config 参数）
  - [x] 统一结果 JSON schema（task-level + run-level summary + judge logs pointers）

- [x] Task 2: 实现消融开关（可运行变体）
  - [x] W/O Evolution：禁用 `evolve_skill` 触发与 skill_library 写入新变异技能
  - [x] W/O Hierarchical Memory：禁用 memory.write 抽象、planner 不注入 procedural rules
  - [x] W/O Dynamic Orchestration：跳过 `multi_skill_orchestrator` 的 planning+execution，改为固定流程 baseline（需定义固定流程）

- [x] Task 3: 增强 complex orchestration 评测日志与 judge 透明度
  - [x] 固化 judge 配置与 prompt 模板（版本化/可 hash）
  - [x] 记录每条任务的 judge 输入与原始输出，并做结构化解析失败兜底
  - [x] 输出 failure mode 字段（planning/execution/calculation/synthesis/judge）

- [x] Task 4: 增加基准统计导出（benchmark card 数据）
  - [x] 对 `benchmarks/complex_tasks.json` 与 `benchmarks/complex_tasks_real_api.json` 输出统计摘要
  - [x] 统计：任务数、required_skills 分布、链路长度（基于 plan/trajectory 的 proxy）

- [x] Task 5: 规范化并重跑 baseline（公平对比）
  - [x] 明确 baseline 工具集合与递归限制/重试策略
  - [x] 结果字段与 FinAgent-Evo 对齐，便于 compare 脚本聚合

- [x] Task 6: Judge 校准（人评一致性）
  - [x] 设计人评标注文件格式（task_id → score/notes）
  - [x] 输出与 judge 分数的相关性与偏差分析（例如 Spearman + 误差分桶）

- [x] Task 7: 成本与稳定性度量
  - [x] 记录任务耗时、工具调用次数、API 时间戳/缓存命中（如实现缓存）
  - [x] 输出 run-level summary（成功率、均值、P50/P90、Top-K 失败模式）

- [x] Task 8: 实验跑分与产物落盘（用于论文）
  - [x] 跑 Full 与 3 个消融在同一任务集上（优先 complex tasks）
  - [x] 生成对比表（Full vs ablations vs baseline）与显著性/置信区间（如可行）

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 5 depends on Task 1
- Task 8 depends on Task 2, Task 3, Task 4, Task 5, Task 7
