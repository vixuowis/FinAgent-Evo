# FinAgent-Evo: Autonomous Evolving Dynamic Skill Orchestration Framework

---

## English Introduction

### 🌟 Project Overview
**FinAgent-Evo** is an autonomous evolving Agent framework specialized for financial investment research. Built upon the [Deep Agents](https://github.com/langchain-ai/deepagents) research workflow, it incorporates Genetic Algorithms and Hierarchical Memory to address the challenges of non-stationary financial markets.

### 🚀 Key Innovations (vs. Standard Deep Agents)
1. **Skill Evolution Engine**:
   - Unlike static prompts, FinAgent-Evo defines skills as "genotypes".
   - Using **Mutation** and **Crossover** logic, the agent evolves its analysis logic based on performance feedback (e.g., Sharpe Ratio, Drawdown).
2. **Hierarchical Memory**:
   - **Working Memory**: Current session context.
   - **Episodic Memory**: Representative success/failure cases.
   - **Procedural Memory**: Abstracted "rules of thumb" for cross-task knowledge reuse.
3. **Dynamic Orchestration**:
   - Real-time adjustment of skill execution paths (DAG) based on task complexity.
4. **Self-Improvement Loop**:
   - Automatically triggers experience extraction after task completion to convert execution logs into long-term knowledge.

### 🏃 Running the System

#### 1. Web UI Mode (Recommended for Visualization)
- **Start Backend**:
  ```bash
  uv run langgraph dev
  ```
- **Start Frontend**:
  ```bash
  cd ui && npm run dev
  ```
- **Access**: `http://localhost:3000` (Configure `Deployment URL: http://127.0.0.1:2024` and `Assistant ID: finagent`)

#### 2. CLI Mode (For Quick Interaction)
```bash
uv run python -m src.run "Analyze investment opportunities in the semiconductor industry for 2024"
```

#### 3. IDE Integration (ACP Server)
Add this command to your editor settings (Zed, Trae, etc.):
```bash
uv run python -m src.server
```

---

## 中文介绍

### 🌟 项目概述
**FinAgent-Evo** 是一个专为金融投资研究设计的自主进化 Agent 框架。它基于 [Deep Agents](https://github.com/langchain-ai/deepagents) 的深度研究工作流，并引入了遗传算法和分层记忆系统，解决了金融市场“非平稳性”带来的挑战。

### 🚀 核心改进 (相比于传统 Deep Agents)
1. **技能进化引擎 (Skill Evolution Engine)**:
   - 不同于静态的 Prompt，FinAgent-Evo 将技能定义为“基因型”。
   - 通过**变异 (Mutation)**和**交叉 (Crossover)**逻辑，Agent 能够根据市场反馈（如夏普比率、回撤）自主演化出最适合当前场景的分析逻辑。
2. **分层记忆系统 (Hierarchical Memory)**:
   - **工作记忆**: 处理当前任务流。
   - **情节记忆**: 存储具有代表性的成功或失败案例。
   - **程序记忆**: 将零散经验抽象为“操作准则”，实现跨任务的经验复用。
3. **动态编排 (Dynamic Orchestration)**:
   - 实时调整技能执行路径（DAG），实现“按需调度”。
4. **自改进闭环**:
   - 任务结束后自动触发经验提取，将执行结果转化为长期知识。

### 🏃 运行系统

#### 1. 网页 UI 模式 (推荐用于流程可视化)
- **启动后端**:
  ```bash
  uv run langgraph dev
  ```
- **启动前端**:
  ```bash
  cd ui && npm run dev
  ```
- **访问**: `http://localhost:3000` (配置 `Deployment URL: http://127.0.0.1:2024` 且 `Assistant ID: finagent`)

#### 2. 命令行模式 (快速对话)
```bash
uv run python -m src.run "分析 2024 年半导体行业的投资机会"
```

#### 3. IDE 插件集成 (支持 Zed, Trae 等)
在编辑器设置中添加此启动命令:
```bash
uv run python -m src.server
```

---

## 🛠 Setup | 环境配置

1. **Install Dependencies | 安装依赖**:
   ```bash
   uv sync
   ```

2. **Configure Environment | 配置环境变量**:
   Create a `.env` file | 创建 `.env` 文件:
   ```env
   OPEN_ROUTER_API_KEY=your_key
   TAVILY_API_KEY=your_key
   DASHSCOPE_API_KEY=your_key  # Optional for GLM-5
   ```

## 📂 Project Structure | 项目结构

- `src/core/`: Evolution engine, memory system, and prompt templates.
- `src/agent.py`: Core Agent definition and tool registration.
- `src/server.py`: ACP Protocol implementation.
- `docs/`: Original research proposal and documentation.
- `ui/`: Official Deep Agents UI for visualization.

## 📜 Proposal Reference
Based on the research proposal: [docs/proposal.md](docs/proposal.md).
