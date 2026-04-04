import json

def create_extended_testset():
    with open("benchmarks/financereasoning/hard.json", "r") as f:
        full_data = json.load(f)
    
    # Select 12 cases (the first 12 unique question_ids to ensure diversity and include the original 2)
    # We'll filter for items that have 'question', 'context', and 'ground_truth'
    test_cases = []
    seen_ids = set()
    
    for item in full_data:
        if "question" in item and "context" in item and "ground_truth" in item:
            qid = item.get("question_id", "unknown")
            if qid not in seen_ids:
                # Basic cleaning/mapping for the test runner
                case = {
                    "question_id": qid,
                    "question": item["question"],
                    "context": item["context"],
                    "ground_truth": item["ground_truth"]
                }
                test_cases.append(case)
                seen_ids.add(qid)
        
        if len(test_cases) >= 12:
            break
            
    with open("benchmarks/financereasoning/extended.json", "w") as f:
        json.dump(test_cases, f, indent=4)
    
    print(f"Created extended testset with {len(test_cases)} cases.")

if __name__ == "__main__":
    create_extended_testset()
