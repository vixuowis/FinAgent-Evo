import os
import json
import glob

# Load original tasks
all_original_tasks = {}
for i in range(1, 5):
    with open(f'src/benchmarks/shard_{i}.json', 'r') as f:
        data = json.load(f)
        for t in data['tasks']:
            all_original_tasks[t['task_id']] = t

# Load detected failures
with open('detected_failures_jsonl.json', 'r') as f:
    failures = json.load(f)

# Create rerun benchmark files
for variant, failed_tasks in failures.items():
    rerun_tasks = []
    for ft in failed_tasks:
        tid = ft['task_id']
        if tid in all_original_tasks:
            rerun_tasks.append(all_original_tasks[tid])
    
    if rerun_tasks:
        output_file = f'src/benchmarks/rerun_{variant}.json'
        with open(output_file, 'w') as f:
            json.dump({"tasks": rerun_tasks}, f, indent=2)
        print(f"Created {output_file} with {len(rerun_tasks)} tasks.")
