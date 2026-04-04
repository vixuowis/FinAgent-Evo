from datasets import load_dataset
import json

def fetch_finben_examples():
    examples = []
    
    print("Fetching FPB examples...")
    try:
        fpb = load_dataset("TheFinAI/flare-fpb", split="test", trust_remote_code=True)
        for i in range(5):
            examples.append({
                "task": "Sentiment Analysis (FPB)",
                "question_id": f"fpb-{i}",
                "question": f"What is the sentiment of the following sentence? Choices: positive, negative, neutral.\nSentence: {fpb[i]['query']}",
                "context": "",
                "ground_truth": fpb[i]["answer"]
            })
    except Exception as e:
        print(f"Error fetching FPB: {e}")

    print("Fetching FinQA examples...")
    try:
        finqa = load_dataset("TheFinAI/flare-finqa", split="test", trust_remote_code=True)
        for i in range(5):
            # FinQA query usually includes context and question
            examples.append({
                "task": "Numerical Reasoning (FinQA)",
                "question_id": f"finqa-{i}",
                "question": finqa[i]["query"],
                "context": "",
                "ground_truth": finqa[i]["answer"]
            })
    except Exception as e:
        print(f"Error fetching FinQA: {e}")

    with open("benchmarks/finben/samples.json", "w") as f:
        json.dump(examples, f, indent=4)
    
    print(f"Saved {len(examples)} examples to benchmarks/finben/samples.json")

if __name__ == "__main__":
    fetch_finben_examples()
