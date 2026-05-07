import json
import glob
import os
import numpy as np

def get_overall(patterns):
    hard_success_list = []
    judge_score_list = []
    steps_list = []
    for pat in patterns:
        for fp in glob.glob(f"/Users/vix/Code/FinAgent/src/benchmarks/results/**/{pat}/**/run.json", recursive=True):
            if "review_revise" in fp.lower(): continue
            try:
                with open(fp) as f:
                    d = json.load(f)
                    
                results_list = d.get("results", [])
                for res in results_list:
                    task_id = res.get("task_id")
                    if not task_id: continue
                        
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
                        
                    hard_success_list.append(hard_success)
                    judge_score_list.append(score)
                    steps_list.append(steps)
            except Exception as e:
                pass
    return np.mean(hard_success_list)*100, np.mean(judge_score_list), np.mean(steps_list)

fa_hs, fa_sc, fa_st = get_overall(["*finagent*", "*dvampire*"])
fm_hs, fm_sc, fm_st = get_overall(["*finmem*"])
full_hs, full_sc, full_st = get_overall(["*full*"])

print(f"Full: {full_hs:.1f}% / {full_sc:.1f} / {full_st:.1f}")
print(f"FinAgent: {fa_hs:.1f}% / {fa_sc:.1f} / {fa_st:.1f}")
print(f"FinMem: {fm_hs:.1f}% / {fm_sc:.1f} / {fm_st:.1f}")
