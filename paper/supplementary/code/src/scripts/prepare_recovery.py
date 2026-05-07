
import json
import glob
import os

def prepare_recovery_json():
    # 1. Load all 300 tasks
    with open("src/benchmarks/tasks/complex_tasks_300_unique.json", "r") as f:
        all_tasks_data = json.load(f)
        all_tasks = all_tasks_data["tasks"] if isinstance(all_tasks_data, dict) else all_tasks_data
    
    all_task_ids = {t.get("task_id") or t.get("id") for t in all_tasks}
    id_to_task = {t.get("task_id") or t.get("id"): t for t in all_tasks}
    
    # 2. Find completed SUCCESSFUL tasks for 'full'
    directories = [
        "src/benchmarks/results/full_run_300",
        "src/benchmarks/results/full_run_300_sharded"
    ]
    
    success_ids = set()
    latest_results = {}
    
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
    
    for tid, res in latest_results.items():
        if res["score"] >= 70 and not res["fabrication"]:
            success_ids.add(tid)
            
    # 3. Recovery list = All IDs - Success IDs
    recovery_ids = all_task_ids - success_ids
    
    print(f"Total tasks: {len(all_task_ids)}")
    print(f"Successfully completed: {len(success_ids)}")
    print(f"Tasks needing (re)run: {len(recovery_ids)}")
    
    recovery_benchmark = [id_to_task[tid] for tid in sorted(list(recovery_ids)) if tid in id_to_task]
    
    output_path = "src/benchmarks/tasks/full_recovery_benchmark.json"
    with open(output_path, "w") as f:
        json.dump({"tasks": recovery_benchmark}, f, indent=2)
    
    print(f"Saved {len(recovery_benchmark)} tasks to {output_path}")

if __name__ == "__main__":
    prepare_recovery_json()
