
import json
import glob
import os

def refine_failed_tasks():
    # Load all 300 tasks to get the full list of IDs
    with open("src/benchmarks/tasks/complex_tasks_300_unique.json", "r") as f:
        all_tasks_data = json.load(f)
        if isinstance(all_tasks_data, dict):
            all_tasks = all_tasks_data["tasks"]
        else:
            all_tasks = all_tasks_data
    
    all_task_ids = {t.get("task_id") or t.get("id") for t in all_tasks}
    id_to_task = {t.get("task_id") or t.get("id"): t for t in all_tasks}
    
    # We only care about the 'full' variant
    # We'll look at all results and keep the LATEST one for each task_id
    directories = [
        "src/benchmarks/results/full_run_300",
        "src/benchmarks/results/full_run_300_sharded"
    ]
    
    latest_results = {} # task_id -> {score, fabrication, logged_at}
    
    log_files = []
    for directory in directories:
        log_files.extend(glob.glob(os.path.join(directory, "**/judge_logs.jsonl"), recursive=True))
    
    for log_file in log_files:
        if "full" not in log_file:
            continue
            
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    task_id = data.get("task_id")
                    if not task_id: continue
                    
                    logged_at = data.get("logged_at", "")
                    parsed = data.get("judge_parsed", {})
                    score = parsed.get("score", 0)
                    fab = parsed.get("fabrication_detected", False)
                    
                    if task_id not in latest_results or logged_at > latest_results[task_id]["logged_at"]:
                        latest_results[task_id] = {
                            "score": score,
                            "fabrication": fab,
                            "logged_at": logged_at
                        }
                except:
                    continue
    
    failed_task_ids = []
    for tid in all_task_ids:
        res = latest_results.get(tid)
        if not res:
            # Task not run yet
            continue
        
        # Criteria for failure: score < 70 or fabrication
        if res["score"] < 70 or res["fabrication"]:
            failed_task_ids.append(tid)
            
    print(f"Total tasks in benchmark: {len(all_task_ids)}")
    print(f"Tasks with results: {len(latest_results)}")
    print(f"Failed tasks to rerun: {len(failed_task_ids)}")
    
    # Create the failed tasks benchmark file
    failed_benchmark = [id_to_task[tid] for tid in failed_task_ids if tid in id_to_task]
    
    output_path = "src/benchmarks/tasks/failed_full_tasks_to_rerun.json"
    with open(output_path, "w") as f:
        json.dump({"tasks": failed_benchmark}, f, indent=2)
    
    print(f"Saved {len(failed_benchmark)} tasks to {output_path}")

if __name__ == "__main__":
    refine_failed_tasks()
