import json
import os

def clean_shard(path):
    judge_logs_path = os.path.join(path, "judge_logs.jsonl")
    run_json_path = os.path.join(path, "run.json")
    
    if not os.path.exists(judge_logs_path) or not os.path.exists(run_json_path):
        print(f"Skipping {path}: missing files")
        return

    # 1. Read and filter judge_logs.jsonl
    valid_judge_lines = []
    failed_task_ids = set()
    
    with open(judge_logs_path, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                # Check if this is a failed judge attempt
                if data.get("judge_parsed", {}).get("score") == 0 and "Connection error" in data.get("judge_parsed", {}).get("reasoning", ""):
                    failed_task_ids.add(data.get("task_id"))
                    print(f"Found failed task in judge_logs: {data.get('task_id')}")
                else:
                    valid_judge_lines.append(line)
            except:
                valid_judge_lines.append(line)

    # 2. Read and filter run.json
    with open(run_json_path, "r") as f:
        run_data = json.load(f)
    
    original_count = len(run_data.get("results", []))
    new_results = [res for res in run_data.get("results", []) if res.get("task_id") not in failed_task_ids]
    
    run_data["results"] = new_results
    # Update summary task count
    if "summary" in run_data:
        run_data["summary"]["task_count"] = len(new_results)
    
    print(f"Cleaned {path}: {original_count} -> {len(new_results)} tasks. Removed: {failed_task_ids}")

    # 3. Write back
    with open(judge_logs_path, "w") as f:
        for line in valid_judge_lines:
            f.write(line)
            
    with open(run_json_path, "w") as f:
        json.dump(run_data, f, indent=2)

base_dir = "src/benchmarks/results/ablation_run_300"
for shard_dir in os.listdir(base_dir):
    full_path = os.path.join(base_dir, shard_dir)
    if os.path.isdir(full_path):
        clean_shard(full_path)
