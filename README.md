# FinAgent-Evo: Autonomous Evolving Dynamic Skill Orchestration Framework

---

## 🚀 Latest Updates (2026-04-10)

### **Intelligent Evolution & Memory Upgrade**
- **LLM-Driven Evolution**: Transitioned from static crossover logic to **LLM-as-a-Meta-Model** mutation. The agent now intelligently rewrites its own "Genotype" (prompts) based on performance feedback.
- **Hierarchical Memory Abstraction**: Implemented a **Knowledge Abstraction Engine** that automatically distills episodic experiences into persistent **Procedural Rules**.
- **ACP Server Enhancement**: Full support for **Agent Client Protocol**, enabling seamless integration with AI-native IDEs like **Trae** and **Zed**.
- **Interactive Verification**: Added specialized test suites (`src/test_evolution_flow.py`, `src/test_memory_flow.py`) to demonstrate the live evolution and abstraction chains.

### **智能进化与记忆升级 (中文)**
- **LLM 驱动的进化**: 从静态的交叉逻辑转型为以 **LLM 作为元模型 (Meta-Model)** 的变异机制。Agent 现在能够根据任务反馈智能重写自身的“基因型”（Prompt）。
- **分层记忆抽象**: 实现了**知识抽象引擎**，自动将零散的情节经验（Episodic Memory）提炼为持久的**程序性规则 (Procedural Rules)**。
- **ACP 服务增强**: 全面支持 **Agent Client Protocol**，实现与 **Trae**、**Zed** 等 AI 原生 IDE 的无缝集成。
- **交互式验证**: 新增专项测试套件（`src/test_evolution_flow.py`, `src/test_memory_flow.py`），直观展示实时进化与抽象链路。

---

## English Introduction

### 🌟 Project Overview
**FinAgent-Evo** is an autonomous evolving Agent framework specialized for financial investment research. Built upon the [Deep Agents](https://github.com/langchain-ai/deepagents) research workflow, it incorporates Genetic Algorithms and Hierarchical Memory to address the challenges of non-stationary financial markets.

### 🚀 Key Innovations (vs. Standard Deep Agents)
1. **Intelligent Skill Evolution Engine**:
   - Unlike static prompts, FinAgent-Evo defines skills as **"Genotypes"**.
   - Using **LLM as a Meta-Model**, the agent intelligently rewrites (Mutates) its analysis logic based on performance feedback.
   - Includes `evolve_skill` and `invoke_skill` tools for dynamic logic adaptation.
2. **Hierarchical Memory Abstraction**:
   - **Working Memory**: Current session context.
   - **Episodic Memory**: Representative success/failure cases.
   - **Procedural Memory**: **Knowledge Abstraction Engine** automatically extracts "Rules of Thumb" from episodic experiences for cross-task reuse.
3. **Dynamic Orchestration**:
   - Real-time adjustment of skill execution paths (DAG) based on task complexity.
4. **Self-Improvement Loop**:
   - Automatically triggers experience extraction and skill mutation after task completion to convert execution logs into long-term knowledge.
5. **LLM Agent Server (ACP)**:
   - Implements the Agent Client Protocol for seamless integration with AI-native IDEs (e.g., Zed, Trae).

### 🧪 Verification & Testing
You can verify the evolution and memory chains using the following scripts:
- **Skill Evolution**: `PYTHONPATH=. uv run python src/test_evolution_flow.py`
- **Memory Abstraction**: `PYTHONPATH=. uv run python src/test_memory_flow.py`

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
1. **智能技能进化引擎 (Skill Evolution Engine)**:
   - 不同于静态的 Prompt，FinAgent-Evo 将技能定义为**“基因型” (Genotypes)**。
   - 使用 **LLM 作为元模型 (Meta-Model)**，Agent 能够根据任务反馈智能重写（变异）分析逻辑。
   - 引入 `evolve_skill` 和 `invoke_skill` 工具，实现分析逻辑的动态适配。
2. **分层记忆抽象 (Hierarchical Memory)**:
   - **工作记忆**: 处理当前任务流。
   - **情节记忆**: 存储具有代表性的成功或失败案例。
   - **程序记忆**: **知识抽象引擎** 自动从情节经验中提取“操作准则”，实现跨任务的经验复用。
3. **动态编排 (Dynamic Orchestration)**:
   - 实时调整技能执行路径（DAG），实现“按需调度”。
4. **自改进闭环**:
   - 任务结束后自动触发经验提取和技能演进，将执行结果转化为长期知识。
5. **LLM Agent 服务 (ACP)**:
   - 支持 Agent Client Protocol，可无缝集成到 Zed、Trae 等 AI 原生编辑器中。

### 🧪 验证与测试
你可以通过以下脚本验证进化与记忆链路：
- **技能进化测试**: `PYTHONPATH=. uv run python src/test_evolution_flow.py`
- **记忆抽象测试**: `PYTHONPATH=. uv run python src/test_memory_flow.py`

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
