import asyncio
import os
import sys
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from src.agent import agent, list_skills, evolve_skill, invoke_skill

load_dotenv()

async def test_evolution_flow():
    print("--- Starting Link Evolution Test ---\n")
    
    config = {"configurable": {"thread_id": "test_thread_evolution"}}
    
    # Step 1: List current skills
    print("Step 1: Listing initial skills...")
    initial_skills = list_skills.invoke({})
    print(initial_skills)
    print("-" * 50)
    
    # Step 2: Simulate a user task and provide feedback
    print("Step 2: Simulating task and feedback...")
    task_input = "Analyze Bitcoin price trend for next 24 hours."
    feedback = "The technical_analysis skill is too basic. It only looks at RSI. It needs to include Volume Divergence and Bollinger Bands for better accuracy in volatile markets like BTC."
    
    # Step 3: Trigger evolution
    print(f"Step 3: Evolving 'technical_analysis' with feedback: '{feedback}'...")
    evolution_result = await evolve_skill.ainvoke({"skill_id": "technical_analysis", "feedback": feedback})
    print(evolution_result)
    print("-" * 50)
    
    # Step 4: List skills again to see the new mutation
    print("Step 4: Listing updated skills...")
    updated_skills = list_skills.invoke({})
    print(updated_skills)
    print("-" * 50)
    
    # Step 5: Find the new skill ID and use it
    import re
    match = re.search(r"evolved into (technical_analysis_mutated_\d+)", evolution_result)
    if match:
        new_skill_id = match.group(1)
        print(f"Step 5: Invoking the new skill '{new_skill_id}'...")
        result = await invoke_skill.ainvoke({"skill_id": new_skill_id, "input": "BTC/USDT 1h chart"})
        print(result)
    else:
        print("Failed to extract new skill ID from evolution result.")

if __name__ == "__main__":
    asyncio.run(test_evolution_flow())
