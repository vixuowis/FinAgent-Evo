
import json
import os

def calculate_metrics():
    # Use benchmarks/finben/100.json instead of benchmarks/finben/samples.json
    samples_path = "benchmarks/finben/100.json"
    results_path = "benchmarks/finben/results/samples_results.json"
    
    if not os.path.exists(samples_path) or not os.path.exists(results_path):
        print(f"Required files not found: {samples_path} or {results_path}")
        return

    with open(samples_path, "r") as f:
        samples = json.load(f)
    with open(results_path, "r") as f:
        results = json.load(f)

    # Map results by question_id
    results_map = {r["question_id"]: r["success"] for r in results}

    # Define task to high-level category mapping
    # FinBen typically categorizes tasks like this:
    mapping = {
        "Information Extraction (IE)": ["NER", "FinRED", "Finer-Ord", "Knowledge Extraction"],
        "Text Analysis (TA)": ["FPB", "FiQA-SA", "TSA", "FOMC", "Headlines", "MLESG", "MA", "Sentiment Analysis", "Classification"],
        "Question Answering (QA)": ["FinQA", "TatQA", "TAT-QA", "ConvFinQA", "Number Understanding"],
        "Text Generation (TG)": ["ECTSUM", "Text Summarization"],
        "Risk Management (RM)": ["German", "Fraud Detection", "Credit Scoring & Risk", "Credit"],
        "Forecasting (FO)": ["Stock Movement", "Forecasting"],
        "Decision Making (DM)": ["DM", "Decision Making"]
    }

    # Accumulate results
    stats = {cat: {"total": 0, "success": 0} for cat in mapping.keys()}
    total_all = {"total": 0, "success": 0}

    for sample in samples:
        qid = sample["question_id"]
        if qid not in results_map:
            continue
        
        success = results_map[qid]
        task = sample.get("task", "").replace("flare-", "").lower()
        cat = sample.get("category", "")
        
        # Determine high-level category
        assigned_cat = None
        for hl_cat, tasks in mapping.items():
            # Check if task (lowered) or cat (original or lowered) is in tasks list
            if task in [t.lower() for t in tasks] or cat in tasks or cat.lower() in [t.lower() for t in tasks]:
                assigned_cat = hl_cat
                break
        
        if not assigned_cat:
            # Fallback heuristics
            if "Extraction" in cat or "NER" in task: assigned_cat = "Information Extraction (IE)"
            elif "Sentiment" in cat or "Classification" in cat or "MA" in task: assigned_cat = "Text Analysis (TA)"
            elif "Number" in cat or "QA" in task or "tatqa" in task: assigned_cat = "Question Answering (QA)"
            elif "Summarization" in cat: assigned_cat = "Text Generation (TG)"
            elif "Risk" in cat or "Credit" in cat: assigned_cat = "Risk Management (RM)"
            elif "Forecasting" in cat: assigned_cat = "Forecasting (FO)"
            elif "Decision" in cat: assigned_cat = "Decision Making (DM)"

        if assigned_cat and assigned_cat in stats:
            stats[assigned_cat]["total"] += 1
            if success:
                stats[assigned_cat]["success"] += 1
            
            total_all["total"] += 1
            if success:
                total_all["success"] += 1

    print("\n--- FinBen Accuracy Results ---")
    for cat, data in stats.items():
        if data["total"] > 0:
            acc = (data["success"] / data["total"]) * 100
            print(f"{cat}: {data['success']}/{data['total']} ({acc:.2f}%)")
        else:
            print(f"{cat}: 0/0 (N/A)")
    
    if total_all["total"] > 0:
        overall_acc = (total_all["success"] / total_all["total"]) * 100
        print(f"\nOverall Accuracy: {total_all['success']}/{total_all['total']} ({overall_acc:.2f}%)")

if __name__ == "__main__":
    calculate_metrics()
