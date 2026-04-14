import os
import json
import asyncio
import time
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from deepagents import create_deep_agent

load_dotenv()

# Setup Qwen model via DashScope
llm = ChatOpenAI(
    api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url=os.environ.get("DASHSCOPE_BASE_URL"),
    model=os.environ.get("DASHSCOPE_MODEL")
)

@tool
def calculator(expression: str) -> str:
    """A simple calculator tool. Pass a mathematical expression like '2 * (3 + 4)'."""
    try:
        # Use eval safely by restricting globals and locals
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"

# Initialize tools
search_tool = TavilySearch(max_results=3)
tools = [search_tool, calculator]

# Create standard ReAct agent using deepagents framework
agent_executor = create_deep_agent(model=llm, tools=tools, system_prompt="You are a helpful AI assistant. Use the tools provided to solve the user's tasks. If you don't know the answer, use the search tool.")

async def run_baseline():
    input_path = "benchmarks/complex_tasks_real_api.json"
    output_path = "benchmarks/react_real_api_results.json"
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    tasks = data.get("tasks", [])[:3]
    results = []
    
    print(f"Starting ReAct baseline evaluation on {len(tasks)} tasks...")
    
    for i, task in enumerate(tasks):
        print(f"\n[{i+1}/{len(tasks)}] Running Task {task['task_id']}: {task['query'][:50]}...")
        start_time = time.time()
        
        try:
            # We want to capture the trajectory (tool calls) and the final response
            response = await agent_executor.ainvoke(
                {"messages": [("user", task["query"])]},
                config={"recursion_limit": 15}
            )
            
            messages = response.get("messages", [])
            
            # Extract trajectory
            trajectory = []
            final_answer = ""
            for msg in messages:
                if msg.type == "ai" and msg.tool_calls:
                    for tc in msg.tool_calls:
                        trajectory.append({
                            "tool": tc["name"],
                            "input": tc["args"]
                        })
                elif msg.type == "ai" and not msg.tool_calls:
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
        
    print(f"\nBaseline evaluation completed. Results saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(run_baseline())