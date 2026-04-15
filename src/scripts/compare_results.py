import json
import os

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def main():
    react_res = load_json("benchmarks/react_baseline_results.json")
    fin_res = load_json("benchmarks/finagent_results.json")
    
    if not react_res or not fin_res:
        print("Waiting for both results to be generated...")
        return
        
    print("| Task ID | ReAct Steps | ReAct Time (s) | FinAgent Steps | FinAgent Time (s) |")
    print("|---------|-------------|----------------|----------------|-------------------|")
    
    for r_task, f_task in zip(react_res["results"], fin_res["results"]):
        t_id = r_task["task_id"]
        r_steps = len(r_task["trajectory"])
        r_time = f"{r_task['elapsed_time']:.1f}"
        
        f_steps = len(f_task["trajectory"])
        f_time = f"{f_task['elapsed_time']:.1f}"
        
        print(f"| {t_id} | {r_steps} | {r_time} | {f_steps} | {f_time} |")
        
if __name__ == "__main__":
    main()