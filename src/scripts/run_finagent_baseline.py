import os
import json
import asyncio
import time
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from src.agent import agent

load_dotenv()

async def run_finagent():
    input_path = "benchmarks/complex_tasks_real_api.json"
    output_path = "benchmarks/finagent_real_api_results.json"
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    tasks = data.get("tasks", [])[:3]
    results = []
    
    print(f"Starting FinAgent-Evo evaluation on {len(tasks)} tasks...")
    
    for i, task in enumerate(tasks):
        print(f"\n[{i+1}/{len(tasks)}] Running Task {task['task_id']}: {task['query'][:50]}...")
        start_time = time.time()
        
        try:
            config = {"configurable": {"thread_id": f"eval_finagent_{task['task_id']}"}}
            
            # Trigger the orchestrator or let the agent handle it naturally
            response = await agent.ainvoke(
                {"messages": [HumanMessage(content=task["query"])]},
                config=config
            )
            
            messages = response.get("messages", [])
            
            # Extract trajectory
            trajectory = []
            final_answer = ""
            for msg in messages:
                if msg.type == "ai":
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tc in msg.tool_calls:
                            trajectory.append({
                                "tool": tc["name"],
                                "input": tc["args"]
                            })
                    if msg.content:
                        final_answer = msg.content
                        
            elapsed_time = time.time() - start_time
            print(f"  -> Finished in {elapsed_time:.2f}s. Steps: {len(trajectory)}")
            
            results.append({
                "task_id": task["task_id"],
                "query": task["query"],
                "final_answer": final_answer,
                "trajectory": trajectory,
                "elapsed_time": elapsed_time,
                "error": None
            })
            
        except Exception as e:
            print(f"  -> Error: {e}")
            results.append({
                "task_id": task["task_id"],
                "query": task["query"],
                "final_answer": "",
                "trajectory": [],
                "elapsed_time": time.time() - start_time,
                "error": str(e)
            })
            
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"results": results}, f, indent=2, ensure_ascii=False)
        
    print(f"\nFinAgent evaluation completed. Results saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(run_finagent())