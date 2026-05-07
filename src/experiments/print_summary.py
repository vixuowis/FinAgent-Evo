import json

with open("/Users/vix/Code/FinAgent/src/benchmarks/results/summary_v3.json") as f:
    d = json.load(f)

for v, runs in d.get("by_variant", {}).items():
    if not runs: continue
    for r in runs:
        sr = r.get('hard_success_rate')
        sc = r.get('judge_score_mean')
        sr_str = f"{sr*100:.1f}%" if sr is not None else "None"
        sc_str = f"{sc:.1f}" if sc is not None else "None"
        print(f"[{v}] (n={r.get('n_tasks', 0)}): SR={sr_str}, Score={sc_str}")
