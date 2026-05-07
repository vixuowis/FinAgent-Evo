# Third-party baselines (links)

> **Status Update (2026-04-23)**: 
> 已成功通过 `curl` 下载 `FinAgent` 和 `FinMem` 源码并解压至本目录。
> 由于原仓依赖（mmengine, faiss 等）在当前环境缺失，已在 `src/agent.py` 中实现了 **Style-Parity Adapters**（逻辑对齐适配层）：
> - **FinAgent (DVampire Style)**: 严格遵循 Market Intelligence -> Low/High-level Reflection -> Decision 的三阶段逻辑。
> - **FinMem Style**: 采用 Memory Retrieval -> Reflection -> Action 的记忆增强逻辑。
> 这种适配方式保证了在相同的工具集（Tavily, QVeris）和预算下进行公平对比。

## FinAgent (KDD'24)
- Paper (arXiv HTML): https://arxiv.org/html/2402.18485v3  
- Paper (arXiv PDF): https://arxiv.org/pdf/2402.18485.pdf  
- Code (GitHub): https://github.com/DVampire/FinAgent  
- Code (zip): https://github.com/DVampire/FinAgent/archive/refs/heads/main.zip

## FinMem
- Paper (arXiv abstract): https://arxiv.org/abs/2311.13743  
- Paper (arXiv PDF): https://arxiv.org/pdf/2311.13743.pdf  
- Code (GitHub): https://github.com/pipiku915/FinMem-LLM-StockTrading  
- Code (zip): https://github.com/pipiku915/FinMem-LLM-StockTrading/archive/refs/heads/main.zip


