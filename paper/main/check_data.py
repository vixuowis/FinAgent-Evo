import json, os

d = "/Users/vix/Code/FinAgent/src/benchmarks/results/final_consolidated_results.json"
if os.path.exists(d):
    with open(d) as f:
        data = json.load(f)
    for method, metrics in data.items():
        print(f"[{method}]")
        print(f"Overall: SR={metrics.get('hard_success', 0)*100:.1f}%, Score={metrics.get('judge_score', 0):.1f}")
        for s, s_metrics in metrics.get("scenarios", {}).items():
            print(f"  {s}: {s_metrics.get('score', 0):.1f}")
