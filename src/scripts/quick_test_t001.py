import os
import sys
import asyncio
import json

# Add project root to sys.path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root not in sys.path:
    sys.path.insert(0, root)

from dotenv import load_dotenv
from src.agent import run_multi_skill_orchestrator_with_logs

load_dotenv()

async def test_task():
    task = {
        "task_id": "T001",
        "query": "请获取苹果公司（AAPL）的最新收盘价，并结合当前10万美元的投资预算，快速测算理论可买入的股数（保留两位小数），以便我进行初步头寸规划。",
        "difficulty": "easy",
        "evaluation_criteria": {
            "final_answer_metrics": [
                "苹果公司(AAPL)的最新收盘价",
                "10万美元预算可买入的股数（保留两位小数）"
            ]
        }
    }
    
    print(f"Running task: {task['task_id']}")
    print(f"Query: {task['query']}")
    
    try:
        # Generate a unique thread_id
        config = {"configurable": {"thread_id": "test_t001"}}
        
        result = await run_multi_skill_orchestrator_with_logs(task['query'], config=config)
        
        print("\n--- Final Answer ---")
        print(result.get("final_answer"))
        
        print("\n--- Execution Logs ---")
        for log in result.get("execution_logs", []):
            print(f"Tool: {log.get('tool') or log.get('skill_id')}")
            # print(f"Input: {log.get('input')}")
            # print(f"Output: {str(log.get('output'))[:200]}...")
            
    except Exception as e:
        print(f"Error running task: {e}")

if __name__ == "__main__":
    asyncio.run(test_task())
