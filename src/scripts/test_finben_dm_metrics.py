
import json
import os
import numpy as np
from calculate_trading_metrics import report_financial_metrics

def test_finben_dm_metrics():
    """
    Test the financial metrics on the 'Decision Making' category in FinBen results.
    We map success to a positive return and failure to a negative return.
    """
    results_path = "benchmarks/finben/results/samples_results.json"
    samples_path = "benchmarks/finben/samples.json"
    
    if not os.path.exists(results_path) or not os.path.exists(samples_path):
        print(f"Required files not found: {results_path} or {samples_path}")
        return

    with open(results_path, "r") as f:
        results = json.load(f)
    with open(samples_path, "r") as f:
        samples = json.load(f)

    # Map question_id to category
    qid_to_cat = {s["question_id"]: s["category"] for s in samples}
    
    # Filter for Decision Making results
    dm_results = []
    for r in results:
        qid = r["question_id"]
        if qid in qid_to_cat and qid_to_cat[qid] == "Decision Making":
            dm_results.append(r)
    
    if not dm_results:
        print("No Decision Making results found in samples_results.json")
        return
    
    print(f"\n--- Testing Decision Making Metrics on {len(dm_results)} samples ---")
    
    # Map success to a hypothetical daily return
    # Success: +1.5% return (good decision)
    # Failure: -1.0% return (bad decision)
    # This is a simulation for demonstration purposes.
    returns = []
    for r in dm_results:
        if r["success"]:
            returns.append(0.015)
        else:
            returns.append(-0.010)
    
    # Calculate and report metrics
    report_financial_metrics(returns)

if __name__ == "__main__":
    test_finben_dm_metrics()
