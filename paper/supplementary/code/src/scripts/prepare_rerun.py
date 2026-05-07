
import json
import os
import glob

def identify_rerun_tasks(results_dirs):
    rerun_tasks = {
        "full": set(),
        "finagent_dvampire": set(),
        "finmem": set()
    }
    
    for root_dir in results_dirs:
        run_files = glob.glob(os.path.join(root_dir, "**/run.json"), recursive=True)
        for run_file in run_files:
            variant = "unknown"
            if "full" in run_file.lower(): variant = "full"
            elif "dvampire" in run_file.lower(): variant = "finagent_dvampire"
            elif "finmem" in run_file.lower(): variant = "finmem"
            
            if variant == "unknown": continue
            
            try:
                with open(run_file, 'r') as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else data.get("results", [])
                    
                    for item in items:
                        task_id = item.get("task_id")
                        score = item.get("score", 0.0)
                        
                        # Failure criteria:
                        # 1. Low score (likely execution failure or judge error)
                        # 2. Explicit failure mode
                        # 3. Trajectory contains errors
                        
                        is_failure = False
                        failure_reason = ""
                        if score == 0.0:
                            is_failure = True
                            failure_reason = "Zero Score"
                        
                        run_info = item.get("run", {})
                        if run_info.get("failure_mode") or run_info.get("error"):
                            is_failure = True
                            failure_reason = "Run Error"
                            
                        # Check trajectory for 429s or SyntaxErrors
                        trajectory = item.get("agent", {}).get("trajectory", [])
                        for step in trajectory:
                            output = str(step.get("output", ""))
                            if "429" in output or "SyntaxError" in output or "Execution failed" in output:
                                is_failure = True
                                failure_reason = "Tool Error"
                                break
                        
                        if is_failure:
                            rerun_tasks[variant].add(task_id)
            except Exception as e:
                print(f"Error reading {run_file}: {e}")
                
    return rerun_tasks

def create_rerun_benchmark(failed_map, original_benchmark_path, output_path):
    # Load all original tasks
    with open(original_benchmark_path, 'r') as f:
        all_tasks = json.load(f)
    
    # Map task_id to task object
    task_map = {t["id"]: t for t in all_tasks}
    
    # We want a union of all failed task IDs across variants to keep it simple, 
    # OR we can just generate a benchmark with all unique failed IDs.
    all_failed_ids = set()
    for ids in failed_map.values():
        all_failed_ids.update(ids)
        
    rerun_tasks = []
    for tid in sorted(list(all_failed_ids)):
        if tid in task_map:
            rerun_tasks.append(task_map[tid])
        else:
            print(f"Warning: Task {tid} not found in {original_benchmark_path}")
            
    with open(output_path, 'w') as f:
        json.dump(rerun_tasks, f, indent=2, ensure_ascii=False)
        
    print(f"Created rerun benchmark with {len(rerun_tasks)} tasks at {output_path}")
    return all_failed_ids

if __name__ == "__main__":
    results_dirs = [
        "src/benchmarks/results/full_recovery_run",
        "src/benchmarks/results/full_run_300_sharded"
    ]
    
    failed_map = identify_rerun_tasks(results_dirs)
    
    for variant, ids in failed_map.items():
        print(f"Variant {variant}: {len(ids)} tasks identified for rerun.")
    
    # Use the combined shards as the source (or just the main pool)
    # Since we have shards 1-4, we might need to look at them all.
    # For now, let's assume we can pull from a master list if it exists, or just use shard_1 as a proxy for the format.
    
    # Actually, let's just use the task IDs and pull from the original shard files.
    source_benchmarks = ["src/benchmarks/tasks/shard_1.json", "src/benchmarks/tasks/shard_2.json", "src/benchmarks/tasks/shard_3.json", "src/benchmarks/tasks/shard_4.json"]
    all_source_tasks = []
    for sb in source_benchmarks:
        with open(sb, 'r') as f:
            data = json.load(f)
            if isinstance(data, dict) and "tasks" in data:
                all_source_tasks.extend(data["tasks"])
            elif isinstance(data, list):
                all_source_tasks.extend(data)
            
    task_map = {t["task_id"]: t for t in all_source_tasks if "task_id" in t}
    
    # Create variant-specific rerun benchmarks
    for variant, ids in failed_map.items():
        if not ids: continue
        
        rerun_list = [task_map[tid] for tid in sorted(list(ids)) if tid in task_map]
        out_path = f"src/benchmarks/rerun_{variant}.json"
        with open(out_path, 'w') as f:
            json.dump(rerun_list, f, indent=2, ensure_ascii=False)
        print(f"Created {out_path} with {len(rerun_list)} tasks.")
