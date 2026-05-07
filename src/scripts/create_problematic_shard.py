import json
import os

def create_problematic_shard():
    problematic_tids = [
        "T145", "T179", "T219", # Missing
        "T068", "T143", "T147", "T263", # Zeros
        "T051", "T076", "T109", "T113", "T208", "T220", "T234", "T239", "T265", "T266", "T295" # Low scores
    ]
    
    all_tasks = {}
    for i in range(1, 5):
        with open(f"src/benchmarks/shard_{i}.json", "r") as f:
            data = json.load(f)
            for t in data["tasks"]:
                all_tasks[t["task_id"]] = t
                
    problematic_tasks = []
    for tid in problematic_tids:
        if tid in all_tasks:
            problematic_tasks.append(all_tasks[tid])
        else:
            print(f"Warning: Task {tid} not found in any shard!")
            
    output_path = "src/benchmarks/tasks/rerun_problematic_full.json"
    with open(output_path, "w") as f:
        json.dump({"tasks": problematic_tasks}, f, indent=2, ensure_ascii=False)
        
    print(f"Created problematic shard with {len(problematic_tasks)} tasks at {output_path}")

if __name__ == "__main__":
    create_problematic_shard()
