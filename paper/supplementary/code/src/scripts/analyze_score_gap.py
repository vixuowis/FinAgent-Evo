import json
import os
import glob
from collections import defaultdict
import numpy as np

def analyze_gap():
    # Load task difficulties
    tid_to_diff = {}
    for i in range(1, 5):
        with open(f"src/benchmarks/shard_{i}.json", "r") as f:
            data = json.load(f)
            for t in data["tasks"]:
                tid_to_diff[t["task_id"]] = t.get("difficulty", "unknown")

    # Load consolidated results
    with open("src/benchmarks/results/final_consolidated_results.json", "r") as f:
        results = json.load(f)

    variants = ["EvoFinAgent", "wo_evolution", "wo_memory", "wo_orchestration"]
    difficulties = ["easy", "medium", "hard"]

    stats = defaultdict(lambda: defaultdict(list))
    
    for tid, v_scores in results.items():
        diff = tid_to_diff.get(tid, "unknown")
        for v, score in v_scores.items():
            stats[v][diff].append(score)

    print("| Variant | Easy | Medium | Hard | Total Avg |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    
    for v in variants:
        row = [f"**{v}**"]
        total_scores = []
        for diff in difficulties:
            scores = stats[v][diff]
            avg = np.mean(scores) if scores else 0
            row.append(f"{avg:.2f}")
            total_scores.extend(scores)
        
        total_avg = np.mean(total_scores) if total_scores else 0
        row.append(f"{total_avg:.2f}")
        print("| " + " | ".join(row) + " |")

    # Find cases where wo_orchestration >> EvoFinAgent
    print("\n--- Outlier Analysis (wo_orchestration > EvoFinAgent + 30) ---")
    outliers = []
    for tid, v_scores in results.items():
        full = v_scores.get("EvoFinAgent", 0)
        orch = v_scores.get("wo_orchestration", 0)
        if orch > full + 30:
            outliers.append((tid, tid_to_diff.get(tid), full, orch))
    
    outliers.sort(key=lambda x: x[3]-x[2], reverse=True)
    for tid, diff, full, orch in outliers[:15]:
        print(f"- {tid} ({diff}): Full={full:.1f}, ReAct={orch:.1f} | Gap: {orch-full:.1f}")

if __name__ == "__main__":
    analyze_gap()
