# Tasks

- [x] Task 1: Save the simulated NeurIPS review
  - [x] SubTask 1.1: Extract the review content from `spec.md` (Appendix) and save it to `docs/neurips_2026_simulated_review.md` for team reference.

- [x] Task 2: Implement Procedural Memory retrieval and filtering
  - [x] SubTask 2.1: Update `src/core/memory.py` to add a retrieval mechanism (e.g., limit to top-K rules) to select the most relevant procedural rules based on the current task.
  - [x] SubTask 2.2: Ensure the orchestrator injects only the filtered rules into the system prompt to prevent context bloat.

- [x] Task 3: Setup Human Evaluation correlation framework
  - [x] SubTask 3.1: Create `src/scripts/human_eval_correlation.py` to compute Pearson and Spearman correlation metrics between LLM judge scores and mock human expert scores.

- [x] Task 4: Expand the complex orchestration benchmark dataset
  - [x] SubTask 4.1: Generate an additional 80 tasks (mocked or real) to reach N=100 and save to `benchmarks/complex_tasks_real_api_expanded.json`.

- [x] Task 5: Update the NeurIPS paper `neurips_paper/main.tex`
  - [x] SubTask 5.1: Update the Limitations section to discuss the planned N=100 expansion and human evaluation correlation.
  - [x] SubTask 5.2: Add a discussion paragraph on resolving Procedural Rule conflicts in the DAG orchestrator.
  - [x] SubTask 5.3: Add a discussion paragraph on the negative Alpha tradeoff and future multi-objective mutation to balance risk and benchmark tracking.

# Task Dependencies
- Task 1, 2, 3, 4, and 5 can be executed in parallel.