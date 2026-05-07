# FinAgent-Evo Complex Orchestration Benchmark Card

## Overview
This benchmark evaluates the ability of financial agents to orchestrate multiple specialized tools to solve complex, multi-step financial reasoning and data retrieval tasks.

- **Tasks (N)**: 20
- **Trials per Task (R)**: 3
- **Evaluation**: Dual success metrics (Hard-success and Judge-success).
- **Tool Suite**: QVeris MCP (Real-time Financial APIs).

## Task Taxonomy
The 20 tasks cover the following categories:
1. **Valuation & DCF Modeling**: Multi-step intrinsic value assessment with cross-currency conversion.
2. **Macro Interest Rate Analysis**: Correlation between central bank policy and asset yields.
3. **Cross-Asset Ratio Analysis**: Equity vs. Crypto relative value modeling.
4. **Sentiment-Driven Trading**: News mining integrated with technical price levels.

## Parity Audit (Submission-Ready)
To ensure reproducibility and fair comparison, we fix the following budgets across all methods:
- **Tool Access**: All agents share the same MCP tool IDs and schemas.
- **Cache Policy**: `cache-at-time` enabled for tool responses to ensure deterministic inputs across variants.
- **Timeout**: 180 seconds per task.
- **Max Retries**: 3 per tool call.
- **Judge Configuration**: 
  - Model: `Qwen3.6-plus`
  - Temperature: 0
  - Rubric: Fixed JSON-output prompt (see Appendix of Paper).

## Reproducibility Assets
The following assets are provided in the repository for audit:
- `src/benchmarks/complex_tasks_real_api.json`: Raw task definitions.
- `src/benchmarks/results_neurips_v5_full/`: Complete execution logs, judge outputs, and aggregated stats.
- `src/core/qveris_cache.py`: Implementation of the response caching layer.
