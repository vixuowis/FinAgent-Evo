import asyncio
import os
import sys
from dotenv import load_dotenv
from src.agent import extract_experience, list_memory_rules

load_dotenv()

async def test_memory_flow():
    print("--- Starting Hierarchical Memory Abstraction Test ---\n")
    
    # Step 1: Initial rules (should be empty)
    print("Step 1: Listing initial procedural rules...")
    initial_rules = list_memory_rules.invoke({})
    print(initial_rules)
    print("-" * 50)
    
    # Step 2: Extract 5 high-importance experiences
    print("Step 2: Extracting 5 high-importance episodic experiences...")
    experiences = [
        {"task": "Analyze Nvidia earnings", "outcome": "Successful prediction of price movement based on H100 demand.", "importance": 0.9},
        {"task": "Evaluate Bitcoin volatility", "outcome": "Avoided false breakout signals by using Volume Divergence.", "importance": 0.85},
        {"task": "Competitor analysis for Apple", "outcome": "Identified supply chain risk that was missed by other analysts.", "importance": 0.95},
        {"task": "Market sentiment analysis for Tesla", "outcome": "Detected shift in sentiment early by tracking social media trends.", "importance": 0.8},
        {"task": "Portfolio optimization for tech stocks", "outcome": "Improved Sharpe ratio by 0.2 using better correlation modeling.", "importance": 0.9}
    ]
    
    for exp in experiences:
        print(f"Adding experience for: '{exp['task']}'...")
        await extract_experience.ainvoke(exp)
        
    print("-" * 50)
    
    # Step 3: Check procedural rules again (should be abstracted now)
    print("Step 3: Listing abstracted procedural memory (Rules)...")
    final_rules = list_memory_rules.invoke({})
    print(final_rules)

if __name__ == "__main__":
    asyncio.run(test_memory_flow())
