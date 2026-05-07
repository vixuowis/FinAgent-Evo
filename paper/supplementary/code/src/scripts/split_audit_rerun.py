import json
import os

def split_audit_rerun():
    with open("src/benchmarks/tasks/rerun_discrepancies_full.json", "r") as f:
        tasks = json.load(f)
    
    n = len(tasks)
    shard_size = (n + 3) // 4
    
    for i in range(4):
        shard = tasks[i*shard_size : (i+1)*shard_size]
        with open(f"src/benchmarks/audit_rerun_shard_{i+1}.json", "w") as f:
            json.dump(shard, f, indent=2)
        print(f"Created src/benchmarks/audit_rerun_shard_{i+1}.json with {len(shard)} tasks.")

if __name__ == "__main__":
    split_audit_rerun()
