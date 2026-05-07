
import json
import collections

def analyze_scores(run_path):
    with open(run_path, 'r') as f:
        data = json.load(f)
    
    results = data.get('results', [])
    scores = []
    task_scores = {}
    
    for r in results:
        judge_data = r.get('judge', {})
        agg = judge_data.get('parsed_agg', {})
        # Only count if it was backfilled or has a non-zero score from elsewhere
        if agg.get('reasoning') == 'backfill_ensemble' or (agg.get('score', 0) > 0):
            score = agg.get('score', 0)
            scores.append(score)
            task_scores[r['task_id']] = score
            
    if not scores:
        print("No scores found yet.")
        return

    # Basic stats
    avg_score = sum(scores) / len(scores)
    pass_rate = sum(1 for s in scores if s >= 70) / len(scores) * 100
    
    # Distribution
    dist = collections.Counter()
    for s in scores:
        bucket = (s // 10) * 10
        dist[bucket] += 1
        
    print(f"Total tasks judged: {len(scores)}")
    print(f"Average Score: {avg_score:.2f}")
    print(f"Pass Rate (>=70): {pass_rate:.1f}%")
    print("\nScore Distribution:")
    for bucket in sorted(dist.keys(), reverse=True):
        print(f"{int(bucket)}-{int(bucket+9)}: {'█' * dist[bucket]} ({dist[bucket]})")
        
    print("\nTop 5 Tasks:")
    sorted_tasks = sorted(task_scores.items(), key=lambda x: x[1], reverse=True)
    for tid, s in sorted_tasks[:5]:
        print(f"{tid}: {s}")
        
    print("\nBottom 5 Tasks:")
    for tid, s in sorted_tasks[-5:]:
        print(f"{tid}: {s}")

if __name__ == "__main__":
    analyze_scores('src/benchmarks/results/n100_full_run/1776708903_full/run.json')
