
import json
import glob
import os

def analyze_full_errors():
    directories = [
        "src/benchmarks/results/full_run_300",
        "src/benchmarks/results/full_run_300_sharded"
    ]
    
    log_files = []
    for directory in directories:
        log_files.extend(glob.glob(os.path.join(directory, "**/judge_logs.jsonl"), recursive=True))
    
    error_samples = []
    
    for log_file in log_files:
        if "full" not in log_file:
            continue
            
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    parsed = data.get("judge_parsed", {})
                    score = parsed.get("score", 0)
                    fab = parsed.get("fabrication_detected", False)
                    reasoning = parsed.get("reasoning", "No reasoning provided.")
                    
                    if score < 50 or fab:
                        error_samples.append({
                            "task_id": data.get("task_id"),
                            "score": score,
                            "fabrication": fab,
                            "reasoning": reasoning,
                            "log_file": log_file
                        })
                        if len(error_samples) >= 10:
                            break
                except:
                    continue
            if len(error_samples) >= 10:
                break
    
    for s in error_samples:
        print(f"--- Task: {s['task_id']} ---")
        print(f"Score: {s['score']} | Fab: {s['fabrication']}")
        print(f"Reasoning: {s['reasoning']}")
        print(f"Log: {s['log_file']}\n")

if __name__ == "__main__":
    analyze_full_errors()
