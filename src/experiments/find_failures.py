import os
import json
import glob

base_dir = 'src/benchmarks/results/ablation_run_300'
variants = ['wo_evolution', 'wo_memory', 'wo_orchestration']
full_dir = 'src/benchmarks/results/full_run_300_sharded'

failures = {}

def check_failures(pattern, variant_name):
    var_failures = []
    for f in glob.glob(pattern):
        try:
            with open(f) as jf:
                data = json.load(jf)
                tasks = data if isinstance(data, list) else data.get('tasks', [])
                # Extract shard number safely
                shard_num = "unknown"
                parts = f.split('/')[-2].split('_')
                for p in parts:
                    if p.isdigit():
                        shard_num = p
                        break
                
                for t in tasks:
                    task_id = t.get('task_id')
                    score = 0
                    if t.get('judge_results'):
                        score = t['judge_results'][-1].get('parsed', {}).get('score', 0)
                    
                    if score == 0:
                        var_failures.append({'shard': shard_num, 'task_id': task_id})
        except: pass
    if var_failures:
        failures[variant_name] = var_failures

for v in variants:
    check_failures(os.path.join(base_dir, f'shard_*_{v}', 'run.json'), v)

check_failures(os.path.join(full_dir, 'shard_*_full', 'run.json'), 'full')

with open('detected_failures.json', 'w') as f:
    json.dump(failures, f, indent=2)

print(f"Detected {sum(len(v) for v in failures.values())} total failures.")
for v, tasks in failures.items():
    print(f"  {v}: {len(tasks)} failures")
