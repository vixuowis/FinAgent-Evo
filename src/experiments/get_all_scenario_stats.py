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

scenario_stats = defaultdict(lambda: defaultdict(lambda: {"hard_success": [], "judge_score": [], "steps": []}))

def get_stats(pattern, variant_name):
    for fp in glob.glob(f"/Users/vix/Code/FinAgent/src/benchmarks/results/**/{pattern}/**/run.json", recursive=True):
        if "review_revise" in fp.lower(): continue
        try:
            with open(fp) as f:
                d = json.load(f)
                
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
                    
                steps = 0
                if "metrics" in res:
                    steps = res["metrics"].get("tool_calls", 0)
                elif "execution_log" in res and isinstance(res["execution_log"], list):
                    steps = len([x for x in res["execution_log"] if x.get("role") == "tool" or "tool_calls" in x])
                elif "trajectory" in res and isinstance(res["trajectory"], list):
                    steps = len([x for x in res["trajectory"] if x.get("role") == "tool" or "tool_calls" in x])
                
                if steps == 0:
                    steps = res.get("stats", {}).get("tool_calls", 0)
                    
                scenario_stats[variant_name][theme]["hard_success"].append(hard_success)
                scenario_stats[variant_name][theme]["judge_score"].append(score)
                scenario_stats[variant_name][theme]["steps"].append(steps)
        except Exception as e:
            pass

get_stats("*finagent*", "FinAgent")
get_stats("*dvampire*", "FinAgent")
get_stats("*finmem*", "FinMem")
get_stats("*full*", "Full")

print("Theme | " + " | ".join([f"{v} (HS/Score/Steps)" for v in ["Full", "FinAgent", "FinMem"]]))
for theme in themes:
    row = [theme]
    for v in ["Full", "FinAgent", "FinMem"]:
        stats = scenario_stats[v][theme]
        if stats["hard_success"]:
            hs = np.mean(stats["hard_success"]) * 100
            js = np.mean(stats["judge_score"])
            st = np.mean(stats["steps"])
            row.append(f"{hs:.1f}% / {js:.1f} / {st:.1f}")
        else:
            row.append("N/A / N/A / N/A")
    print(" | ".join(row))
