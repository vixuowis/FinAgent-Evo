import json
from datasets import load_dataset
import pandas as pd
import random
import traceback

TASKS = {
    "Sentiment Analysis": [
        "TheFinAI/flare-fpb", "TheFinAI/flare-fiqasa", "TheFinAI/flare-fomc", "TheFinAI/flare-tsa"
    ],
    "Classification": [
        "TheFinAI/flare-headlines", "TheFinAI/flare-finarg_ecc_auc", "TheFinAI/flare-finarg_ecc_arc",
        "TheFinAI/flare-multifin_en", "TheFinAI/flare-ma", "TheFinAI/flare-mlesg"
    ],
    "Knowledge Extraction": [
        "TheFinAI/flare-ner", "TheFinAI/flare-finer_ord", "TheFinAI/flare-finred",
        "TheFinAI/flare-causal20_sc", "TheFinAI/flare-cd"
    ],
    "Number Understanding": [
        "TheFinAI/flare-finqa", "TheFinAI/flare-tatqa", "TheFinAI/flare-fnxl", "TheFinAI/flare-fsrl",
        "TheFinAI/flare-convfinqa"
    ],
    "Text Summarization": [
        "TheFinAI/flare-ectsum", "TheFinAI/flare-edtsum"
    ],
    "Credit Scoring & Risk": [
        "TheFinAI/flare-german", "TheFinAI/flare-australian", "TheFinAI/flare-cra_lendingclub",
        "TheFinAI/flare-cra_ccf", "TheFinAI/flare-cra_ccfraud", "TheFinAI/flare-cra_polish",
        "TheFinAI/flare-cra_taiwan", "TheFinAI/flare-cra_portoseguro", "TheFinAI/flare-cra_travelinsurance"
    ],
    "Decision Making": [
        "TheFinAI/flare-sm_bigdata", "TheFinAI/flare-sm_acl", "TheFinAI/flare-sm_cikm"
    ],
    "Forecasting": []
}

def fetch_samples(task_name, num_samples=3):
    print(f"Fetching samples for {task_name}...")
    try:
        # Some might need 'test' or 'validation' split
        splits = ["test", "validation", "train"]
        dataset = None
        for split in splits:
            try:
                dataset = load_dataset(task_name, split=split, trust_remote_code=True)
                print(f"  Successfully loaded split: {split}")
                break
            except:
                continue
        
        if dataset is None:
            print(f"  Failed to load any split for {task_name}")
            return []
        
        indices = random.sample(range(len(dataset)), min(num_samples, len(dataset)))
        samples = []
        for idx in indices:
            item = dataset[idx]
            samples.append({
                "question_id": f"{task_name.split('/')[-1]}-{idx}",
                "task": task_name.split("/")[-1],
                "question": item.get("query", item.get("question", item.get("text", ""))),
                "context": item.get("context", ""),
                "ground_truth": str(item.get("answer", item.get("label", "")))
            })
        return samples
    except Exception as e:
        print(f"  Error fetching {task_name}: {str(e)}")
        # traceback.print_exc()
        return []

def main():
    all_samples = []
    # Try to get ~100 samples total by taking 6 samples from each successful task
    for category, task_list in TASKS.items():
        print(f"\nCategory: {category}")
        for task_name in task_list:
            num = 20 if category == "Decision Making" else 6
            samples = fetch_samples(task_name, num_samples=num)
            for s in samples:
                s["category"] = category
            all_samples.extend(samples)
    
    # Final summary
    print(f"\nTotal samples collected from HF: {len(all_samples)}")
    
    # Add some manual samples for missing/failed categories to reach ~100
    manual_samples = [
        {
            "question_id": "manual-ectsum-01",
            "task": "ectsum",
            "question": "Summarize this earnings call snippet in one sentence.",
            "context": "Our revenue grew by 15% year-over-year, driven by strong cloud demand, although margins were pressured by increased R&D spending on AI initiatives.",
            "ground_truth": "Revenue grew 15% on cloud demand despite AI-related R&D margin pressure.",
            "category": "Text Summarization"
        },
        {
            "question_id": "manual-sm-01",
            "task": "sm_bigdata",
            "question": "Based on this news, predict the next-day stock movement (Up/Down).",
            "context": "The company reported record-breaking quarterly profits and a 2:1 stock split.",
            "ground_truth": "Up",
            "category": "Forecasting"
        },
        {
            "question_id": "manual-sm-02",
            "task": "sm_acl",
            "question": "Predict the stock movement after this tweet: $AAPL shares plummet after the CEO's unexpected resignation.",
            "context": "",
            "ground_truth": "Down",
            "category": "Forecasting"
        },
        {
            "question_id": "manual-ner-01",
            "task": "ner",
            "question": "Extract financial entities and their types: Elon Musk sold $4 billion worth of Tesla shares.",
            "context": "",
            "ground_truth": "Elon Musk, Person; $4 billion, Amount; Tesla, Organization; Tesla shares, Asset",
            "category": "Knowledge Extraction"
        }
    ]
    all_samples.extend(manual_samples)
    
    # Save to JSON
    output_path = "benchmarks/finben/100.json"
    with open(output_path, "w") as f:
        json.dump(all_samples, f, indent=4)
    
    print(f"\nTotal samples collected: {len(all_samples)}")
    print(f"Saved to: {output_path}")

if __name__ == "__main__":
    main()
