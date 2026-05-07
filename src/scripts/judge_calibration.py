import argparse
import json
import os
import sys
from typing import Any, Dict, List, Tuple

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root not in sys.path:
    sys.path.insert(0, root)

from src.evaluation.utils import spearmanr


def load_run(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_human(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        out: Dict[str, Any] = {}
        for row in obj:
            tid = row.get("task_id") or row.get("id")
            if tid is not None:
                out[str(tid)] = row
        return out
    raise ValueError("Unsupported human label format")


def get_score_from_human(v: Any) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict) and "score" in v:
        return float(v["score"])
    raise ValueError("Invalid human score")


def main():
    parser = argparse.ArgumentParser(description="Judge calibration vs human labels (Spearman + error buckets).")
    parser.add_argument("--run", type=str, required=True)
    parser.add_argument("--human", type=str, required=True)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    run = load_run(args.run)
    human = load_human(args.human)

    pairs: List[Tuple[str, float, float]] = []
    for r in run.get("results", []):
        tid = str(r.get("task_id"))
        if tid not in human:
            continue
        judge_score = None
        if "judge" in r and r["judge"].get("parsed"):
            judge_score = r["judge"]["parsed"].get("score")
        if judge_score is None:
            continue
        pairs.append((tid, float(judge_score), get_score_from_human(human[tid])))

    judge_scores = [p[1] for p in pairs]
    human_scores = [p[2] for p in pairs]
    rho = spearmanr(judge_scores, human_scores)

    abs_err = [abs(a - b) for a, b in zip(judge_scores, human_scores)]
    mae = (sum(abs_err) / len(abs_err)) if abs_err else None

    buckets = {"<=5": 0, "5-10": 0, "10-20": 0, ">20": 0}
    for e in abs_err:
        if e <= 5:
            buckets["<=5"] += 1
        elif e <= 10:
            buckets["5-10"] += 1
        elif e <= 20:
            buckets["10-20"] += 1
        else:
            buckets[">20"] += 1

    out = {
        "n": len(pairs),
        "spearman_rho": rho,
        "mae": mae,
        "error_buckets": buckets,
        "pairs": [{"task_id": tid, "judge": j, "human": h, "abs_error": abs(j - h)} for tid, j, h in pairs],
    }

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(args.output)
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
