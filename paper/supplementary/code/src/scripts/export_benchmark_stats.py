import argparse
import json
from collections import Counter, defaultdict
from typing import Any, Dict, List


def load_tasks(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict) and "tasks" in obj:
        return obj["tasks"]
    if isinstance(obj, list):
        return obj
    raise ValueError(f"Unsupported benchmark format: {path}")


def infer_type(task: Dict[str, Any]) -> str:
    q = (task.get("query") or task.get("task") or "").lower()
    skills = task.get("required_skills_subset") or task.get("required_skills") or []
    skills_txt = " ".join(skills).lower()
    if "dcf" in q or "dcf" in skills_txt:
        return "valuation_dcf"
    if "cpi" in q or "利率" in q or "macro" in skills_txt:
        return "macro_rates"
    if "新闻" in q or "search" in skills_txt or "news" in q:
        return "news_driven"
    if "btc" in q or "crypto" in skills_txt or "比特币" in q:
        return "crypto"
    if "期权" in q or "hedge" in q:
        return "hedging"
    return "other"


def calc_stats(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    difficulty = Counter()
    required_skills = Counter()
    task_types = Counter()
    min_tool_calls = []
    seq_lens = []
    alt_paths = []

    for t in tasks:
        if t.get("difficulty"):
            difficulty[t["difficulty"]] += 1

        skills = t.get("required_skills_subset") or t.get("required_skills") or []
        for s in skills:
            required_skills[s] += 1

        task_types[infer_type(t)] += 1

        crit = t.get("evaluation_criteria") or {}
        if isinstance(crit, dict):
            if "min_tool_calls" in crit and crit["min_tool_calls"] is not None:
                min_tool_calls.append(int(crit["min_tool_calls"]))
            seqs = crit.get("must_call_sequence") or []
            if seqs:
                alt_paths.append(len(seqs))
                seq_lens.extend([len(s) for s in seqs if isinstance(s, list)])

    stats = {
        "task_count": len(tasks),
        "difficulty_distribution": dict(difficulty),
        "required_skills_distribution": dict(required_skills.most_common()),
        "task_type_distribution": dict(task_types),
        "min_tool_calls": {
            "avg": (sum(min_tool_calls) / len(min_tool_calls)) if min_tool_calls else None,
            "min": min(min_tool_calls) if min_tool_calls else None,
            "max": max(min_tool_calls) if min_tool_calls else None,
        },
        "must_call_sequence_proxy": {
            "avg_depth": (sum(seq_lens) / len(seq_lens)) if seq_lens else None,
            "min_depth": min(seq_lens) if seq_lens else None,
            "max_depth": max(seq_lens) if seq_lens else None,
            "avg_alternative_paths": (sum(alt_paths) / len(alt_paths)) if alt_paths else None,
        },
    }
    return stats


def main():
    parser = argparse.ArgumentParser(description="Export benchmark statistics (benchmark card).")
    parser.add_argument("--input", type=str, default="src/benchmarks/tasks/complex_tasks_real_api.json")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    tasks = load_tasks(args.input)
    stats = calc_stats(tasks)

    out = args.output or (args.input.replace(".json", "_stats.json"))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(out)


if __name__ == "__main__":
    main()

