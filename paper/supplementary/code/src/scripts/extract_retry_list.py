
import json
import os
import glob

def get_failed_task_ids(root_dir, variant_pattern):
    failed_tasks = set()
    run_files = glob.glob(os.path.join(root_dir, "**", "run.json"), recursive=True)
    
    for run_file in run_files:
        if variant_pattern not in run_file.lower():
            continue
            
        try:
            with open(run_file, 'r') as f:
                data = json.load(f)
                items = data if isinstance(data, list) else data.get("results", [])
                
                for item in items:
                    task_id = item.get("task_id")
                    score = item.get("score", 0.0)
                    failure_mode = item.get("run", {}).get("failure_mode") or item.get("failure_mode")
                    
                    # Score 0.0 or suspicious failure modes
                    if score == 0.0 or failure_mode in ["resume_unknown", "execution", "timeout"]:
                        failed_tasks.add(task_id)
        except Exception as e:
            print(f"Error reading {run_file}: {e}")
            
    return sorted(list(failed_tasks))

if __name__ == "__main__":
    # 1. Full variant failures in recovery run
    full_failures = get_failed_task_ids("src/benchmarks/results/full_recovery_run", "full")
    print(f"full_failures = {json.dumps(full_failures)}")
    
    # 2. Baseline failures in current sharded run
    dvampire_failures = get_failed_task_ids("src/benchmarks/results/full_run_300_sharded", "finagent_dvampire")
    print(f"dvampire_failures = {json.dumps(dvampire_failures)}")
    
    finmem_failures = get_failed_task_ids("src/benchmarks/results/full_run_300_sharded", "finmem")
    print(f"finmem_failures = {json.dumps(finmem_failures)}")
