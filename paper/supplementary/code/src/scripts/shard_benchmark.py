
import json
import os

def shard_benchmark():
    benchmark_path = "src/benchmarks/tasks/complex_tasks_300_unique.json"
    with open(benchmark_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    
    # Just to be sure it's a list
    if isinstance(tasks, dict) and "tasks" in tasks:
        tasks = tasks["tasks"]
    
    # We want to split the remaining tasks for each variant.
    # But for simplicity, we can just split the WHOLE 300 into N shards.
    # Each variant runner will skip what it already did.
    
    num_shards = 4
    shard_size = len(tasks) // num_shards
    
    for i in range(num_shards):
        start = i * shard_size
        end = (i + 1) * shard_size if i < num_shards - 1 else len(tasks)
        shard_tasks = tasks[start:end]
        
        shard_path = f"src/benchmarks/shard_{i+1}.json"
        with open(shard_path, "w", encoding="utf-8") as f:
            json.dump({"tasks": shard_tasks}, f, ensure_ascii=False, indent=2)
        print(f"Created {shard_path} with {len(shard_tasks)} tasks.")

if __name__ == "__main__":
    shard_benchmark()
