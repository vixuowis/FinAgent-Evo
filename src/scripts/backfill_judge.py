
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

async def backfill_run(run_path: str):
    print(f"Backfilling judge scores for: {run_path}")
    if not os.path.exists(run_path):
        print(f"File not found: {run_path}")
        return

    with open(run_path, "r", encoding="utf-8") as f:
        run_obj = json.load(f)

    results = run_obj.get("results", [])
    judge_cfgs = create_judge_configs()
    run_dir = os.path.dirname(run_path)
    judge_logs_path = os.path.join(run_dir, "judge_logs.jsonl")
    
    # Track changes
    updated_count = 0
    total = len(results)

    for i, r in enumerate(results):
        # Skip if we already have a valid ensemble score
        agg = r.get("judge", {}).get("parsed_agg", {})
        is_ensemble = agg.get("reasoning") in ["backfill_ensemble", "resume_ensemble_mean_score"]
        has_score = agg.get("score", 0) > 0
        
        # Check for errors in individual judge items
        has_error = any("judge_error" in str(it.get("parsed", {}).get("reasoning", "")) for it in r.get("judge", {}).get("items", []))
        
        if is_ensemble and has_score and not has_error:
            # Also ensure we don't have too many duplicate items
            if len(r.get("judge", {}).get("items", [])) <= 3: # 1 baseline + 2 judges
                continue
            
        # If it was a successful execution, we should (re)judge it
        if not r.get("run", {}).get("success", False):
            continue

        print(f"  [{i+1}/{total}] Judging task {r['task_id']} trial {r.get('trial_idx', 0)}...")
        
        task_stub = {
            "query": r.get("query"),
            "evaluation_criteria": r.get("evaluation_criteria")
        }

        try:
            judge_items = []
            for cfg in judge_cfgs:
                await asyncio.sleep(5)  # Increased delay to avoid rate limits
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

                # Log to file
                with open(judge_logs_path, "a", encoding="utf-8") as f:
                    f.write(safe_json_dumps({
                        "task_id": r["task_id"],
                        "trial_idx": r.get("trial_idx", 0),
                        "judge_name": cfg.name,
                        "judge_config": {"model": cfg.model},
                        "judge_parsed": parsed,
                        "logged_at": utc_now_iso()
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
                    "reasoning": "backfill_ensemble",
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
            
            # Periodic checkpoint every 2 updates
            if updated_count % 2 == 0:
                from src.evaluation.complex_runner import _compute_run_summary
                run_obj["summary"] = _compute_run_summary(results, judge_enabled=True)
                with open(run_path, "w", encoding="utf-8") as f:
                    json.dump(run_obj, f, ensure_ascii=False, indent=2)
                print(f"  [Checkpoint] Saved updated results. Current Avg Score: {run_obj['summary']['avg_score']:.2f}")

        except Exception as e:
            print(f"    Error judging result {i}: {e}")

    if updated_count > 0:
        # Update summary using logic from complex_runner.py
        from src.evaluation.complex_runner import _compute_run_summary
        run_obj["summary"] = _compute_run_summary(results, judge_enabled=True)
        
        # Save back
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(run_obj, f, ensure_ascii=False, indent=2)
        print(f"Done. Updated {updated_count} results. New Avg Score: {run_obj['summary']['avg_score']:.2f}")
    else:
        print("No results needed backfilling.")

async def main():
    # Find all run.json files in src/benchmarks/results
    results_dir = "src/benchmarks/results"
    run_files = []
    for root_dir, dirs, files in os.walk(results_dir):
        if "run.json" in files:
            run_files.append(os.path.join(root_dir, "run.json"))
    
    # Filter for specifically the n100 run
    to_process = []
    for rf in run_files:
        if "n100_full_run" in rf:
            to_process.append(rf)
    
    print(f"Found {len(to_process)} run files to process.")
    for rf in to_process:
        await backfill_run(rf)

if __name__ == "__main__":
    asyncio.run(main())
