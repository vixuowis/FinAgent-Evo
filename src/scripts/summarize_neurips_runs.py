import argparse
import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple


def load_run(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_runs(root: str) -> List[str]:
    out: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn == "run.json":
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def mean(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    return sum(xs) / len(xs)


def bootstrap_ci(xs: List[float], n: int = 1000, alpha: float = 0.05) -> Tuple[Optional[float], Optional[float]]:
    if len(xs) < 2:
        return None, None
    rng = random.Random(0)
    samples = []
    for _ in range(n):
        s = [xs[rng.randrange(0, len(xs))] for _ in range(len(xs))]
        samples.append(sum(s) / len(s))
    samples.sort()
    lo = int((alpha / 2) * len(samples))
    hi = int((1 - alpha / 2) * len(samples)) - 1
    return samples[lo], samples[hi]


def summarize_run(run: Dict[str, Any]) -> Dict[str, Any]:
    schema_v = run.get("schema_version", "v1")
    results = run.get("results", [])
    
    # Task aggregation
    task_data: Dict[str, Dict[str, List[Any]]] = {}
    for r in results:
        t_id = r.get("task_id")
        if t_id not in task_data:
            task_data[t_id] = {
                "hard_success": [],
                "judge_success": [],
                "scores": [],
                "elapsed": [],
                "tool_calls": [],
            }
        
        # Hard success
        task_data[t_id]["hard_success"].append(bool(r.get("run", {}).get("success")))
        
        # Derived fields (schema v2) or fallback (schema v1)
        derived = r.get("derived") or {}
        if "judge_success" in derived:
            task_data[t_id]["judge_success"].append(bool(derived["judge_success"]))
        else:
            # Fallback for v1: use hard_success as judge_success proxy or calculate if judge present
            j = r.get("judge", {}).get("parsed", {})
            if isinstance(j, dict) and j.get("score") is not None:
                # Default threshold 70 for legacy
                task_data[t_id]["judge_success"].append(float(j.get("score", 0)) >= 70.0 and not j.get("fabrication_detected", False))
            else:
                task_data[t_id]["judge_success"].append(bool(r.get("run", {}).get("success")))
        
        # Scores
        j = r.get("judge", {}).get("parsed", {})
        if isinstance(j, dict) and j.get("score") is not None:
            try:
                task_data[t_id]["scores"].append(float(j["score"]))
            except Exception:
                pass
        
        # Resource metrics
        if r.get("run", {}).get("elapsed_s") is not None:
            task_data[t_id]["elapsed"].append(float(r["run"]["elapsed_s"]))
        if r.get("metrics", {}).get("tool_calls") is not None:
            task_data[t_id]["tool_calls"].append(float(r["metrics"]["tool_calls"]))

    # Task-level means
    task_hard_sr = [mean(v["hard_success"]) for v in task_data.values() if v["hard_success"]]
    task_judge_sr = [mean(v["judge_success"]) for v in task_data.values() if v["judge_success"]]
    task_scores = [mean(v["scores"]) for v in task_data.values() if v["scores"]]
    task_elapsed = [mean(v["elapsed"]) for v in task_data.values() if v["elapsed"]]
    task_tool_calls = [mean(v["tool_calls"]) for v in task_data.values() if v["tool_calls"]]

    # Bootstrap CI
    hard_sr_ci = bootstrap_ci(task_hard_sr) if task_hard_sr else (None, None)
    judge_sr_ci = bootstrap_ci(task_judge_sr) if task_judge_sr else (None, None)
    score_ci = bootstrap_ci(task_scores) if task_scores else (None, None)

    failure_modes: Dict[str, int] = {}
    for r in results:
        fm = r.get("run", {}).get("failure_mode")
        if fm:
            failure_modes[fm] = failure_modes.get(fm, 0) + 1

    return {
        "run_id": run.get("run_id"),
        "schema_version": schema_v,
        "variant": (run.get("variant") or {}).get("name"),
        "benchmark": (run.get("benchmark") or {}).get("path"),
        "n_tasks": len(task_data),
        "n_trials": len(results),
        "hard_success_rate": mean(task_hard_sr),
        "hard_success_rate_ci95": {"low": hard_sr_ci[0], "high": hard_sr_ci[1]},
        "judge_success_rate": mean(task_judge_sr),
        "judge_success_rate_ci95": {"low": judge_sr_ci[0], "high": judge_sr_ci[1]},
        "judge_score_mean": mean(task_scores),
        "judge_score_ci95": {"low": score_ci[0], "high": score_ci[1]},
        "elapsed_s_mean": mean(task_elapsed),
        "tool_calls_mean": mean(task_tool_calls),
        "failure_modes": dict(sorted(failure_modes.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def main():
    parser = argparse.ArgumentParser(description="Summarize NeurIPS evaluation runs (run.json).")
    parser.add_argument("--root", type=str, default="src/benchmarks/results")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    run_paths = find_runs(args.root)
    summaries = [summarize_run(load_run(p)) for p in run_paths]

    by_variant: Dict[str, List[Dict[str, Any]]] = {}
    for s in summaries:
        by_variant.setdefault(s.get("variant") or "unknown", []).append(s)

    out = {"root": args.root, "runs": summaries, "by_variant": by_variant}

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    
    # Print Markdown Table
    print("\n### Main Benchmark Summary Table")
    print("| Variant | Tasks | Trials | Hard Success Rate | Judge Success Rate | Judge Score | Latency (s) | Tool Calls |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    react_sensitivity = []
    
    for variant, runs in sorted(by_variant.items()):
        # Use latest run for each variant
        s = runs[-1]
        
        # Track react sensitivity variants separately
        if variant.startswith("react_limit_"):
            react_sensitivity.append(s)
            continue
            
        hard_sr = f"{s['hard_success_rate']*100:.1f}% ± {(s['hard_success_rate_ci95']['high']-s['hard_success_rate_ci95']['low'])/2*100:.1f}%" if s['hard_success_rate_ci95']['low'] is not None else f"{s['hard_success_rate']*100:.1f}%"
        judge_sr = f"{s['judge_success_rate']*100:.1f}% ± {(s['judge_success_rate_ci95']['high']-s['judge_success_rate_ci95']['low'])/2*100:.1f}%" if s['judge_success_rate_ci95']['low'] is not None else f"{s['judge_success_rate']*100:.1f}%"
        
        score_val = s.get('judge_score_mean')
        if score_val is not None:
            score = f"{score_val:.1f} ± {(s['judge_score_ci95']['high']-s['judge_score_ci95']['low'])/2:.1f}" if s['judge_score_ci95']['low'] is not None else f"{score_val:.1f}"
        else:
            score = "N/A"
            
        latency = f"{s['elapsed_s_mean']:.1f}" if s.get('elapsed_s_mean') is not None else "N/A"
        tools = f"{s['tool_calls_mean']:.1f}" if s.get('tool_calls_mean') is not None else "N/A"
        print(f"| {variant} | {s['n_tasks']} | {s['n_trials']} | {hard_sr} | {judge_sr} | {score} | {latency} | {tools} |")

    if react_sensitivity:
        print("\n### ReAct Recursion Limit Sensitivity Scan")
        print("| Limit | Hard SR | Judge SR | Score |")
        print("| :--- | :--- | :--- | :--- |")
        for s in sorted(react_sensitivity, key=lambda x: int(x['variant'].split("_")[-1])):
            limit = s['variant'].split("_")[-1]
            hard_sr = f"{s['hard_success_rate']*100:.1f}%"
            judge_sr = f"{s['judge_success_rate']*100:.1f}%"
            score_val = s.get('judge_score_mean')
            score = f"{score_val:.1f}" if score_val is not None else "N/A"
            print(f"| {limit} | {hard_sr} | {judge_sr} | {score} |")


if __name__ == "__main__":
    main()
