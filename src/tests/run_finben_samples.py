import json
import asyncio
import re
import os
import sys
from uuid import uuid4
from src.agent import agent

# Result file path
RESULTS_FILE = "benchmarks/finben/results/samples_results.json"

async def evaluate_finben(test_case):
    question = test_case["question"]
    context = test_case["context"]
    ground_truth = str(test_case["ground_truth"])
    category = test_case.get("category", "General")
    task = test_case.get("task", "General")
    question_id = test_case.get("question_id", "unknown")
    
    prompt = f"Context: {context}\n\nQuestion: {question}\n\nPlease provide your final answer at the end of your response, prefixed with 'Final Answer: '."
    
    print(f"\n--- Testing [{category}] Task: {task} ({question_id}) ---")
    print(f"Question: {question}")
    
    try:
        config = {"configurable": {"thread_id": str(uuid4())}}
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config
        )
        
        last_message = result["messages"][-1]
        response_text = last_message.content
        print(f"\nAgent Response (excerpt): {response_text[:300]}...")
        
        # Extract final answer
        # Robust regex: skip markdown bolding if present
        match = re.search(r"Final Answer:\s*\**\s*(.*?)\s*\**\s*$", response_text, re.DOTALL | re.MULTILINE)
        if not match:
             # Fallback if there's text after the answer
             match = re.search(r"Final Answer:\s*\**\s*(.*?)(?:\n|\*|$)", response_text, re.DOTALL)
        
        if match:
            agent_answer = match.group(1).strip()
            # Clean bolding
            agent_answer = agent_answer.replace("**", "").replace("__", "")
            
            print(f"Agent Answer: {agent_answer}")
            print(f"Ground Truth: {ground_truth}")
            
            # More robust matching logic
            agent_answer_clean = agent_answer.lower().strip()
            ground_truth_clean = ground_truth.lower().strip()
            
            is_correct = False
            if task.startswith("flare-tsa"):
                # For sentiment scores, we check if the sign matches
                # and if the absolute difference is within a reasonable range (0.6)
                try:
                    # More robust number extraction: handle trailing dots, commas, etc.
                    num_match = re.search(r"([-]?\d*\.?\d+)", agent_answer)
                    if num_match:
                        agent_val = float(num_match.group(1))
                        gt_val = float(ground_truth)
                        # Sign match: (a > 0 and b > 0) or (a < 0 and b < 0) or (a == 0 and b == 0)
                        # We use a small epsilon to handle very close to zero values
                        if abs(gt_val) < 0.1:
                            sign_match = abs(agent_val) < 0.25
                        else:
                            sign_match = (agent_val * gt_val > 0)
                        
                        is_correct = sign_match and abs(agent_val - gt_val) < 0.6
                    else:
                        is_correct = False
                except:
                    is_correct = False
            elif category == "Sentiment Analysis" or category == "Classification" or category == "Forecasting" or category == "Credit Scoring & Risk" or category == "Decision Making":
                is_correct = ground_truth_clean in agent_answer_clean or agent_answer_clean in ground_truth_clean
            elif category == "Number Understanding":
                # Try to extract number from agent answer
                # Remove currency symbols and commas
                clean_agent_answer = agent_answer.replace("$", "").replace(",", "").replace("thousands", "").replace("million", "").replace("billion", "").strip()
                num_match = re.search(r"([-?\d\.]+)", clean_agent_answer)
                if num_match:
                    try:
                        agent_val = float(num_match.group(1))
                        gt_val = float(ground_truth.replace("$", "").replace(",", "").strip())
                        is_correct = abs(agent_val - gt_val) < 1e-2
                    except:
                        is_correct = ground_truth_clean in agent_answer_clean
                else:
                    is_correct = ground_truth_clean in agent_answer_clean
            elif task == "NER":
                gt_entities = [e.strip().lower() for e in ground_truth.replace(";", ",").split(",")]
                is_correct = all(entity in agent_answer_clean for entity in gt_entities)
            elif category == "Text Summarization":
                gt_tokens = set(re.findall(r"\w+", ground_truth.lower()))
                agent_tokens = set(re.findall(r"\w+", agent_answer_clean))
                overlap = gt_tokens.intersection(agent_tokens)
                is_correct = (len(overlap) / len(gt_tokens)) > 0.3 if gt_tokens else False
            else:
                is_correct = ground_truth_clean in agent_answer_clean or agent_answer_clean in ground_truth_clean
            
            print(f"Result: {'✅ PASS' if is_correct else '❌ FAIL'}")
            return {
                "question_id": question_id,
                "success": is_correct,
                "agent_answer": agent_answer,
                "ground_truth": ground_truth,
                "response": response_text
            }
        else:
            print("❌ Could not find 'Final Answer: ' in agent response.")
            return {
                "question_id": question_id,
                "success": False,
                "error": "No Final Answer found",
                "response": response_text
            }
            
    except Exception as e:
        print(f"❌ Error during execution: {str(e)}")
        return {
            "question_id": question_id,
            "success": False,
            "error": str(e)
        }

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run FinBen sample tests.")
    parser.add_argument("--file", type=str, default="benchmarks/finben/samples.json", help="Path to test JSON file.")
    parser.add_argument("--category", type=str, default=None, help="Filter by category name.")
    parser.add_argument("--task", type=str, default=None, help="Filter by task name.")
    parser.add_argument("--rerun-failed", action="store_true", help="Rerun failed cases.")
    args = parser.parse_args()

    test_file = args.file
    if not os.path.exists(test_file):
        print(f"Test file not found: {test_file}")
        return
        
    with open(test_file, "r") as f:
        test_cases = json.load(f)
    
    results = []
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r") as f:
                results = json.load(f)
        except:
            results = []
            
    if args.rerun_failed:
        failed_ids = {r["question_id"] for r in results if not r.get("success")}
        results = [r for r in results if r.get("success")]
        tested_ids = {r["question_id"] for r in results}
        print(f"Rerunning {len(failed_ids)} failed test cases.")
    else:
        tested_ids = {r["question_id"] for r in results}
        print(f"Loaded {len(results)} existing results. Resuming from remaining {len(test_cases) - len(results)} cases.")

    total = len(test_cases)
    for i, case in enumerate(test_cases, 1):
        qid = case.get("question_id", "unknown")
        if qid in tested_ids:
            continue
            
        if args.category and args.category.lower() not in case.get("category", "").lower():
            continue
        if args.task and args.task.lower() not in case.get("task", "").lower():
            continue
            
        print(f"\n[{i}/{total}] Processing Case {qid} ({case.get('category')} - {case.get('task')})...")
        result = await evaluate_finben(case)
        results.append(result)
        
        # Save after each case
        with open(RESULTS_FILE, "w") as f:
            json.dump(results, f, indent=4)
    
    # Summary
    success_count = sum(1 for r in results if r.get("success"))
    total_tested = len(results)
    print("\n" + "="*30)
    print(f"Summary for {test_file}: {success_count}/{total_tested} passed ({(success_count/total_tested)*100:.2f}%)")
    print("="*30)

if __name__ == "__main__":
    asyncio.run(main())
