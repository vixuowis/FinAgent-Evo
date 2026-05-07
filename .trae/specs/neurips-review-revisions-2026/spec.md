# NeurIPS Review Revisions Spec

## Why
We received a simulated NeurIPS review for the FinAgent-Evo paper. The review gave a 7/10 (Accept / Good Paper) but highlighted several weaknesses: small sample size (N=20), lack of human evaluation baselines, and procedural memory context bloat. It also raised questions for the rebuttal regarding evolution robustness, rule conflicts, and the negative Alpha issue in InvestorBench. We need to plan experiments and paper improvements to address these points.

## What Changes
- Save the simulated NeurIPS review for record-keeping.
- Implement Procedural Memory retrieval/filtering to limit context bloat as the agent runs longer.
- Expand the complex orchestration benchmark dataset from N=20 to N=100 using cached/simulated environments.
- Create an evaluation script to compare LLM-as-a-judge scores with human expert baselines (Pearson/Spearman correlation).
- Update the `main.tex` manuscript to explicitly address the review's weaknesses and rebuttal questions (e.g., adding multi-objective mutation discussion for the negative Alpha, clarifying DAG conflict resolution).

## Impact
- Affected specs: N/A
- Affected code: `src/core/memory.py`, `src/scripts/`, `neurips_paper/main.tex`

## ADDED Requirements
### Requirement: Procedural Memory Retrieval
The system SHALL implement a filtering/retrieval mechanism for procedural memory rules to prevent System Prompt context window bloat.

### Requirement: Benchmark Expansion
The system SHALL support evaluating on a 100-task benchmark suite with simulated/cached APIs.

### Requirement: Human-Eval Correlation
The system SHALL provide a script to calculate Pearson/Spearman correlation between LLM judge scores and human expert scores.

## MODIFIED Requirements
### Requirement: Paper Manuscript
The `main.tex` SHALL be updated to address sample size limitations, human-eval plans, rule conflict resolution, and the negative Alpha tradeoff.

---

## Appendix: Simulated NeurIPS Review Content
**Title:** FinAgent-Evo: LLM-Driven Skill Evolution and Hierarchical Memory for Robust Multi-Skill Financial Agents
**Recommendation:** **7/10 (Accept / Good Paper)** 
**Confidence:** 4/5 (Confident)

**1. Summary**
The paper proposes FinAgent-Evo to solve vulnerabilities in multi-skill long-sequence financial tasks. It abstracts skills as evolvable prompt genotypes and uses a DAG orchestrator for numerical consistency audits. It achieves 95.0% Hard-Success and 81.4% Judge-Success, dropping numerical hallucinations to 5%.

**2. Soundness: 7/10**
- Strengths: DAG + Python REPL audit mechanism is excellent; ablation studies are very thorough.
- Weaknesses: Sample size (N=20) is too small; reliance on LLM-as-a-judge without human evaluation correlation.

**3. Significance: 8/10**
- Addresses real financial agent pain points (hallucinations, non-stationarity). High practical value.

**4. Novelty: 7/10**
- Combinatorial novelty in defining skills as strict I/O genotypes and tying evolution to API feedback. Episodic to Procedural rule abstraction is a great paradigm.

**5. Clarity: 9/10**
- Extremely clear structure, strong data presentation, and highly reproducible appendices.

**6. Strengths**
- Directly solves financial agent hallucinations.
- Detailed ablation analysis.
- Honest limitations analysis (e.g., negative Alpha, w/o Memory hard-success anomaly).

**7. Weaknesses**
- Small test set (N=20). Needs expansion to N=100.
- Lack of Human Evaluation baseline.
- Procedural Memory context bloat (no rule retrieval/filtering mentioned).

**8. Questions for Rebuttal**
- Evolution Engine robustness against bad meta-model mutations?
- How does the DAG Orchestrator handle conflicting Procedural Rules?
- Does strict schema validation inhibit high-risk/high-reward trades (Negative Alpha)? How to balance this with multi-objective mutation?