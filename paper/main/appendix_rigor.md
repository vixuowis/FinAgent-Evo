# Appendix: Evaluation Rigor & Methodology Details

## 1. Multi-Judge Consistency Analysis (Institutional-Grade Calibration)

To ensure the reliability of LLM-as-a-Judge, we conducted a calibration study between **GPT-5.4** and **Claude-Opus-4.6** across 60+ complex investment research tasks.

| Metric | Value | Interpretation |
| :--- | :--- | :--- |
| **Pearson Correlation ($r$)** | **0.786** | Strong positive correlation in scoring trends. |
| **Mean Absolute Difference (MAD)** | **16.89 / 100** | Systemic offset (Claude is more lenient). |
| **Agreement Rate ($\Delta \le 20$)** | **66.7%** | High consistency in identifying high/low performers. |
| **Agreement Rate ($\Delta \le 10$)** | **22.8%** | Divergence in fine-grained rubric interpretation. |

**Conclusion**: The strong correlation ($r=0.786$) validates the use of a Dual-Judge ensemble to mitigate single-model bias. While Claude-Opus-4.6 is generally more "optimistic," both models consistently identify the same performance bottlenecks.

## 2. Numerical Fidelity Verification (Strict Hard Success)

We implemented a programmatic verification layer to calculate the **Hard Success Rate**. Unlike standard success metrics that only check for "answer presence," our mechanism enforces **Numerical Traceability**:

- **Mechanism**: The evaluator extracts all numeric values (prices, ratios, percentages) from the agent's **Final Answer** and compares them against the **Execution Trajectory** (tool outputs from QVeris or Python REPL).
- **Threshold**: A task is marked as "Hard Success" ONLY if:
    1. The agent provides a final answer.
    2. At least **80%** of the quantitative claims in the answer can be traced back to a verified tool output within a 0.01 tolerance.
- **Impact**: This eliminates "hallucinated success" where an agent provides a correct-looking answer using fabricated data.

## 3. Train/Test Separation (State Freeze)

To prevent **Test-Time Adaptation** (leakage of task-specific knowledge into the Skill Library or Memory), we implemented a `FINAGENT_FREEZE_STATE` protocol during all benchmark runs:

- **Episodic Memory**: Retrieval is allowed (Few-shot prompting), but `extract_experience` (writing new memory) is disabled.
- **Skill Evolution**: Mutated skill prompts are loaded from the pre-trained library, but no new `mutations` are triggered based on test task performance.
- **Baseline Fairness**: This ensures that `EvoFinAgent` is compared against static baselines (like ReAct) under identical "no-learning" conditions during the test phase.
