#!/bin/bash

# EvoFinAgent Full Experimental Suite
# This script runs all variants for the NeurIPS paper.

BENCHMARK="src/benchmarks/tasks/complex_tasks_real_api.json"
REPEAT=3
OUTPUT_DIR="src/benchmarks/results/full_suite_$(date +%Y%m%d_%H%M%S)"

echo "🚀 Starting Full Experimental Suite..."
echo "Benchmark: $BENCHMARK"
echo "Repeats: $REPEAT"
echo "Output Directory: $OUTPUT_DIR"

# 1. Main Variants
VARIANTS="full,plan_only,wo_evolution,wo_memory,wo_orchestration,sop,review_revise,react_baseline"
echo "--- Running Main Variants: $VARIANTS ---"
uv run python src/evaluation/complex_runner.py \
    --benchmark $BENCHMARK \
    --variants $VARIANTS \
    --repeat $REPEAT \
    --output-dir $OUTPUT_DIR

# 2. Sensitivity Scan (ReAct Recursion Limit)
echo "--- Running Sensitivity Scan (ReAct Limits) ---"
uv run python src/evaluation/complex_runner.py \
    --benchmark $BENCHMARK \
    --variants react_limit_10,react_limit_15,react_limit_25,react_limit_50 \
    --repeat $REPEAT \
    --output-dir $OUTPUT_DIR/sensitivity

# 3. Summarize
echo "--- Summarizing Results ---"
uv run python src/scripts/summarize_neurips_runs.py --root $OUTPUT_DIR --output $OUTPUT_DIR/summary.json

echo "✅ All experiments completed. Summary available at $OUTPUT_DIR/summary.json"
