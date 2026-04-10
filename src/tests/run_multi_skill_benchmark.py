import asyncio
import json
import os
import sys
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from src.agent import agent, multi_skill_orchestrator, list_skills

load_dotenv()

async def run_benchmark_task(task_name, prompt):
    print(f"\n" + "="*50)
    print(f"TASK: {task_name}")
    print(f"PROMPT: {prompt}")
    print("="*50)
    
    # Configuration 1: Standard Agent (letting it decide which tools to use)
    print("\n--- Configuration 1: Standard Agent (Self-Orchestration) ---")
    config = {"configurable": {"thread_id": f"std_{task_name}"}}
    try:
        res1 = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]}, config=config)
        print(f"Result 1: {res1['messages'][-1].content[:500]}...")
    except Exception as e:
        print(f"Error in Config 1: {str(e)}")

    # Configuration 2: FinAgent-Evo (Using Multi-Skill Orchestrator)
    print("\n--- Configuration 2: FinAgent-Evo (Explicit Multi-Skill Orchestration) ---")
    try:
        # We explicitly tell the agent to use the orchestrator for this hard task
        orchestration_prompt = f"Use the multi_skill_orchestrator tool to solve this complex task: {prompt}"
        res2 = await agent.ainvoke({"messages": [HumanMessage(content=orchestration_prompt)]}, config=config)
        print(f"Result 2: {res2['messages'][-1].content[:500]}...")
    except Exception as e:
        print(f"Error in Config 2: {str(e)}")

async def main():
    hard_tasks = [
        {
            "name": "NVIDIA Strategic Investment Analysis",
            "prompt": "Analyze NVIDIA (NVDA) for a 6-month investment horizon. You must fetch market data, perform technical analysis, check sentiment, and calculate a potential price target based on growth metrics. Provide a final decision: Buy, Hold, or Sell."
        },
        {
            "name": "Tech Sector Hedging Strategy",
            "prompt": "Given the current high interest rate environment and tech stock volatility, determine if a portfolio of Apple, Microsoft, and Tesla should be hedged with Put options. Use technical indicators and sentiment analysis for all three stocks to justify your decision. Final Answer: Yes/No with justification."
        }
    ]
    
    for task in hard_tasks:
        await run_benchmark_task(task["name"], task["prompt"])

if __name__ == "__main__":
    asyncio.run(main())
