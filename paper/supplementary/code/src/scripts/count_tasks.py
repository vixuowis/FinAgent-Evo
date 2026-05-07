import json
import os
import glob
from collections import defaultdict

def count_tasks():
    root_dir = "src/benchmarks/results"
    new_dirs = ["reruns", "reruns_audit", "full_recovery_run", "ablation_run_300", "quick_check"]
    
    counts = defaultdict(set)
    
    for d in new_dirs:
        path = os.path.join(root_dir, d)
        run_files = glob.glob(os.path.join(path, "**/run.json"), recursive=True)
        for f in run_files:
            try:
                with open(f, 'r') as j:
                    data = json.load(j)
                    v = data.get("variant", {})
                    v_name = v.get("name") if isinstance(v, dict) else str(v)
                    
                    if v_name == "plan_only": v_name = "full"
                    if not v_name: continue
                    if "wo_orchestration" in v_name or "react" in v_name:
                        v_name = "wo_orchestration"
                        
                    results = data.get("results", []) or data.get("tasks", [])
                    for r in results:
                        tid = r.get("task_id")
                        if tid:
                            counts[v_name].add(tid)
            except:
                pass
                
    for v, tids in counts.items():
        print(f"{v}: {len(tids)} tasks")

if __name__ == "__main__":
    count_tasks()
