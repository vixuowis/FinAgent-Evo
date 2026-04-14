import os
import json
import urllib.parse
import requests
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

QVERIS_API_KEY = os.getenv("QVERIS_API_KEY")
QVERIS_BASE_URL = "https://qveris.ai/api/v1"

def execute_qveris_tool(tool_id: str, parameters: Dict[str, Any]) -> str:
    url = f"{QVERIS_BASE_URL}/tools/execute?tool_id={urllib.parse.quote(tool_id)}"
    headers = {
        "Authorization": f"Bearer {QVERIS_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"parameters": parameters, "max_response_size": 20480}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("success"):
                data = res_json.get("result", {}).get("data", res_json.get("result", {}))
                return json.dumps(data, ensure_ascii=False)[:2000]
            else:
                return f"QVeris Execution failed: {res_json.get('error_message')}"
        return f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return f"Request failed: {str(e)}"

# --- Specialized QVeris Tools ---

@tool
def get_stock_price(symbol: str) -> str:
    """Get real-time stock price and basic quote for a specific ticker symbol (e.g., 'AAPL')."""
    return execute_qveris_tool("finnhub_io_api.stock.quote", {"symbol": symbol})

@tool
def get_financial_statements(symbol: str) -> str:
    """Get the latest annual income statement data for a specific ticker symbol (e.g., 'AAPL')."""
    return execute_qveris_tool("financialmodelingprep.stable.incomestatement.retrieve.v1.dd6d583f", {"symbol": symbol})

@tool
def get_exchange_rate(pair: str) -> str:
    """Get real-time forex exchange rate for a specific currency pair (e.g., 'EUR/USD')."""
    return execute_qveris_tool("twelvedata.exchangerate.retrieve.v1.9eeb3b0d", {"symbol": pair})

@tool
def get_macro_data(indicator: str) -> str:
    """Get US macroeconomic data. Valid indicators: 'CPI', 'FEDERAL_FUNDS_RATE', 'TREASURY_YIELD_10Y'."""
    indicator = indicator.upper()
    if indicator == "CPI":
        return execute_qveris_tool("alphavantage.economic.cpi.retrieve.v1.7aca3c4a", {"interval": "monthly"})
    elif indicator == "FEDERAL_FUNDS_RATE":
        return execute_qveris_tool("alphavantage.economic.federal_funds_rate.retrieve.v1.7aca3c4a", {"interval": "daily"})
    elif indicator == "TREASURY_YIELD_10Y":
        return execute_qveris_tool("alphavantage.economic.treasury_yield.retrieve.v1.7aca3c4a", {"interval": "daily", "maturity": "10year"})
    return "Unsupported indicator. Use CPI, FEDERAL_FUNDS_RATE, or TREASURY_YIELD_10Y."

@tool
def get_crypto_price(symbol: str) -> str:
    """Get real-time cryptocurrency price in USD (e.g., 'BTC', 'ETH')."""
    return execute_qveris_tool("twelvedata.exchangerate.retrieve.v1.9eeb3b0d", {"symbol": f"{symbol}/USD"})

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
    This will execute the skill's specific analysis logic using the LLM.
    """
    # Direct mappings for QVeris tools to bypass LLM overhead
    qveris_map = {
        "get_stock_price": get_stock_price,
        "get_financial_statements": get_financial_statements,
        "get_exchange_rate": get_exchange_rate,
        "get_macro_data": get_macro_data,
        "get_crypto_price": get_crypto_price
    }
    
    if skill_id in qveris_map:
        # Extract the core parameter from input string if LLM passed it weirdly
        import re
        # Simple heuristic to extract symbol/indicator
        param_val = input.split(":")[-1].strip() if ":" in input else input.strip()
        # For safety, if params are passed correctly, use them
        if params and len(params) > 0:
            param_val = list(params.values())[0]
        else:
            # try to find uppercase letters
            words = re.findall(r'[A-Z/_]+', input)
            if words:
                param_val = words[0]
                
        try:
            res = qveris_map[skill_id].invoke(param_val)
            return f"[QVeris Tool {skill_id} Executed]\n{res}"
        except Exception as e:
            return f"Error executing QVeris tool {skill_id}: {str(e)}"
            
    skill = skill_library.get_skill(skill_id)
    if not skill:
        return f"Skill {skill_id} not found in the library."
    
    # Execute the skill using the meta_model and the prompt_chromosome
    from langchain_core.messages import SystemMessage, HumanMessage
    
    system_msg = SystemMessage(content=skill.genotype.prompt_chromosome)
    user_content = f"Input: {input}"
    if params:
        user_content += f"\nParameters: {json.dumps(params)}"
        
    try:
        response = await model.ainvoke([system_msg, HumanMessage(content=user_content)])
        return f"[Skill {skill_id} Execution Result]\n{response.content}"
    except Exception as e:
        return f"Error executing skill {skill_id}: {str(e)}"

@tool
async def multi_skill_orchestrator(complex_task: str) -> str:
    """
    A high-level orchestrator that plans and executes a sequence of skills to solve a hard task.
    It uses procedural memory (Rules of Thumb) to guide the planning process.
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    
    # 1. Get all available skills and their dependencies
    skills = skill_library.get_all_skills()
    skills_info = []
    for s in skills:
        deps = f" (Depends on: {', '.join(s.genotype.tool_deps)})" if s.genotype.tool_deps else ""
        skills_info.append(f"- {s.genotype.skill_id}: {s.genotype.prompt_chromosome[:200]}...{deps}")
        
    # Add built-in data fetching tools
    built_in_tools = [
        "- get_stock_price: Get real-time stock price (e.g. 'AAPL')",
        "- get_financial_statements: Get latest annual income statement data",
        "- get_exchange_rate: Get forex exchange rate (e.g. 'EUR/USD')",
        "- get_macro_data: Get US macroeconomic data (CPI, FEDERAL_FUNDS_RATE, TREASURY_YIELD_10Y)",
        "- get_crypto_price: Get real-time cryptocurrency price (e.g. 'BTC')"
    ]
    skills_info.extend(built_in_tools)
    skills_str = "\n".join(skills_info)
    
    # 2. Get procedural memory (Rules of Thumb)
    rules = memory.get_procedural_rules()
    rules_str = "\n".join([f"- {r.content}" for r in rules]) if rules else "No specific rules yet."
    
    # 3. Ask the model to create a strategic plan
    plan_prompt = f"""
    You are the Strategic Orchestration Engine for FinAgent-Evo.
    Your goal is to solve the complex financial task below by orchestrating specialized skills.
    
    ### Task:
    {complex_task}
    
    ### Available Skills:
    {skills_str}
    
    ### Procedural Memory (Best Practices):
    {rules_str}
    
    ### MANDATORY EXECUTION RULES:
    - **NO SIMULATION**: You MUST actually call the skills. Do not just describe what you would do.
    - **DATA VERIFICATION**: Every claim must be backed by the output of a skill (e.g., fetch_market_data for prices).
    - **PYTHON FOR MATH**: Use 'python_interpreter' for ANY calculation (drawdown, correlation, etc.). Do not do math in your head.
    - **DEPENDENCY ORDER**: Order skills logically (e.g., fetch data before analysis).
    - **SYNTHESIS RIGOR**: The final step MUST use 'strategic_decision_making' to unify all findings.
    
    Output your plan as a JSON list of steps. 
    Format: [{"step": 1, "skill_id": "...", "reasoning": "...", "input": "...", "params": {"symbol": "AAPL"}}]
    """
    
    try:
        plan_response = await model.ainvoke([
            SystemMessage(content="You are an expert financial strategist and orchestration engine. You NEVER simulate tool calls; you ALWAYS execute them."), 
            HumanMessage(content=plan_prompt)
        ])
        
        import re
        json_match = re.search(r"\[.*\]", plan_response.content, re.DOTALL)
        if not json_match:
            return f"Failed to generate a structured plan. Response: {plan_response.content}"
            
        plan = json.loads(json_match.group(0))
        
        # 4. Execute the plan with strict context passing and output logging
        results = []
        context_accumulator = ""
        execution_logs = []
        for step in plan:
            skill_id = step.get("skill_id")
            step_input = step.get("input")
            reasoning = step.get("reasoning", "")
            params = step.get("params", None)
            
            print(f"Orchestrator: Step {step.get('step')} - {reasoning} (Using {skill_id})")
            
            # Enrich input with previous context
            enriched_input = f"Task: {step_input}\nPrevious Context: {context_accumulator[:2000]}"
            
            # Execute skill
            res = await invoke_skill.ainvoke({"skill_id": skill_id, "input": enriched_input, "params": params})
            
            # Record result with metadata
            step_record = f"--- STEP {step.get('step')} ({skill_id}) ---\nReasoning: {reasoning}\nOutput: {res}"
            results.append(step_record)
            execution_logs.append({
                "step": step.get("step"),
                "skill_id": skill_id,
                "input": step_input,
                "output": res
            })
            
            # Update context for next steps
            context_accumulator += f"\n[Result from Step {step.get('step')} ({skill_id})]: {res[:1000]}"
            
        # 5. Final Synthesis with Self-Correction
        logs_str = "\n\n".join(results)
        synthesis_prompt = f"""
        You are the Senior Financial Analyst for FinAgent-Evo.
        Task: {complex_task}
        
        Detailed Execution Logs (VERIFIED):
        {logs_str}
        
        ### Final Instructions:
        1. Review all execution logs above. 
        2. Ensure every required skill was used correctly.
        3. Identify any contradictions (e.g., technicals vs sentiment).
        4. Synthesize a high-conviction final answer. Include actual data points from the logs.
        5. If 'python_interpreter' was used, YOU MUST SHOW THE PYTHON CODE AND THE OUTPUT in your response.
        """
        final_res = await model.ainvoke([
            SystemMessage(content="You are a senior financial analyst providing a final recommendation based on verified execution logs. You provide PROOF of work."), 
            HumanMessage(content=synthesis_prompt)
        ])
        
        # Append Appendix for transparency
        appendix = "\n\n---\n### 🛠 Execution Appendix (Transparency Logs)\n"
        for log in execution_logs:
            appendix += f"- **Step {log['step']} ({log['skill_id']})**: Executed with input '{log['input'][:50]}...'\n"
            
        return final_res.content + appendix
        
    except Exception as e:
        return f"Error during orchestration: {str(e)}"

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

    decision_making_genotype = SkillGenotype(
        skill_id="strategic_decision_making",
        category=SkillCategory.ANALYSIS,
        llm_config={"model_tier": ModelTier.HEAVY, "temperature": 0.0, "max_tokens": 2000},
        prompt_chromosome="""You are a Senior Investment Committee Member. Your role is to synthesize multi-dimensional data (technical, fundamental, sentiment, macro) to provide high-conviction investment decisions.
        1. Evaluate risk-reward ratios.
        2. Consider downside protection.
        3. Align with specific investment horizons (e.g., 6 months).
        4. Output a clear BUY/HOLD/SELL recommendation with a target price and stop-loss.""",
        tool_deps=["technical_analysis", "analyze_sentiment"],
        input_schema={"context": "string", "analysis_results": "string"},
        output_schema={"recommendation": "string", "target_price": "number", "stop_loss": "number"}
    )
    skill_library.add_skill(Skill(decision_making_genotype))

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
        get_stock_price,
        get_financial_statements,
        get_exchange_rate,
        get_macro_data,
        get_crypto_price,
        think_tool,
        python_interpreter,
        extract_experience,
        evolve_skill,
        invoke_skill,
        multi_skill_orchestrator,
        list_skills,
        list_memory_rules,
        optimize_skill_topology,
        *skill_tools
    ],
    system_prompt=system_prompt,
)
