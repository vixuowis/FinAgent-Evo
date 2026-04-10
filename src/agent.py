import os
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import tool
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

from src.core.types import SkillGenotype, SkillCategory, ModelTier, Experience
from src.core.skill import Skill, SkillLibrary
from src.core.memory import HierarchicalMemory
from src.core.evolution import EvolutionEngine
from src.core.prompts import (
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
    REPRODUCIBILITY_INSTRUCTIONS,
    EVOLUTION_INSTRUCTIONS
)

# Load environment variables
load_dotenv()

# --- Agent Creation ---

model = ChatOpenAI(
    model="glm-5",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://coding.dashscope.aliyuncs.com/v1",
    timeout=600,  # Increase timeout to 10 minutes for deep research
    max_retries=5, # Increase retries for unstable network
)

# --- Initialize Core Components ---
skill_library = SkillLibrary()
memory = HierarchicalMemory(meta_model=model)
evolution_engine = EvolutionEngine(meta_model=model)

# --- Specialized Tools ---

@tool
def tavily_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for real-time information using Tavily.
    """
    search = TavilySearch(max_results=max_results)
    results = search.run(query)
    return str(results)

@tool
def think_tool(reflection: str) -> str:
    """
    A strategic reflection mechanism to pause and assess progress, analyze findings, 
    identify gaps, and plan next steps.
    """
    return f"Reflection recorded: {reflection}"

@tool
def python_interpreter(code: str) -> str:
    """
    A Python REPL to execute code for complex calculations, data analysis, or simulations.
    Use this for any mathematical modeling, precision rounding, or multi-step numerical problems.
    Input should be valid Python code. The tool returns the stdout of the execution.
    """
    try:
        repl = PythonREPL()
        return repl.run(code)
    except Exception as e:
        return f"Error executing code: {str(e)}"

@tool
async def extract_experience(task: str, outcome: str, importance: float):
    """
    Store task outcomes and lessons in the agent's memory system.
    """
    await memory.write(Experience(
        id=f"exp_{int(datetime.now().timestamp())}",
        task=task,
        context={},
        outcome=outcome,
        lessons=["Auto-extracted lesson based on task success."],
        importance=importance,
    ))
    return "Experience successfully extracted and stored in Hierarchical Memory."

@tool
async def evolve_skill(skill_id: str, feedback: str) -> str:
    """
    Explicitly trigger the evolution of a specific skill based on performance feedback.
    This will mutate the skill's prompt chromosome using the evolution engine.
    """
    skill = skill_library.get_skill(skill_id)
    if not skill:
        return f"Skill {skill_id} not found."
    
    mutated_genotype = await evolution_engine.mutate(skill.genotype, feedback)
    new_skill = Skill(mutated_genotype)
    skill_library.add_skill(new_skill)
    
    # Also update the fitness score of the original skill based on negative feedback
    skill.update_fitness(0.1) 
    
    return f"Skill {skill_id} evolved into {mutated_genotype.skill_id}. New Prompt: {mutated_genotype.prompt_chromosome[:100]}... Use 'invoke_skill' with the new ID to test it."

@tool
async def invoke_skill(skill_id: str, input: str, params: Optional[Dict[str, Any]] = None) -> str:
    """
    Invokes a specialized skill from the library by its ID.
    Use this to execute evolved skills or any specialized analysis logic.
    """
    skill = skill_library.get_skill(skill_id)
    if not skill:
        return f"Skill {skill_id} not found in the library."
    
    # In a real implementation, this would call another LLM chain using the prompt_chromosome
    # For this demo, we simulate the execution and show the evolution effect
    return f"[Skill {skill_id} Execution Result]\nInput: {input}\nPrompt Context: {skill.genotype.prompt_chromosome}\nResult: Simulated high-quality financial analysis based on the mutated prompt."

@tool
def list_skills() -> str:
    """
    List all available skills in the library with their descriptions and current fitness scores.
    """
    skills = skill_library.get_all_skills()
    info = []
    for s in skills:
        info.append(f"- {s.genotype.skill_id} ({s.genotype.category}): {s.genotype.prompt_chromosome[:50]}... [Fitness: {s.genotype.fitness_score:.2f}]")
    return "Available Skills:\n" + "\n".join(info)

@tool
def list_memory_rules() -> str:
    """
    List all abstracted procedural rules and guidelines stored in the agent's hierarchical memory.
    These rules are extracted from past experiences to guide future tasks.
    """
    rules = memory.get_procedural_rules()
    if not rules:
        return "No procedural rules abstracted yet. Need more episodic experiences."
    
    info = []
    for r in rules:
        info.append(f"- [Rule {r.id}]: {r.content}")
    return "Abstracted Procedural Memory (Rules):\n" + "\n".join(info)

@tool
def optimize_skill_topology(current_task: str) -> str:
    """
    Evolve and optimize the agent's skill library for the current task.
    """
    all_skills = [s.genotype for s in skill_library.get_all_skills()]
    optimized = evolution_engine.select(all_skills, 5)
    return f"Skill Topology Optimized for task: {current_task}. Active skills: {', '.join([s.skill_id for s in optimized])}."

# --- Register Initial Skills ---

def register_initial_skills():
    market_data_genotype = SkillGenotype(
        skill_id="fetch_market_data",
        category=SkillCategory.DATA,
        llm_config={"model_tier": ModelTier.STANDARD, "temperature": 0.1, "max_tokens": 500},
        prompt_chromosome="You are a specialized financial data fetcher. Retrieve historical and real-time price data, volume, and volatility metrics for the requested asset.",
        tool_deps=[],
        input_schema={"asset": "string", "timeframe": "string"},
        output_schema={"data": "string"}
    )
    skill_library.add_skill(Skill(market_data_genotype))

    sentiment_genotype = SkillGenotype(
        skill_id="analyze_sentiment",
        category=SkillCategory.ANALYSIS,
        llm_config={"model_tier": ModelTier.HEAVY, "temperature": 0.3, "max_tokens": 1500},
        prompt_chromosome="You are an expert financial sentiment analyst. Evaluate news headlines, social media trends, and analyst reports.",
        tool_deps=["fetch_market_data"],
        input_schema={"query": "string"},
        output_schema={"sentiment": "string", "score": "number", "drivers": "list"}
    )
    skill_library.add_skill(Skill(sentiment_genotype))

    tech_analysis_genotype = SkillGenotype(
        skill_id="technical_analysis",
        category=SkillCategory.ANALYSIS,
        llm_config={"model_tier": ModelTier.STANDARD, "temperature": 0.1, "max_tokens": 1000},
        prompt_chromosome="You are a quantitative technical analyst. Use price and volume data to identify key support/resistance levels and trend indicators (RSI, MACD).",
        tool_deps=["fetch_market_data"],
        input_schema={"asset": "string", "data": "string"},
        output_schema={"signal": "string", "levels": "dict"}
    )
    skill_library.add_skill(Skill(tech_analysis_genotype))

register_initial_skills()

# Convert library skills to tools
skill_tools = [s.to_tool() for s in skill_library.get_all_skills()]

system_prompt = "\n".join([
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
    REPRODUCIBILITY_INSTRUCTIONS,
    EVOLUTION_INSTRUCTIONS
])

# Create the deep agent
agent = create_deep_agent(
    model=model,
    tools=[
        tavily_search,
        think_tool,
        python_interpreter,
        extract_experience,
        evolve_skill,
        invoke_skill,
        list_skills,
        list_memory_rules,
        optimize_skill_topology,
        *skill_tools
    ],
    system_prompt=system_prompt,
)
