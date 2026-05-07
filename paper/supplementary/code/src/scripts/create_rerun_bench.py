import json
import os

def create_rerun_benchmark():
    # Load discrepancies
    with open("audit_discrepancies.json", "r") as f:
        discrepancies = json.load(f)
    
    # Task IDs to rerun
    task_ids = [d["task_id"] for d in discrepancies]
    print(f"Planning to rerun {len(task_ids)} tasks for Full variant.")

    # Load all benchmark tasks to find the full task objects
    all_tasks = {}
    for shard_file in ["src/benchmarks/tasks/shard_1.json", "src/benchmarks/tasks/shard_2.json", "src/benchmarks/tasks/shard_3.json", "src/benchmarks/tasks/shard_4.json"]:
        if os.path.exists(shard_file):
            with open(shard_file, "r") as f:
                data = json.load(f)
                tasks_list = data.get("tasks", [])
                for task in tasks_list:
                    all_tasks[task["task_id"]] = task

    # Collect tasks
    rerun_tasks = []
    for tid in task_ids:
        if tid in all_tasks:
            rerun_tasks.append(all_tasks[tid])
        else:
            print(f"Warning: Task {tid} not found in benchmark shards.")

    # Write to new benchmark file
    with open("src/benchmarks/tasks/rerun_discrepancies_full.json", "w") as f:
        json.dump(rerun_tasks, f, indent=2)
    
    print(f"Created src/benchmarks/tasks/rerun_discrepancies_full.json with {len(rerun_tasks)} tasks.")

if __name__ == "__main__":
    create_rerun_benchmark()
