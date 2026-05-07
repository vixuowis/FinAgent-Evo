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

async def backfill_plan_only(run_path: str):
    print(f"Backfilling judge scores for PLAN-ONLY results: {run_path}")
    if not os.path.exists(run_path):
        print(f"File not found: {run_path}")
        return

    with open(run_path, "r", encoding="utf-8") as f:
        run_obj = json.load(f)

    results = run_obj.get("results", [])
    judge_cfgs = create_judge_configs()
    run_dir = os.path.dirname(run_path)
    judge_logs_path = os.path.join(run_dir, "judge_logs_dual.jsonl")
    
    updated_count = 0
    total = len(results)

    for i, r in enumerate(results):
        # We want to force re-judging with the dual judge
        print(f"  [{i+1}/{total}] Judging PLAN-ONLY task {r['task_id']}...")
        
        task_stub = {
            "query": r.get("query"),
            "evaluation_criteria": r.get("evaluation_criteria")
        }

        try:
            judge_items = []
            for cfg in judge_cfgs:
                await asyncio.sleep(1) # Fast retry
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

                with open(judge_logs_path, "a", encoding="utf-8") as f:
                    f.write(safe_json_dumps({
                        "task_id": r["task_id"],
                        "judge_name": cfg.name,
                        "judge_parsed": parsed,
                        "logged_at": utc_now_iso()
                    }) + "\n")

            scores = [float(it["parsed"].get("score", 0)) for it in judge_items]
            agg_score = (sum(scores) / len(scores)) if scores else 0.0
            fabrication = any(bool(it["parsed"].get("fabrication_detected", False)) for it in judge_items)
            
            r["judge_dual"] = {
                "score": agg_score,
                "fabrication_detected": fabrication,
                "items": judge_items
            }
            
            updated_count += 1
            if updated_count % 5 == 0:
                with open(run_path, "w", encoding="utf-8") as f:
                    json.dump(run_obj, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"    Error: {e}")

    with open(run_path, "w", encoding="utf-8") as f:
        json.dump(run_obj, f, ensure_ascii=False, indent=2)
    
    # Calculate avg
    dual_scores = [x.get("judge_dual", {}).get("score", 0) for x in results if "judge_dual" in x]
    avg_dual = sum(dual_scores) / len(dual_scores) if dual_scores else 0
    print(f"Done. Plan-only Dual-Judge Avg: {avg_dual:.2f}")

async def main():
    target = 'src/benchmarks/results/1776589570_plan_only/run.json'
    await backfill_plan_only(target)

if __name__ == "__main__":
    asyncio.run(main())
