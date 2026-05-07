# Case Study: Deep Dive into Long-Chain Financial Reasoning

We analyze two representative tasks (T01 and T12) from our benchmark to highlight the performance gap between the Full FinAgent-Evo system and the standard ReAct baseline.

## Case 1: T01 - Intrinsic Valuation of Toyota (TM) ADR
**Task**: Evaluate TM ADR intrinsic value by fetching FCF in USD, converting to JPY via real-time FX, performing DCF, and comparing back to USD market price.

### Full FinAgent-Evo (Score: 90/100)
**Trajectory**:
1. `get_financial_statements(symbol='TM')`: Successfully retrieved JPY-denominated FCF.
2. `get_stock_price(symbol='TM')`: Obtained real-time USD ADR price.
3. `get_exchange_rate(pair='USD/JPY')`: Fetched 1:153.4 rate.
4. `python_interpreter`: **Persistence check passed**. Used the `fcf_jpy` and `usd_jpy_rate` from previous steps to calculate intrinsic value in USD.
5. `strategic_decision_making`: Concluded a 12% margin of safety.

**Why it succeeded**:
- **Orchestration**: The agent followed a clear 5-step plan without backtracking.
- **REPL Persistence**: The ability to hold variables across steps prevented "UndefinedVariable" errors and eliminated the need to re-fetch data.

### ReAct Baseline (Score: 0/100)
**Failure Mode**: **Recursion Limit (25 steps)**.
The agent fetched financial statements but got stuck in a loop trying to verify if the FCF was in USD or JPY. It repeatedly called `get_exchange_rate` and `search_financial_news` to clarify the currency unit, eventually hitting the step limit without performing a single calculation.

---

## Case 2: T12 - Energy Sector Dividend Sustainability (XOM vs CVX)
**Task**: Compare FCF dividend payout coverage for Exxon Mobil and Chevron, incorporating OPEC+ macro sentiment.

### Full FinAgent-Evo (Score: 85/100)
**Trajectory**:
1. Parallel retrieval of `get_financial_statements` for both XOM and CVX.
2. `search_financial_news`: Extracted OPEC+ production cut impact.
3. `python_interpreter`: Calculated coverage ratios (XOM: 1.4x, CVX: 1.2x).
4. `strategic_decision_making`: Recommended XOM for higher sustainability.

**Why it succeeded**:
- **Memory Injection**: Injected rules regarding "Dividend Payout Ratio calculation patterns" which streamlined the Python code generation.
- **Robust Synthesis**: Handled the comparison of two distinct entities within a single plan.

### ReAct Baseline (Score: 0/100)
**Failure Mode**: **Logical Drift / Tool Hallucination**.
After fetching XOM data, the agent "forgot" to fetch CVX data and proceeded to calculate coverage for XOM using hallucinated numbers for Chevron to complete the comparison, leading to a total score of 0 for numerical fabrication.

---

## Key Takeaway
The **70% success gap** between Full and Baseline is not just about LLM capability, but about **Workflow Control**. Without Orchestration, even the strongest LLMs suffer from logical entropy in financial tasks requiring >4 steps.
