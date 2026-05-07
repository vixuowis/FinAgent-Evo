import json
import os
import glob
from collections import defaultdict

def find_missing():
    # Load consolidated results
    with open("src/benchmarks/results/final_consolidated_results.json", "r") as f:
        results = json.load(f)

    variants_map = {
        "EvoFinAgent": "full",
        "wo_evolution": "wo_evolution",
        "wo_memory": "wo_memory",
        "wo_orchestration": "wo_orchestration"
    }

    missing = defaultdict(list)
    
    for tid in [f"T{i:03d}" for i in range(1, 301)]:
        v_scores = results.get(tid, {})
        for new_name, old_name in variants_map.items():
            # In consolidate_results.py, missing tasks are set to 0.0
            # But we need to distinguish between 0.0 score and NOT RUN.
            # Actually, I'll use the audit logic.
            pass

    # Use audit logic to find truly missing
    root_dir = "src/benchmarks/results"
    new_dirs = ["reruns", "reruns_audit", "full_recovery_run", "ablation_run_300", "quick_check"]
    
    task_found = defaultdict(lambda: defaultdict(bool))
    
    for d in new_dirs:
        path = os.path.join(root_dir, d)
        run_files = glob.glob(os.path.join(path, "**/run.json"), recursive=True)
        for run_file in run_files:
            if "OLD_BACKUP" in run_file: continue
            try:
                with open(run_file, 'r') as f:
                    data = json.load(f)
                    v_name = data.get("variant", {}).get("name", "unknown") if isinstance(data.get("variant"), dict) else str(data.get("variant"))
                    if v_name == "plan_only": v_name = "full"
                    if "wo_orchestration" in v_name or "react" in v_name: v_name = "wo_orchestration"
                    
                    res_list = data.get("results", []) or data.get("tasks", [])
                    for r in res_list:
                        tid = r.get("task_id")
                        if tid: task_found[tid][v_name] = True
            except: pass

    missing_report = defaultdict(list)
    for tid in [f"T{i:03d}" for i in range(1, 301)]:
        for v in ["full", "wo_evolution", "wo_memory", "wo_orchestration"]:
            if not task_found[tid][v]:
                missing_report[v].append(tid)

    print("--- Missing Tasks Report ---")
    for v, tids in missing_report.items():
        print(f"{v}: {len(tids)} missing tasks")
        # Save to file for easy rerun
        with open(f"src/benchmarks/missing_{v}.json", "w") as f:
            json.dump(tids, f)

if __name__ == "__main__":
    find_missing()
