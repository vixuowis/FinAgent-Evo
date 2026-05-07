
import json
import os
import glob

def find_failures(root_dir):
    failures = {}
    
    # Search for run.json files
    run_files = glob.glob(os.path.join(root_dir, "**/run.json"), recursive=True)
    
    for run_file in run_files:
        try:
            with open(run_file, 'r') as f:
                data = json.load(f)
                
                # Check if it's a list of results (new format) or a dict (old format)
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict) and "results" in data:
                    items = data["results"]
                else:
                    continue
                
                # Identify the variant from the path or data
                variant = "unknown"
                path_parts = run_file.split(os.sep)
                for part in path_parts:
                    if "full" in part.lower(): variant = "full"
                    elif "dvampire" in part.lower(): variant = "finagent_dvampire"
                    elif "finmem" in part.lower(): variant = "finmem"
                
                for item in items:
                    task_id = item.get("task_id")
                    score = item.get("score", 0.0)
                    
                    # Also check if it's a failure in judgment or generation
                    # Sometimes score is 0.0 because of actual poor performance, 
                    # but usually in this context it's an error.
                    if score == 0.0:
                        if variant not in failures:
                            failures[variant] = set()
                        failures[variant].add(task_id)
        except Exception as e:
            print(f"Error reading {run_file}: {e}")
            
    return failures

if __name__ == "__main__":
    results_dir = "src/benchmarks/results"
    failures = find_failures(results_dir)
    
    for variant, task_ids in failures.items():
        sorted_tasks = sorted(list(task_ids))
        print(f"\n### Variant: {variant} ({len(sorted_tasks)} failures) ###")
        print(",".join(sorted_tasks))
