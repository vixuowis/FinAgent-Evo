import json
import os
import glob
import asyncio
from src.evaluation.judge import create_judge_configs, run_judge
from src.evaluation.utils import safe_json_dumps

async def backfill_failed_judges():
    root_dir = "src/benchmarks/results"
    new_dirs = ["reruns", "reruns_audit", "full_recovery_run", "ablation_run_300", "quick_check"]
    
    judge_cfgs = create_judge_configs()
    
    for d in new_dirs:
        path = os.path.join(root_dir, d)
        run_files = glob.glob(os.path.join(path, "**/run.json"), recursive=True)
        for run_file in run_files:
            if "OLD_BACKUP" in run_file: continue
            
            modified = False
            try:
                with open(run_file, 'r') as f:
                    data = json.load(f)
                
                results = data.get("results", []) or data.get("tasks", [])
                for res in results:
                    judge_data = res.get("judge", {})
                    items = judge_data.get("items", [])
                    
                    # Check if ANY judge in the ensemble failed
                    any_judge_failed = False
                    for it in items:
                        p = it.get("parsed", {})
                        reasoning = str(p.get("reasoning", "")).lower()
                        if "judge_error" in reasoning or "insufficient" in reasoning or "quota" in reasoning:
                            any_judge_failed = True
                            break
                    
                    if any_judge_failed and res.get("agent", {}).get("final_answer"):
                        print(f"Re-judging task {res.get('task_id')} in {run_file}...")
                        
                        judge_items = []
                        for cfg in judge_cfgs:
                            parsed, raw, error, _ = await run_judge(
                                res, 
                                res["agent"]["final_answer"],
                                res["agent"]["trajectory"],
                                cfg
                            )
                            judge_items.append({
                                "name": cfg.name,
                                "model": cfg.model,
                                "parsed": parsed,
                                "raw_text": raw,
                                "parse_error": error
                            })
                        
                        # Aggregation logic
                        scores = [it["parsed"].get("score", 0) for it in judge_items if "judge_error" not in str(it["parsed"].get("reasoning"))]
                        score = sum(scores)/len(scores) if scores else 0
                        
                        res["judge"] = {
                            "parsed_agg": {
                                "score": score,
                                "reasoning": "backfill_fix",
                                "met_metrics": [],
                                "missed_metrics": [],
                                "fabrication_detected": any(it["parsed"].get("fabrication_detected", False) for it in judge_items)
                            },
                            "items": judge_items
                        }
                        res["derived"]["judge_success"] = score >= 70
                        modified = True
                
                if modified:
                    with open(run_file, 'w') as f:
                        json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Error processing {run_file}: {e}")

if __name__ == "__main__":
    asyncio.run(backfill_failed_judges())
