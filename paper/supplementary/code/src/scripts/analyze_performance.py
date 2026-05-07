
import json
import os
import glob
from collections import defaultdict

def analyze_results():
    # 1. Load Task Metadata and Themes
    task_metadata = {}
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
    
    # Load from 300 unique tasks
    try:
        with open('src/benchmarks/tasks/complex_tasks_300_unique.json', 'r') as f:
            tasks_300 = json.load(f)['tasks']
            for i, t in enumerate(tasks_300):
                tid = t['task_id']
                # Theme index is based on 30 tasks per theme
                # T001 -> idx 0 -> theme 0
                # T031 -> idx 30 -> theme 1
                try:
                    t_num = int(tid[1:])
                    theme_idx = (t_num - 1) // 30
                    theme_name = themes[theme_idx] if theme_idx < len(themes) else "Other"
                except:
                    theme_name = "Other"
                
                task_metadata[tid] = {
                    'difficulty': t.get('difficulty', 'unknown'),
                    'theme': theme_name
                }
    except Exception as e:
        print(f"Error loading 300 tasks: {e}")

    # Load from real API tasks (T01-T20) - Map these to relevant themes if possible
    try:
        with open('src/benchmarks/tasks/complex_tasks_real_api.json', 'r') as f:
            tasks_api = json.load(f)['tasks']
            for t in tasks_api:
                # Manual mapping for T01-T20 to themes
                tid = t['task_id']
                theme = "Other"
                if tid in ["T01", "T04", "T05"]: theme = "Equity Research & Valuation"
                elif tid in ["T02", "T06"]: theme = "Macro Strategy & Forex"
                elif tid in ["T03", "T07"]: theme = "Crypto & Alternative Assets"
                # ... etc, for simplicity, use a default if not 300-unique
                task_metadata[tid] = {
                    'difficulty': t.get('difficulty', 'unknown'),
                    'theme': theme
                }
    except Exception as e:
        print(f"Error loading API tasks: {e}")

    # 2. Collect Judge Logs
    # Search in full_run_300_sharded and reruns
    log_files = glob.glob('src/benchmarks/results/full_run_300_sharded/*/judge_logs.jsonl')
    log_files += glob.glob('src/benchmarks/results/reruns/*/judge_logs.jsonl')
    
    results = defaultdict(lambda: defaultdict(list)) # variant -> category -> scores
    
    for log_file in log_files:
        # Extract variant from directory name
        # e.g., src/benchmarks/results/full_run_300_sharded/shard_1_full/judge_logs.jsonl -> full
        # e.g., src/benchmarks/results/reruns/rerun_s1_full/judge_logs.jsonl -> full
        dir_name = os.path.basename(os.path.dirname(log_file))
        variant = None
        if '_full' in dir_name: variant = 'full'
        elif '_finagent_dvampire' in dir_name: variant = 'finagent_dvampire'
        elif '_finmem' in dir_name: variant = 'finmem'
        
        if not variant:
            continue

        try:
            # Group scores by task_id and trial_idx to average across judges
            task_trial_scores = defaultdict(list)
            
            with open(log_file, 'r') as f:
                for line in f:
                    if not line.strip(): continue
                    data = json.loads(line)
                    task_id = data.get('task_id')
                    trial_idx = data.get('trial_idx', 0)
                    
                    # Score is in judge_parsed['score']
                    score = None
                    if 'judge_parsed' in data and data['judge_parsed']:
                        score = data['judge_parsed'].get('score')
                    
                    if task_id and score is not None:
                        task_trial_scores[(task_id, trial_idx)].append(score)
            
            # Average scores per task-trial and assign to variant/categories
            for (task_id, trial_idx), scores in task_trial_scores.items():
                avg_score = sum(scores) / len(scores)
                
                # Filter for "normal" cases: user asked for normal cases.
                # Usually, 0 scores are failures. Let's see if we should exclude them.
                # However, the user might want to see the real average including failures.
                # Let's keep non-zero scores as "normal" or just keep all.
                # Given the 429 issue, many 0s are engineering failures.
                if avg_score == 0: continue 

                meta = task_metadata.get(task_id, {'difficulty': 'unknown', 'theme': 'Other'})
                diff = meta['difficulty']
                theme = meta['theme']
                
                results[variant][f"diff_{diff}"].append(avg_score)
                results[variant][f"theme_{theme}"].append(avg_score)
                results[variant]["all"].append(avg_score)
                
        except Exception as e:
            print(f"Error reading {log_file}: {e}")

    # 3. Calculate Averages
    variants = ['full', 'finagent_dvampire', 'finmem']
    difficulties = ['diff_easy', 'diff_medium', 'diff_hard', 'all']
    
    display_themes = [f"theme_{t}" for t in themes]
    display_categories = difficulties + display_themes

    # Print Table
    header = "| Category | Full | DVampire | FinMem | Gap (Full-DV) |"
    separator = "| :--- | :---: | :---: | :---: | :---: |"
    print(header)
    print(separator)
    
    for cat in display_categories:
        label = cat.replace('diff_', '').replace('theme_', '')
        row = f"| {label} | "
        vals = []
        for v in variants:
            scores = results[v].get(cat, [])
            if scores:
                avg = sum(scores) / len(scores)
                row += f"{avg:.1f} | "
                vals.append(avg)
            else:
                row += "N/A | "
                vals.append(None)
        
        if len(vals) >= 2 and vals[0] is not None and vals[1] is not None:
            gap = vals[0] - vals[1]
            row += f"{gap:+.1f} |"
        else:
            row += "N/A |"
        print(row)

if __name__ == "__main__":
    analyze_results()
