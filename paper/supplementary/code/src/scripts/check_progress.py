
import json
import glob
import os

def count_unique_tasks(directory):
    variants = ["full", "finagent_dvampire", "finmem"]
    stats = {v: set() for v in variants}
    
    # Check full_run_300
    log_files = glob.glob(os.path.join(directory, "*/judge_logs.jsonl"))
    print(f"Found {len(log_files)} log files in {directory}")
    for log_file in log_files:
        variant = None
        # Get the directory name containing the log file
        parent_dir = os.path.basename(os.path.dirname(log_file))
        for v in variants:
            # Check if the variant name (e.g. "finmem") is in the parent dir (e.g. "1776972026_finmem")
            if v in parent_dir:
                variant = v
                break
        
        if not variant:
            print(f"Could not determine variant for {log_file} (parent: {parent_dir})")
            continue
            
        print(f"Processing {log_file} for variant {variant}")
        with open(log_file, 'r') as f:
            lines_count = 0
            for line in f:
                try:
                    data = json.loads(line)
                    task_id = data.get("task_id")
                    if task_id:
                        stats[variant].add(task_id)
                        lines_count += 1
                except Exception as e:
                    print(f"Error parsing line in {log_file}: {e}")
                    continue
            print(f"Added {lines_count} lines from {log_file}")
    
    # Check the new sharded results if any
    sharded_dirs = [
        "src/benchmarks/results/full_run_300_sharded",
        "src/benchmarks/results/full_recovery_run"
    ]
    for sharded_dir in sharded_dirs:
        if os.path.exists(sharded_dir):
            log_files = glob.glob(os.path.join(sharded_dir, "**/judge_logs.jsonl"), recursive=True)
            print(f"Found {len(log_files)} log files in {sharded_dir}")
            for log_file in log_files:
                variant = None
                parent_dir = os.path.basename(os.path.dirname(log_file))
                for v in variants:
                    if v in parent_dir:
                        variant = v
                        break
                
                if not variant:
                    continue
                    
                with open(log_file, 'r') as f:
                    lines_count = 0
                    for line in f:
                        try:
                            data = json.loads(line)
                            task_id = data.get("task_id")
                            if task_id:
                                # For recovery run, we only count it if it's successful or we're just counting completions
                                stats[variant].add(task_id)
                                lines_count += 1
                        except:
                            continue
                    print(f"Added {lines_count} lines from {log_file} for variant {variant}")

    print("-" * 30)
    total_tasks = 300
    for v, tasks in stats.items():
        count = len(tasks)
        percentage = (count / total_tasks) * 100
        print(f"Variant: {v:20} | Completed: {count:3}/{total_tasks} | {percentage:5.1f}%")
    print("-" * 30)

if __name__ == "__main__":
    count_unique_tasks("src/benchmarks/results/full_run_300")
