import json, os

with open("/Users/vix/Code/FinAgent/src/benchmarks/results/summary_v3.json", "r") as f:
    d = json.load(f)

for k, v in d.items():
    print(f"--- {k} ---")
    if "overall" in v:
        print(v["overall"])
    if "scenarios" in v:
        for s, s_res in v["scenarios"].items():
            print(f"  {s}: {s_res}")
