import asyncio
import json
import os
import sys
from typing import Any, Dict, List

# Add project root to sys.path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root not in sys.path:
    sys.path.insert(0, root)

from src.evaluation.judge import create_judge_configs, run_judge
from src.evaluation.utils import safe_json_dumps, utc_now_iso

async def backfill_reviewed_run(run_path: str):
    print(f"Backfilling judge scores for REVIEWED results: {run_path}")
    if not os.path.exists(run_path):
        print(f"File not found: {run_path}")
        return

    with open(run_path, "r", encoding="utf-8") as f:
        run_obj = json.load(f)

    results = run_obj.get("results", [])
    judge_cfgs = create_judge_configs()
    run_dir = os.path.dirname(run_path)
    judge_logs_path = os.path.join(run_dir, "judge_logs_reviewed_v2.jsonl")
    
    # Track changes
    updated_count = 0
    total = len(results)

    for i, r in enumerate(results):
        # SKIP LOGIC: For reviewed results, we ONLY skip if we already have "reviewed_ensemble"
        agg = r.get("judge", {}).get("parsed_agg", {})
        is_reviewed = agg.get("reasoning") == "reviewed_ensemble_v2"
        has_score = agg.get("score", 0) > 0
        
        if is_reviewed and has_score:
            continue
            
        # If it was a successful execution, we should judge it
        if not r.get("run", {}).get("success", False):
            continue

        print(f"  [{i+1}/{total}] Judging REVIEWED V2 task {r['task_id']}...")
        
        task_stub = {
            "query": r.get("query"),
            "evaluation_criteria": r.get("evaluation_criteria")
        }

        try:
            judge_items = []
            for cfg in judge_cfgs:
                # We can be a bit faster here if API allows, but let's stay safe
                await asyncio.sleep(2) 
                parsed, raw, parse_error, judge_input = await run_judge(
                    task=task_stub,
                    final_answer=r["agent"]["final_answer"],
                    trajectory=r["agent"]["trajectory"],
                    cfg=cfg,
                )
                
                judge_items.append({
                    "name": cfg.name,
                    "model": cfg.model,
                    "parsed": parsed,
                    "raw_text": raw,
                    "parse_error": parse_error,
                })

                # Log to separate reviewed logs file
                with open(judge_logs_path, "a", encoding="utf-8") as f:
                    f.write(safe_json_dumps({
                        "task_id": r["task_id"],
                        "trial_idx": r.get("trial_idx", 0),
                        "judge_name": cfg.name,
                        "judge_config": {"model": cfg.model},
                        "judge_parsed": parsed,
                        "logged_at": utc_now_iso(),
                        "is_reviewed": True
                    }) + "\n")

            # Ensemble aggregation
            scores = [float(it["parsed"].get("score", 0)) for it in judge_items]
            agg_score = (sum(scores) / len(scores)) if scores else 0.0
            fabrication = any(bool(it["parsed"].get("fabrication_detected", False)) for it in judge_items)
            
            met_set = set()
            missed_set = set()
            for it in judge_items:
                p = it.get("parsed", {})
                for m in p.get("met_metrics", []): met_set.add(str(m))
                for m in p.get("missed_metrics", []): missed_set.add(str(m))

            r["judge"] = {
                "parsed_agg": {
                    "score": agg_score,
                    "reasoning": "reviewed_ensemble_v2",
                    "met_metrics": sorted(met_set),
                    "missed_metrics": sorted(missed_set),
                    "fabrication_detected": fabrication,
                },
                "items": judge_items,
            }
            
            # Update derived metrics
            if "derived" not in r: r["derived"] = {}
            r["derived"]["judge_success"] = (agg_score >= 70.0) and not fabrication
            
            updated_count += 1
            
            # Save progress every 5 updates
            if updated_count % 5 == 0:
                with open(run_path, "w", encoding="utf-8") as f:
                    json.dump(run_obj, f, ensure_ascii=False, indent=2)
                print(f"  [Checkpoint] Saved {updated_count} reviewed results.")

        except Exception as e:
            print(f"    Error judging result {i}: {e}")

    if updated_count > 0:
        # Update summary
        from src.evaluation.complex_runner import _compute_run_summary
        run_obj["summary"] = _compute_run_summary(results, judge_enabled=True)
        
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(run_obj, f, ensure_ascii=False, indent=2)
        print(f"Done. Updated {updated_count} REVIEWED results. New Avg Score: {run_obj['summary']['avg_score']:.2f}")

async def main():
    target_run = 'src/benchmarks/results/n100_full_run/1776708903_full/run_reviewed_v2.json'
    await backfill_reviewed_run(target_run)

if __name__ == "__main__":
    asyncio.run(main())
