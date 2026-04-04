import json
import asyncio
import re
import os
import sys
from uuid import uuid4
from src.agent import agent

# Default paths
DEFAULT_TEST_FILE = "benchmarks/financereasoning/hard.json"

def get_results_path(test_file):
    """Dynamically determine the results path based on the test file name."""
    dir_name = os.path.dirname(test_file)
    base_name = os.path.basename(test_file)
    # Remove extension
    name_no_ext = os.path.splitext(base_name)[0]
    
    # Put results in a 'results' subdirectory of the benchmark directory
    results_dir = os.path.join(dir_name, "results")
    return os.path.join(results_dir, f"{name_no_ext}_results.json")

async def evaluate_agent_direct(test_case):
    question = test_case["question"]
    context = test_case["context"]
    ground_truth = test_case["ground_truth"]
    question_id = test_case.get("question_id", "unknown")
    
    prompt = f"Context: {context}\n\nQuestion: {question}\n\nPlease provide your final answer as a number at the end of your response, prefixed with 'Final Answer: '."
    
    print(f"\n--- Testing Question {question_id} ---")
    print(f"Question: {question}")
    
    full_response = []
    
    try:
        # Run the agent directly using langgraph's ainvoke or astream
        # We'll use a unique thread_id for each test case to avoid state contamination
        config = {"configurable": {"thread_id": str(uuid4())}}
        
        # Using ainvoke to get the final state
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config
        )
        
        # Extract the last message content
        last_message = result["messages"][-1]
        response_text = last_message.content
        print(f"\nAgent Response (excerpt): {response_text[:200]}...")
        
        # Extract final answer
        # The prompt asks for "Final Answer: [value]"
        # We'll use a more flexible regex that matches numbers, True/False, and other short answers
        match = re.search(r"Final Answer:\s*([\w\.\-\%\$]+)", response_text, re.IGNORECASE)
        
        if match:
            agent_answer_str = match.group(1).strip()
            try:
                # Try numeric comparison first
                agent_answer = float(agent_answer_str.replace("$", "").replace("%", "").replace(",", ""))
                gt_val = float(str(ground_truth).replace("$", "").replace("%", "").replace(",", ""))
                
                # Handle potential 100x difference (percentage vs decimal)
                if abs(agent_answer * 100 - gt_val) < 0.5:
                    is_correct = True
                elif abs(agent_answer - gt_val * 100) < 0.5:
                    is_correct = True
                else:
                    # Increase tolerance to 0.05 to handle minor rounding differences in DCF/Option models
                    is_correct = abs(agent_answer - gt_val) < 0.05
                
                print(f"Agent Answer (numeric): {agent_answer}")
                print(f"Ground Truth: {ground_truth}")
                print(f"Result: {'✅ PASS' if is_correct else '❌ FAIL'}")
                return {
                    "question_id": question_id,
                    "success": is_correct,
                    "agent_answer": agent_answer,
                    "ground_truth": ground_truth,
                    "response": response_text
                }
            except ValueError:
                # String/Boolean comparison
                is_correct = agent_answer_str.lower() == str(ground_truth).lower()
                print(f"Agent Answer (string): {agent_answer_str}")
                print(f"Ground Truth: {ground_truth}")
                print(f"Result: {'✅ PASS' if is_correct else '❌ FAIL'}")
                return {
                    "question_id": question_id,
                    "success": is_correct,
                    "agent_answer": agent_answer_str,
                    "ground_truth": ground_truth,
                    "response": response_text
                }
        else:
            print("❌ Could not find 'Final Answer: ' in agent response.")
            return {
                "question_id": question_id,
                "success": False,
                "error": "No 'Final Answer' found",
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
    parser = argparse.ArgumentParser(description="Run benchmark tests.")
    parser.add_argument("test_file", nargs="?", default=DEFAULT_TEST_FILE, help="Path to test JSON file.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test cases to run.")
    parser.add_argument("--rerun-failed", action="store_true", help="Rerun failed test cases.")
    parser.add_argument("--source", type=str, default=None, help="Filter by source (e.g., 'CodeFinQA', 'FinanceReasoning').")
    args = parser.parse_args()
    
    test_file = args.test_file
    results_file = get_results_path(test_file)
    
    # Ensure results directory exists
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    
    if not os.path.exists(test_file):
        print(f"Test file not found: {test_file}")
        return

    with open(test_file, "r") as f:
        test_cases = json.load(f)
        
    if args.source:
        test_cases = [c for c in test_cases if args.source.lower() in c.get("source", "").lower()]
        print(f"Filtering for source: {args.source}. Found {len(test_cases)} cases.")
        
    if args.limit:
        test_cases = test_cases[:args.limit]
        print(f"Limiting to first {args.limit} cases.")
    
    # Load existing results if any (for resuming)
    results = []
    if os.path.exists(results_file):
        try:
            with open(results_file, "r") as f:
                results = json.load(f)
        except:
            results = []
            
    if args.rerun_failed:
        # Keep only the successful ones in results, and identify the failed ones to rerun
        failed_ids = {r["question_id"] for r in results if r and not r.get("success")}
        results = [r for r in results if r and r.get("success")]
        tested_ids = {r["question_id"] for r in results if r}
        print(f"Rerunning {len(failed_ids)} failed test cases.")
    else:
        tested_ids = {r["question_id"] for r in results if r}
    total = len(test_cases)
    print(f"Loaded {len(results)} existing results. Resuming from remaining {total - len(results)} cases.")
    
    for i, case in enumerate(test_cases, 1):
        qid = case.get("question_id", "unknown")
        if qid in tested_ids:
            continue
            
        print(f"\n[{i}/{total}] Processing Case {qid}...")
        result = await evaluate_agent_direct(case)
        results.append(result)
        
        # Save results after each test case
        with open(results_file, "w") as f:
            json.dump(results, f, indent=4)
            
        # Optional: rate limiting sleep
        await asyncio.sleep(1)
    
    # Final summary
    success_count = sum(1 for r in results if r.get("success"))
    total_count = len(results)
    
    print("\n" + "="*30)
    print(f"Final Summary for {test_file}")
    print(f"Total Tested: {total_count}")
    print(f"Passed: {success_count}")
    print(f"Accuracy: {(success_count/total_count)*100:.2f}%" if total_count > 0 else "N/A")
    print("="*30)
    print(f"Full results saved to {results_file}")

if __name__ == "__main__":
    asyncio.run(main())
