
import json
import os

base_path = "src/benchmarks/results_quantitative_fullscale_n20"
variants = {
    "Full": "1776324486_full",
    "Baseline": "1776324800_react_baseline",
    "w/o Memory": "1776332567_wo_memory",
    "w/o Orchestration": "1776333079_wo_orchestration",
    "w/o Evolution": "1776334085_wo_evolution"
}

print("| Variant | Success Rate | Avg Score | Avg Steps | Avg Latency |")
print("| :--- | :--- | :--- | :--- | :--- |")

for name, dir_name in variants.items():
    run_path = os.path.join(base_path, dir_name, "run.json")
    judge_path = os.path.join(base_path, dir_name, "judge_logs.jsonl")
    
    if os.path.exists(run_path):
        with open(run_path) as f:
            data = json.load(f)
            summary = data.get("summary", {})
            
            scores = []
            if os.path.exists(judge_path):
                with open(judge_path) as jf:
                    for line in jf:
                        try:
                            log = json.loads(line)
                            # Handle different log formats
                            score = None
                            if "judge_parsed" in log and log["judge_parsed"] and "score" in log["judge_parsed"]:
                                score = log["judge_parsed"]["score"]
                            elif "score" in log:
                                score = log["score"]
                            
                            if score is not None:
                                scores.append(score)
                        except:
                            continue
            
            avg_score = sum(scores) / len(scores) if scores else 0
            success_rate = summary.get("success_rate", 0) * 100
            steps = summary.get("tool_calls_avg", 0)
            latency = summary.get("elapsed_s_avg", 0)
            
            print(f"| {name} | {success_rate:.1f}% | {avg_score:.1f} | {steps:.1f} | {latency:.1f}s |")
    else:
        print(f"| {name} | Not Found | - | - | - |")
