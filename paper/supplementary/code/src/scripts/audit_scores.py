import json
import os
import glob
from collections import defaultdict

def load_results(directory):
    results = {}
    # Find all run.json files in the directory tree
    for run_file in glob.glob(os.path.join(directory, "**/run.json"), recursive=True):
        try:
            with open(run_file, 'r') as f:
                data = json.load(f)
                raw_variant = data.get("variant")
                if isinstance(raw_variant, dict):
                    variant_name = raw_variant.get("name", "unknown")
                else:
                    variant_name = str(raw_variant) if raw_variant else "unknown"
                
                # Normalize variant names
                if variant_name == "plan_only": variant_name = "full"
                if "wo_orchestration" in variant_name or "react" in variant_name:
                    variant_name = "wo_orchestration"
                
                # The actual results are in the 'results' list
                for res in data.get("results", []):
                    task_id = res.get("task_id")
                    # Score is nested in judge/parsed_agg/score
                    judge_data = res.get("judge", {})
                    score = 0
                    if "parsed_agg" in judge_data:
                        score = judge_data["parsed_agg"].get("score", 0)
                    elif "score" in judge_data: # Fallback
                        score = judge_data.get("score", 0)
                    
                    if task_id:
                        if task_id not in results:
                            results[task_id] = {}
                        # If multiple runs for same variant, take the best one or the one with judge scores
                        if variant_name not in results[task_id] or score > 0:
                            results[task_id][variant_name] = score
        except Exception as e:
            print(f"Error loading {run_file}: {e}")
    return results

def audit():
    # Load all results from the results directory
    all_results = load_results("src/benchmarks/results")
    
    print(f"Total tasks indexed: {len(all_results)}")
    
    # Compare Full vs wo_orchestration
    discrepancies = []
    for task_id, scores in all_results.items():
        full_score = scores.get("full", 0)
        wo_orch_score = scores.get("wo_orchestration", 0)
        
        # We only care about cases where wo_orchestration is better
        if wo_orch_score > full_score + 5:
            discrepancies.append({
                "task_id": task_id,
                "full": full_score,
                "wo_orch": wo_orch_score,
                "diff": wo_orch_score - full_score
            })
            
    # Sort by diff descending
    discrepancies.sort(key=lambda x: x['diff'], reverse=True)
    
    print(f"Found {len(discrepancies)} cases where wo_orchestration > full + 5")
    print("\nTop Discrepancies (wo_orch > full):")
    for d in discrepancies[:20]:
        print(f"Task {d['task_id']}: Full={d['full']:.1f}, wo_Orch={d['wo_orch']:.1f}, Diff={d['diff']:.1f}")

    # Also check where Full is better to see if the gap is overall negative
    full_better = []
    for task_id, scores in all_results.items():
        full_score = scores.get("full", 0)
        wo_orch_score = scores.get("wo_orchestration", 0)
        if full_score > wo_orch_score + 5:
            full_better.append({
                "task_id": task_id,
                "full": full_score,
                "wo_orch": wo_orch_score,
                "diff": full_score - wo_orch_score
            })
    full_better.sort(key=lambda x: x['diff'], reverse=True)
    print(f"\nFound {len(full_better)} cases where full > wo_orchestration + 5")
    for d in full_better[:10]:
         print(f"Task {d['task_id']}: Full={d['full']:.1f}, wo_Orch={d['wo_orch']:.1f}, Diff={d['diff']:.1f}")

    # Output discrepancies to file
    with open("audit_discrepancies.json", "w") as f:
        json.dump(discrepancies, f, indent=2)

if __name__ == "__main__":
    audit()
