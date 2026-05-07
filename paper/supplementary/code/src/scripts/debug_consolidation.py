import json
import os
import glob
from collections import defaultdict

def debug_consolidation():
    root_dir = "src/benchmarks/results"
    new_dirs = ["reruns", "reruns_audit", "full_recovery_run", "ablation_run_300", "quick_check"]
    
    source_counts = defaultdict(int)
    task_sources = defaultdict(set)
    
    run_files = glob.glob(os.path.join(root_dir, "**/run.json"), recursive=True)
    
    for run_file in run_files:
        is_new = any(x in run_file for x in new_dirs)
        if not is_new: continue
        
        try:
            with open(run_file, 'r') as f:
                data = json.load(f)
                v_name = data.get("variant", {}).get("name", "unknown") if isinstance(data.get("variant"), dict) else str(data.get("variant"))
                
                if "wo_orchestration" in v_name or "react" in v_name:
                    results = data.get("results", []) or data.get("tasks", [])
                    for res in results:
                        tid = res.get("task_id")
                        if tid:
                            source_counts[run_file] += 1
                            task_sources[tid].add(run_file)
        except:
            pass

    print("--- wo_orchestration Data Sources ---")
    for src, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{src}: {count} tasks")
    
    print(f"\nTotal Unique Tasks: {len(task_sources)}")

if __name__ == "__main__":
    debug_consolidation()
