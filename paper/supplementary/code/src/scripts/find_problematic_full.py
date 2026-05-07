import json
import os
import glob
from collections import defaultdict

def find_problematic_full():
    root_dir = "src/benchmarks/results"
    new_dirs = ["reruns", "reruns_audit", "full_recovery_run", "ablation_run_300", "quick_check"]
    
    # task_id -> {score, path, failure_mode, error}
    task_data = {}
    
    for d in new_dirs:
        path = os.path.join(root_dir, d)
        run_files = glob.glob(os.path.join(path, "**/run.json"), recursive=True)
        for run_file in run_files:
            if "OLD_BACKUP" in run_file: continue
            try:
                with open(run_file, 'r') as f:
                    data = json.load(f)
                    v_name = data.get("variant", {}).get("name") if isinstance(data.get("variant"), dict) else str(data.get("variant"))
                    if v_name != "full" and v_name != "plan_only":
                        continue
                    
                    results = data.get("results", []) or data.get("tasks", [])
                    for res in results:
                        tid = res.get("task_id")
                        if not tid: continue
                        
                        score = 0
                        judge_data = res.get("judge", {})
                        if isinstance(judge_data, dict):
                            if "parsed_agg" in judge_data:
                                score = judge_data["parsed_agg"].get("score", 0)
                            elif "parsed" in judge_data:
                                score = judge_data["parsed"].get("score", 0)
                        
                        # Keep the one with highest score, then latest mtime
                        mtime = os.path.getmtime(run_file)
                        if tid not in task_data or score > task_data[tid]['score'] or (score == task_data[tid]['score'] and mtime > task_data[tid]['mtime']):
                            task_data[tid] = {
                                "score": float(score),
                                "path": run_file,
                                "mtime": mtime,
                                "failure_mode": res.get("run", {}).get("failure_mode"),
                                "error": res.get("run", {}).get("error"),
                                "final_answer": res.get("agent", {}).get("final_answer", "")
                            }
            except:
                pass

    missing = []
    zeros = []
    low_scores = []

    for i in range(1, 301):
        tid = f"T{i:03d}"
        if tid not in task_data:
            missing.append(tid)
        else:
            d = task_data[tid]
            if d['score'] == 0:
                zeros.append((tid, d['failure_mode'], d['error']))
            elif d['score'] < 20:
                low_scores.append((tid, d['score'], d['path']))

    print("--- EvoFinAgent Problematic Cases ---")
    print(f"\nMissing Tasks ({len(missing)}):")
    print(", ".join(missing))
    
    print(f"\nZero Score Tasks ({len(zeros)}):")
    for tid, mode, err in zeros:
        print(f"- {tid}: Mode={mode}, Error={str(err)[:100]}")
        
    print(f"\nLow Score Tasks (<20) ({len(low_scores)}):")
    for tid, score, path in low_scores:
        print(f"- {tid}: Score={score}, Path={path}")

if __name__ == "__main__":
    find_problematic_full()
