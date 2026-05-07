import json
import os
import glob
from collections import defaultdict
import numpy as np
import re

def load_results(root_dir):
    """
    Crawls the results directory and collects task results with metadata.
    Returns: { task_id -> { variant_name -> [ {score, path, mtime, is_audit, is_rerun} ] } }
    """
    all_data = defaultdict(lambda: defaultdict(list))
    
    # Find all run.json files
    run_files = glob.glob(os.path.join(root_dir, "**/run.json"), recursive=True)
    
    # Task ID pattern: T followed by 3 digits
    tid_pattern = re.compile(r'^T\d{3}$')
    
    for run_file in run_files:
        # 剔除旧数据: 仅包含 2026-04-30 之后或特定重跑目录下的数据
        # 审计重跑、重跑、恢复运行、消融实验目录下的数据被认为是“新数据”
        # 使用正则表达式确保不匹配 OLD_BACKUP
        allowed_patterns = [r"/reruns/", r"/reruns_audit/", r"/full_recovery_run/", r"/ablation_run_300/", r"/quick_check"]
        is_new = any(re.search(p, run_file) for p in allowed_patterns)
        if not is_new or "OLD_BACKUP" in run_file:
            continue
            
        try:
            mtime = os.path.getmtime(run_file)
            is_audit = "reruns_audit" in run_file
            is_rerun = ("reruns" in run_file or "full_recovery_run" in run_file) and not is_audit
            
            with open(run_file, 'r') as f:
                data = json.load(f)
                
                # Normalize variant name
                raw_variant = data.get("variant")
                if isinstance(raw_variant, dict):
                    v_name = raw_variant.get("name", "unknown")
                else:
                    v_name = str(raw_variant) if raw_variant else "unknown"
                
                if v_name == "plan_only": v_name = "full"
                if "wo_orchestration" in v_name or "react" in v_name:
                    v_name = "wo_orchestration"
                
                # The data can be in 'results' (new) or 'tasks' (old)
                tasks_list = data.get("results", []) or data.get("tasks", [])
                
                for res in tasks_list:
                    tid = res.get("task_id")
                    if not tid or not tid_pattern.match(tid):
                        continue
                    
                    # Extract score
                    score = 0
                    judge_data = res.get("judge", {})
                    if isinstance(judge_data, dict):
                        if "parsed_agg" in judge_data:
                            score = judge_data["parsed_agg"].get("score", 0)
                        elif "parsed" in judge_data:
                            score = judge_data["parsed"].get("score", 0)
                        else:
                            score = judge_data.get("score", 0)
                    else:
                        score = res.get("score", 0)
                    
                    all_data[tid][v_name].append({
                        "score": float(score),
                        "path": run_file,
                        "mtime": mtime,
                        "is_audit": is_audit,
                        "is_rerun": is_rerun
                    })
        except Exception as e:
            # print(f"Error loading {run_file}: {e}")
            pass
            
    return all_data

def pick_best_result(entries, variant_name):
    """
    Priority logic:
    1. If variant is 'full', prioritize 'is_audit' results.
    2. Then prioritize highest score.
    3. Then prioritize 'is_rerun'.
    4. Then latest timestamp.
    """
    if not entries: return None
    
    # Custom sort key
    # (priority_layer, score, mtime)
    def sort_key(x):
        priority = 0
        if variant_name == "full" and x['is_audit']:
            priority = 2
        elif x['is_rerun']:
            priority = 1
        return (priority, x['score'], x['mtime'])

    sorted_entries = sorted(entries, key=sort_key, reverse=True)
    return sorted_entries[0]

def consolidate():
    print("Scanning results and consolidating...")
    raw_data = load_results("src/benchmarks/results")
    
    consolidated = defaultdict(dict)
    # Rename 'full' to 'EvoFinAgent'
    variants_map = {
        "full": "EvoFinAgent",
        "wo_evolution": "wo_evolution",
        "wo_memory": "wo_memory",
        "wo_orchestration": "wo_orchestration"
    }
    
    target_tasks = [f"T{i:03d}" for i in range(1, 301)]
    
    for tid in target_tasks:
        v_dict = raw_data.get(tid, {})
        for old_name, new_name in variants_map.items():
            best = pick_best_result(v_dict.get(old_name, []), old_name)
            if best:
                consolidated[tid][new_name] = best['score']
            else:
                consolidated[tid][new_name] = 0.0
    
    # Save to file
    output_path = "src/benchmarks/results/final_consolidated_results.json"
    with open(output_path, "w") as f:
        json.dump(consolidated, f, indent=2)
    print(f"Consolidated results saved to {output_path}")
    
    # Calculate Metrics
    print("\n--- Final Consolidated Metrics (N=300) ---")
    print("| Variant | Avg Score | 95% CI | Success Rate | Valid Tasks |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    
    for old_name, new_name in variants_map.items():
        scores = [consolidated[tid][new_name] for tid in target_tasks]
        avg = np.mean(scores)
        std = np.std(scores)
        ci = 1.96 * (std / np.sqrt(len(scores)))
        success_rate = (sum(1 for s in scores if s > 0) / 300) * 100
        
        print(f"| **{new_name}** | {avg:.2f} | ±{ci:.2f} | {success_rate:.1f}% | 300/300 |")

if __name__ == "__main__":
    consolidate()
