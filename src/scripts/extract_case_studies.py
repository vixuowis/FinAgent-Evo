
import json
import os

def extract_task(run_file, task_id):
    if not os.path.exists(run_file):
        return None
    with open(run_file) as f:
        data = json.load(f)
        for r in data["results"]:
            if r["task_id"] == task_id:
                return r
    return None

full_run = "src/benchmarks/results_quantitative_fullscale_n20/1776324486_full/run.json"
baseline_run = "src/benchmarks/results_quantitative_fullscale_n20/1776324800_react_baseline/run.json"

for task_id in ["T01", "T12"]:
    print(f"\n--- {task_id} Full ---")
    full_t = extract_task(full_run, task_id)
    if full_t:
        score = full_t.get('judge', {}).get('parsed', {}).get('score', 'N/A')
        print(f"Score: {score}")
        traj = full_t.get('agent', {}).get('trajectory', [])
        print(f"Steps: {len(traj)}")
        for i, step in enumerate(traj):
            tool = step.get("skill_id") or step.get("tool")
            args = step.get("params") or step.get("args") or {}
            print(f"  {i+1}. {tool} ({args})")
    
    print(f"\n--- {task_id} Baseline ---")
    base_t = extract_task(baseline_run, task_id)
    if base_t:
        score = base_t.get('judge', {}).get('parsed', {}).get('score', 'N/A')
        print(f"Score: {score}")
        traj = base_t.get('agent', {}).get('trajectory', [])
        print(f"Steps: {len(traj)}")
        for i, step in enumerate(traj[:15]):
            tool = step.get("skill_id") or step.get("tool")
            args = step.get("params") or step.get("args") or {}
            print(f"  {i+1}. {tool} ({args})")
        if len(traj) > 15:
            print(f"  ... ({len(traj)-15} more steps)")
