
import json
import os

def shard_recovery():
    with open("src/benchmarks/tasks/full_recovery_benchmark.json", "r") as f:
        data = json.load(f)
        tasks = data["tasks"]
        
    num_shards = 4
    shard_size = (len(tasks) + num_shards - 1) // num_shards
    
    for i in range(num_shards):
        shard_tasks = tasks[i*shard_size : (i+1)*shard_size]
        output_path = f"src/benchmarks/recovery_shard_{i+1}.json"
        with open(output_path, "w") as f:
            json.dump({"tasks": shard_tasks}, f, indent=2)
        print(f"Saved {len(shard_tasks)} tasks to {output_path}")

if __name__ == "__main__":
    shard_recovery()
