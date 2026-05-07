# EvoFinAgent Supplementary Material: Code and Benchmark

This package contains the core implementation of EvoFinAgent and the multi-skill financial orchestration benchmark (N=300) introduced in the paper.

## Structure

- code/: Implementation of the Evolution Engine, Hierarchical Memory, and DAG Orchestrator.
- src/benchmarks/: The N=300 complex tasks spanning 10 financial scenarios.
- src/data/: Initial skill library genotypes.

## Reproduction

1. Install dependencies: pip install -r code/requirements.txt
2. Set environment variables (API keys for GPT-4o, etc.).
3. Run the benchmark: python code/src/evaluation/complex_runner.py --benchmark src/benchmarks/tasks/complex_tasks_300_unique.json
