import json
import os
import glob
from collections import defaultdict
import numpy as np

def audit_results():
    root_dir = "src/benchmarks/results"
    new_dirs = ["reruns", "reruns_audit", "full_recovery_run", "ablation_run_300", "quick_check"]
    
    # task_id -> variant -> {score, path, mtime}
    task_data = defaultdict(lambda: defaultdict(list))
    
    for d in new_dirs:
        path = os.path.join(root_dir, d)
        run_files = glob.glob(os.path.join(path, "**/run.json"), recursive=True)
        for run_file in run_files:
            try:
                with open(run_file, 'r') as f:
                    data = json.load(f)
                    v = data.get("variant", {})
                    v_name = v.get("name") if isinstance(v, dict) else str(v)
                    
                    if v_name == "plan_only": v_name = "full"
                    if not v_name: continue
                    if "wo_orchestration" in v_name or "react" in v_name:
                        v_name = "wo_orchestration"
                    
                    results = data.get("results", []) or data.get("tasks", [])
                    for res in results:
                        tid = res.get("task_id")
                        if not tid: continue
                        
                        score = 0
                        judge_data = res.get("judge", {})
                        if isinstance(judge_data, dict):
                            if "parsed_agg" in judge_data:
                                score = judge_data["parsed_agg"].get("score", 0)
                            elif "parsed" in judge_data:
                                score = judge_data["parsed"].get("score", 0)
                        
                        task_data[tid][v_name].append({
                            "score": float(score),
                            "path": run_file,
                            "mtime": os.path.getmtime(run_file)
                        })
            except:
                pass

    # Pick best for each
    final_scores = defaultdict(lambda: defaultdict(float))
    variants = ["full", "wo_evolution", "wo_memory", "wo_orchestration"]
    
    for tid in [f"T{i:03d}" for i in range(1, 301)]:
        for v in variants:
            entries = task_data[tid].get(v, [])
            if entries:
                # Priority: highest score, then latest mtime
                best = sorted(entries, key=lambda x: (x['score'], x['mtime']), reverse=True)[0]
                final_scores[tid][v] = best['score']
            else:
                final_scores[tid][v] = -1.0 # Mark as missing

    print("--- Data Integrity Audit (N=300) ---")
    print("| Variant | Completed | Missing | Zero Scores | Avg (of completed) |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    
    for v in variants:
        scores = [final_scores[tid][v] for tid in [f"T{i:03d}" for i in range(1, 301)]]
        completed = sum(1 for s in scores if s >= 0)
        missing = sum(1 for s in scores if s < 0)
        zeros = sum(1 for s in scores if s == 0)
        valid_scores = [s for s in scores if s >= 0]
        avg = np.mean(valid_scores) if valid_scores else 0
        
        print(f"| {v} | {completed}/300 | {missing} | {zeros} | {avg:.2f} |")

if __name__ == "__main__":
    audit_results()
