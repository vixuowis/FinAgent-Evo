import json
import glob
import os
import numpy as np
from collections import defaultdict

themes = [
    "Equity Research & Valuation",
    "Macro Strategy & Forex",
    "Portfolio Risk & Sector Rotation",
    "Crypto & Alternative Assets",
    "Event-Driven & Policy Analysis",
    "Fixed Income & Credit Analysis",
    "Commodities & Supply Chain",
    "ESG & Sustainable Investing",
    "Quantitative Factors & Technicals",
    "Global Banking & Fintech"
]

scenario_stats = defaultdict(lambda: {"hard_success": [], "judge_score": [], "steps": []})

# Read all run.json files for Full variant
for fp in glob.glob("/Users/vix/Code/FinAgent/src/benchmarks/results/**/*full*/**/run.json", recursive=True):
    try:
        with open(fp) as f:
            d = json.load(f)
        
        # Check if it's actually the Full variant
        if "review_revise" in fp.lower(): continue
            
        results_list = d.get("results", [])
        for res in results_list:
            task_id = res.get("task_id")
            if not task_id: continue
            
            try:
                t_num = int(task_id.replace("T", ""))
                theme_idx = (t_num - 1) // 30
                if theme_idx >= len(themes): continue
                theme = themes[theme_idx]
            except:
                continue
                
            # Judge info
            judge_info = res.get("judge", {})
            if "parsed_agg" in judge_info:
                score = judge_info["parsed_agg"].get("score", 0)
                fab = judge_info["parsed_agg"].get("fabrication_detected", False)
            elif "parsed" in judge_info:
                score = judge_info["parsed"].get("score", 0)
                fab = judge_info["parsed"].get("fabrication_detected", False)
            else:
                parsed = res.get("judge_parsed", {})
                if isinstance(parsed, dict):
                    score = parsed.get("score", 0)
                    fab = parsed.get("fabrication_detected", False)
                else:
                    score = 0
                    fab = True
            
            derived = res.get("derived", {})
            if "hard_success" in derived:
                hard_success = 1 if derived["hard_success"] else 0
            else:
                hard_success = 1 if (not fab and score > 0) else 0
                
            # Steps
            steps = 0
            if "metrics" in res:
                steps = res["metrics"].get("tool_calls", 0)
            elif "execution_log" in res and isinstance(res["execution_log"], list):
                steps = len([x for x in res["execution_log"] if x.get("role") == "tool" or "tool_calls" in x])
            elif "trajectory" in res and isinstance(res["trajectory"], list):
                steps = len([x for x in res["trajectory"] if x.get("role") == "tool" or "tool_calls" in x])
            
            if steps == 0:
                steps = res.get("stats", {}).get("tool_calls", 0)
                
            scenario_stats[theme]["hard_success"].append(hard_success)
            scenario_stats[theme]["judge_score"].append(score)
            scenario_stats[theme]["steps"].append(steps)
            
    except Exception as e:
        pass

print("Theme | Hard Success (%) | Judge Score | Avg Steps | N")
print("-" * 60)
for theme in themes:
    stats = scenario_stats[theme]
    if stats["hard_success"]:
        hs = np.mean(stats["hard_success"]) * 100
        js = np.mean(stats["judge_score"])
        st = np.mean(stats["steps"])
        n = len(stats["hard_success"])
        print(f"{theme} | {hs:.1f}% | {js:.1f} | {st:.1f} | {n}")
    else:
        print(f"{theme} | N/A | N/A | N/A | 0")
