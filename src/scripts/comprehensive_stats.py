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

def load_all_runs():
    variants_data = defaultdict(lambda: defaultdict(dict))
    
    # Read all run.json files
    for fp in glob.glob("/Users/vix/Code/FinAgent/src/benchmarks/results/**/run.json", recursive=True):
        try:
            with open(fp) as f:
                d = json.load(f)
            
            # Use folder name to determine variant
            path_parts = fp.split(os.sep)
            variant = "unknown"
            for p in path_parts:
                if "sop" in p.lower(): variant = "SOP"
                elif "react" in p.lower(): variant = "ReAct"
                elif "dvampire" in p.lower() or "finagent" in p.lower(): variant = "FinAgent"
                elif "finmem" in p.lower(): variant = "FinMem"
                elif "wo_orchestration" in p.lower(): variant = "w/o Orchestration"
                elif "wo_evolution" in p.lower() or "wo_evo" in p.lower(): variant = "w/o Evolution"
                elif "wo_memory" in p.lower() or "wo_mem" in p.lower(): variant = "w/o Memory"
                elif "full" in p.lower(): variant = "Full"
                elif "review_revise" in p.lower(): variant = "ReviewRevise"
            
            if variant == "unknown": continue
            
            results_list = d.get("results", [])
            for res in results_list:
                task_id = res.get("task_id")
                if not task_id: continue
                
                # Try new schema first
                judge_info = res.get("judge", {})
                if "parsed_agg" in judge_info:
                    score = judge_info["parsed_agg"].get("score", 0)
                    fab = judge_info["parsed_agg"].get("fabrication_detected", False)
                elif "parsed" in judge_info:
                    score = judge_info["parsed"].get("score", 0)
                    fab = judge_info["parsed"].get("fabrication_detected", False)
                else:
                    # Try old schema
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

                
                # Keep the latest run or just keep overwriting
                variants_data[variant][task_id] = {"score": score, "sr": hard_success}

        except Exception:
            pass
    return variants_data

data = load_all_runs()

for variant, tasks in data.items():
    print(f"\n[{variant}] (n={len(tasks)})")
    if not tasks: continue
    scores = [v["score"] for v in tasks.values()]
    srs = [v["sr"] for v in tasks.values()]
    print(f"Overall: Score={np.mean(scores):.1f} | SR={np.mean(srs)*100:.1f}%")
    
    # Per scenario
    scenario_scores = defaultdict(list)
    for tid, v in tasks.items():
        try:
            t_num = int(tid.replace("T", ""))
            theme_idx = (t_num - 1) // 30
            if theme_idx < len(themes):
                scenario_scores[themes[theme_idx]].append(v["score"])
        except:
            pass
            
    for i, theme in enumerate(themes):
        if theme in scenario_scores:
            print(f"  {i+1}. {theme}: {np.mean(scenario_scores[theme]):.1f} (n={len(scenario_scores[theme])})")

