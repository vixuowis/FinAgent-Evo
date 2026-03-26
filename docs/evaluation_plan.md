# FinAgent-Evo Benchmark 评估计划

## 1. 评估目标 (Objectives)
旨在从**决策准确性**、**投资盈利性**、**推理可靠性**及**进化有效性**四个维度全面衡量 FinAgent-Evo 框架的性能，并验证其相对于静态 Agent 配置的优势。

## 2. 基准测试选择 (Benchmark Selection)

| 维度 | 基准测试 | 来源 | 重点评估内容 |
| :--- | :--- | :--- | :--- |
| **综合决策** | **InvestorBench** | ACL 2025 | 股票、加密货币、ETF 的端到端投研决策 |
| **数值推理** | **FinanceReasoning** | ACL 2025 | 财报分析、数值计算与多步逻辑推理 |
| **多智能体** | **FinCon** | NeurIPS 2024 | 多个 Agent 角色（分析师、交易员）的协作效果 |
| **实战回测** | **NASDAQ-100 / Binance** | 自定义 | 真实历史数据下的 Sharpe Ratio, MDD 等金融指标 |

## 3. 核心评估指标 (Metrics)

### 3.1 金融性能指标 (Financial Performance)
- **累计收益率 (Cumulative Return)**: 衡量策略的盈利能力。
- **夏普比率 (Sharpe Ratio)**: 风险调整后的收益水平。
- **最大回撤 (Max Drawdown)**: 策略的抗风险能力与稳定性。

### 3.2 模型推理指标 (Reasoning Performance)
- **准确率 (Accuracy)**: 针对 FinanceReasoning 中客观题目的答题准确率。
- **幻觉率 (Hallucination Rate)**: 检测模型在数值计算与事实引用中的虚假信息比例。
- **任务成功率 (Task Success Rate)**: 完成复杂投研工作流（获取数据 -> 分析 -> 建议）的成功比例。

### 3.3 进化效能指标 (Evolutionary Efficiency)
- **适应度增益 (Fitness Gain)**: 进化 50 代后平均 Fitness Score 的提升百分比。
- **技能发现率 (Skill Discovery Rate)**: 进化过程中产生的、表现优于初始技能库的新技能数量。

## 4. 实验协议 (Experimental Protocol)

### 4.1 对照组 (Baselines)
- **Baseline 1: Buy & Hold**: 市场基准策略。
- **Baseline 2: Zero-Shot Agent**: 仅使用 Prompt 但无记忆、无进化的 Agent。
- **Baseline 3: TradingAgents (Li et al., 2024)**: 目前最先进的多 Agent 静态配置方案。

### 4.2 实验环境设置
- **模型**: GPT-4o, Claude 3.5 Sonnet, Llama 3 (70B)。
- **周期**: 2023-01 至 2024-12（覆盖牛熊市切换）。
- **参数**: 种群规模 50，进化代数 30，变异率 0.1。

## 5. 消融实验 (Ablation Studies)
1. **W/O Evolution**: 禁用进化引擎，仅保留静态技能库，验证进化算法对性能的增益。
2. **W/O Hierarchical Memory**: 禁用分层记忆系统，验证长期记忆对连续决策的影响。
3. **W/O Dynamic Orchestration**: 使用固定顺序执行技能，验证动态编排的灵活性。

## 6. 实施时间表 (Timeline)
- **Week 1**: 数据集接入与环境配置。
- **Week 2**: 运行 Baseline 实验，建立性能基准。
- **Week 3**: 运行 FinAgent-Evo 进化实验（多轮迭代）。
- **Week 4**: 消融实验与数据分析，生成最终评估报告。
