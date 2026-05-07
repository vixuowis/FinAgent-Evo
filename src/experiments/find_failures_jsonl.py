import os
import json
import glob

base_dir = 'src/benchmarks/results/ablation_run_300'
variants = ['wo_evolution', 'wo_memory', 'wo_orchestration']
full_dir = 'src/benchmarks/results/full_run_300_sharded'

failures = {}

def check_failures_jsonl(pattern, variant_name):
    var_failures = []
    for f in glob.glob(pattern):
        try:
            with open(f) as jf:
                for line in jf:
                    data = json.loads(line)
                    task_id = data.get('task_id')
                    score = data.get('judge_parsed', {}).get('score', 0)
                    
                    if score == 0:
                        var_failures.append({'task_id': task_id, 'log_file': f})
        except: pass
    if var_failures:
        # Deduplicate by task_id
        unique_failures = {t['task_id']: t for t in var_failures}.values()
        failures[variant_name] = list(unique_failures)

for v in variants:
    check_failures_jsonl(os.path.join(base_dir, f'shard_*_{v}', 'judge_logs.jsonl'), v)

# Also check full run directories
check_failures_jsonl(os.path.join(full_dir, 'shard_*_full', 'judge_logs.jsonl'), 'full')
check_failures_jsonl('src/benchmarks/results/full_run_300/shard_*/judge_logs.jsonl', 'full')

with open('detected_failures_jsonl.json', 'w') as f:
    json.dump(failures, f, indent=2)

print(f"Detected {sum(len(v) for v in failures.values())} total failures from JSONL.")
for v, tasks in failures.items():
    print(f"  {v}: {len(tasks)} failures")
