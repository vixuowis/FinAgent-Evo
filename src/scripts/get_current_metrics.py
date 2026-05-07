import json
import os
import glob
from collections import defaultdict
import numpy as np

def load_results(directory):
    results = {} # task_id -> variant -> score
    # Find all run.json files in the directory tree
    # Sort by modification time to ensure later results override earlier ones
    run_files = glob.glob(os.path.join(directory, "**/run.json"), recursive=True)
    run_files.sort(key=os.path.getmtime)

    for run_file in run_files:
        try:
            with open(run_file, 'r') as f:
                data = json.load(f)
                raw_variant = data.get("variant")
                if isinstance(raw_variant, dict):
                    variant_name = raw_variant.get("name", "unknown")
                else:
                    variant_name = str(raw_variant) if raw_variant else "unknown"
                
                # Normalize variant names
                if variant_name == "plan_only": variant_name = "full"
                if "wo_orchestration" in variant_name or "react" in variant_name:
                    variant_name = "wo_orchestration"
                
                # Check 'results' list (new format)
                for res in data.get("results", []):
                    task_id = res.get("task_id")
                    judge_data = res.get("judge", {})
                    score = 0
                    if "parsed_agg" in judge_data:
                        score = judge_data["parsed_agg"].get("score", 0)
                    elif "score" in judge_data:
                        score = judge_data.get("score", 0)
                    
                    if task_id:
                        if task_id not in results: results[task_id] = {}
                        results[task_id][variant_name] = score

                # Check 'tasks' list (old format)
                for task in data.get("tasks", []):
                    task_id = task.get("task_id")
                    score = task.get("score", 0)
                    if task_id:
                        if task_id not in results: results[task_id] = {}
                        results[task_id][variant_name] = score
        except Exception as e:
            pass
    return results

def get_metrics():
    all_results = load_results("src/benchmarks/results")
    
    variants = ["full", "wo_evolution", "wo_memory", "wo_orchestration"]
    summary = {}
    
    for var in variants:
        scores = [res.get(var, 0) for tid, res in all_results.items() if var in res]
        if scores:
            avg = np.mean(scores)
            std = np.std(scores)
            ci = 1.96 * (std / np.sqrt(len(scores)))
            success_rate = sum(1 for s in scores if s > 0) / 300 * 100 # Total benchmark is 300
            summary[var] = {
                "avg": avg,
                "ci": ci,
                "count": len(scores),
                "success_rate": success_rate
            }

    print("| Variant | Avg Score | 95% CI | Success Rate | Count |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    for var in variants:
        if var in summary:
            s = summary[var]
            print(f"| **{var}** | {s['avg']:.2f} | ±{s['ci']:.2f} | {s['success_rate']:.1f}% | {s['count']}/300 |")

if __name__ == "__main__":
    get_metrics()
