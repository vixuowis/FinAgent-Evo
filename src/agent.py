import os
import json
import urllib.parse
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from loguru import logger
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import tool
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

# --- QVeris Shell Tools for Orchestration ---
@tool
async def qveris_discover(query: str) -> str:
    """
    Discover available remote tools in the QVeris marketplace based on a natural language query.
    Use this to find financial data APIs, technical indicators, or alternative data sources.
    """
    return "QVeris Discover called. (This tool will be intercepted by the Orchestrator for remote call)"

@tool
async def qveris_inspect(tool_ids: list) -> str:
    """
    Inspect specific remote tools in QVeris to see their parameters, description, and usage examples.
    """
    return "QVeris Inspect called. (This tool will be intercepted by the Orchestrator for remote call)"

@tool
async def qveris_call(tool_id: str, search_id: str, params: dict) -> str:
    """
    Execute a remote tool from QVeris with the provided parameters.
    Requires a tool_id and search_id from a previous discover call.
    """
    return "QVeris Call executed. (This tool will be intercepted by the Orchestrator for remote call)"
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
from src.core.lean_prompts import (
    LEAN_RESEARCH_WORKFLOW_INSTRUCTIONS,
    LEAN_EVOLUTION_INSTRUCTIONS
)

# Load environment variables
load_dotenv()

# --- Agent Creation ---

llm_provider = os.getenv("LLM_PROVIDER", "dashscope").strip().lower()

if llm_provider == "maas":
    maas_api_key = os.getenv("MAAS_API_KEY")
    maas_base_url = os.getenv("MAAS_BASE_URL", "https://api.modelarts-maas.com/openai/v1")
    model = ChatOpenAI(
        model=os.getenv("MAAS_MODEL", "glm-5.1"),
        api_key=maas_api_key,
        base_url=maas_base_url,
        timeout=600,
        max_retries=5,
        temperature=0.6,
    )
else:
    model = ChatOpenAI(
        model=os.getenv("DASHSCOPE_MODEL", "qwen3.6-plus"),
        api_key=os.getenv("DASHSCOPE_API_KEY", "dummy"),
        base_url=os.getenv("DASHSCOPE_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1"),
        timeout=600,
        max_retries=5,
        temperature=0.6,
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
    # 1. Check if it's a built-in tool first
    if skill_id == "python_interpreter":
        return python_interpreter.run(input)
    if skill_id == "tavily_search":
        return tavily_search.run(input)
    if skill_id == "qveris_discover":
        return await qveris_discover.ainvoke({"query": input})
    if skill_id == "qveris_inspect":
        return await qveris_inspect.ainvoke({"tool_ids": [input]})
    if skill_id == "qveris_call":
        # In this context, we assume the orchestrator passed a JSON string as input
        try:
            call_params = json.loads(input)
            return await qveris_call.ainvoke(call_params)
        except:
            return "Error: qveris_call requires a JSON string as input with 'tool_id', 'search_id', and 'params'."

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
async def meta_evolution_orchestrator(analysis_logs: str, performance_delta: float) -> str:
    """
    Orchestrate the co-evolution of analysis and evolution skill chains.
    - analysis_logs: Detailed execution trace of the analysis chain.
    - performance_delta: Change in Alpha/SR after the last iteration.
    """
    logger.info(f"Starting Meta-Evolutionary Reflection (Delta: {performance_delta:.4f})")
    
    evo_chain = []
    
    # 1. Self-Reflection Step
    reflection_task = f"Evaluate previous evolution effectiveness. Delta: {performance_delta}"
    evo_chain.append({"step": 1, "skill_id": "meta_reflection", "action": "Analyzing Delta"})
    
    # 2. Trigger mutation if needed
    if performance_delta < 0:
        feedback = "The previous evolution made the agent too conservative. Aggressiveness must be increased."
        res = await evolve_skill.ainvoke({
            "skill_id": "strategic_decision_making", 
            "feedback": feedback
        })
        evo_chain.append({"step": 2, "skill_id": "evolve_skill", "action": "Mutating Strategy", "result": res})
    else:
        evo_chain.append({"step": 2, "skill_id": "none", "action": "Maintain Strategy", "result": "Performance stable or positive."})

    # 3. Extract Experience
    exp_res = await extract_experience.ainvoke({
        "task": "Daily Trading Meta-Evolution",
        "outcome": f"Delta {performance_delta:.4f}",
        "importance": abs(performance_delta) * 10
    })
    evo_chain.append({"step": 3, "skill_id": "extract_experience", "action": "Archiving Lessons", "result": exp_res})

    # Format the chain for display
    chain_str = " -> ".join([f"{item['skill_id']}({item['action']})" for item in evo_chain])
    
    summary = f"""
    ## Evolution Skill Call Chain
    ⛓️ {chain_str}
    
    ### Details:
    - Delta: {performance_delta:.4f}
    - Status: {'Mutation Triggered' if performance_delta < 0 else 'Stability Maintained'}
    """
    return summary

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
    - **REMOTE TOOLS**: If internal tools/skills are insufficient, use 'qveris_discover' to find specialized remote tools for specific tasks.
    
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
            
            logger.info(f"Orchestrator: Step {step.get('step')} - {reasoning} (Using {skill_id})")
            
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
        chain_str = " -> ".join([f"{log['skill_id']}" for log in execution_logs])
        appendix = f"\n\n---\n## Execution Skill Call Chain\n⛓️ {chain_str}\n\n### 🛠 Execution Logs\n"
        for log in execution_logs:
            appendix += f"- **Step {log['step']} ({log['skill_id']})**: {log['input'][:100]}...\n"
            
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
    # Built-in Tools
    info.append("- python_interpreter (TOOL): Execute code for calculations. [Built-in]")
    info.append("- tavily_search (TOOL): Search for real-time news and data. [Built-in]")
    
    # Library Skills
    for s in skills:
        info.append(f"- {s.genotype.skill_id} ({s.genotype.category}): {s.genotype.prompt_chromosome[:100]}... [Fitness: {s.genotype.fitness_score:.2f}]")
    
    return "Available Skills and Tools:\n" + "\n".join(info)

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
        prompt_chromosome="""You are a quantitative technical analyst. 
        Analyze the provided price and volume data.
        1. Calculate SMA-5 (5-day Simple Moving Average) and compare it to the current price.
        2. Calculate RSI-5 (5-day Relative Strength Index).
        3. Identify trend strength: Strong Bullish, Bullish, Neutral, Bearish, Strong Bearish.
        4. Provide clear Support and Resistance levels based on recent price action.
        """,
        tool_deps=["fetch_market_data"],
        input_schema={"price_history": "list", "volume_history": "list"},
        output_schema={"sma_5": "number", "rsi_5": "number", "trend": "string", "levels": "dict"}
    )
    skill_library.add_skill(Skill(tech_analysis_genotype))

    python_genotype = SkillGenotype(
        skill_id="python_interpreter",
        category=SkillCategory.EXECUTION,
        llm_config={"model_tier": ModelTier.STANDARD, "temperature": 0.0, "max_tokens": 1000},
        prompt_chromosome="""You are a Python Interpreter. Execute the provided code and return the output. 
        Use this for complex calculations or data transformations that the LLM cannot do reliably.
        Output ONLY the result of the code execution.
        """,
        tool_deps=[],
        input_schema={"code": "string"},
        output_schema={"output": "string"}
    )
    skill_library.add_skill(Skill(python_genotype))
    decision_making_genotype = SkillGenotype(
        skill_id="strategic_decision_making",
        category=SkillCategory.ANALYSIS,
        llm_config={"model_tier": ModelTier.HEAVY, "temperature": 0.0, "max_tokens": 2000},
        prompt_chromosome="""You are an Expert Alpha-Seeking Quant Trader. Your goal is to MAXIMIZE Alpha while maintaining a high Sharpe Ratio.
        
        ### STRATEGY CORE:
        1. **Trend is Friend**: If price is above SMA-5 and RSI-5 < 70, MAINTAIN 100% exposure. Only sell if trend breaks.
        2. **Volatility Scaling**: In high volatility, scale exposure to 50-70% if unsure, but stay at 100% if the trend is strong.
        3. **Sentiment as Lead**: If News Sentiment is strongly positive (>0.7), anticipate a breakout and increase exposure BEFORE it happens.
        4. **Drawdown Protection**: If price drops >3% from recent peak AND RSI < 30, it might be a crash. Exit immediately (0% exposure).
        
        ### ANALYSIS PILLARS:
        - **Momentum & Trend**: Analyze SMA distance and RSI slope.
        - **Sentiment Divergence**: Is news positive while price is flat? (Bullish divergence).
        - **Volume Confirmation**: (If available) Use volume to confirm trend strength.
        
        ### OUTPUT FORMAT (MANDATORY):
        - Reasoning: <analysis_of_trend_and_sentiment>
        - Target Exposure: <X>% (0-100)
        - Final Recommendation: <BUY/SELL/HOLD>
        """,
        tool_deps=["technical_analysis", "analyze_sentiment"],
        input_schema={"context": "string", "analysis_results": "string"},
        output_schema={"reasoning": "string", "target_exposure": "number", "recommendation": "string"}
    )
    skill_library.add_skill(Skill(decision_making_genotype))

    # --- QVeris Skills ---
    qveris_genotype = SkillGenotype(
        skill_id="qveris_remote_execution",
        category=SkillCategory.EXECUTION,
        llm_config={"model_tier": ModelTier.STANDARD, "temperature": 0.1, "max_tokens": 1000},
        prompt_chromosome="""You are a QVeris Bridge. You can discover, inspect, and call remote financial tools.
        1. Use 'qveris_discover' to find new tools for a query.
        2. Use 'qveris_inspect' to understand how to use a tool.
        3. Use 'qveris_call' to execute the tool.
        
        Always provide the tool_id and search_id for execution.
        """,
        tool_deps=[],
        input_schema={"query": "string", "tool_id": "string", "params": "dict"},
        output_schema={"result": "string"}
    )
    skill_library.add_skill(Skill(qveris_genotype))

register_initial_skills()

# Convert library skills to tools
skill_tools = [s.to_tool(model=model) for s in skill_library.get_all_skills()]

system_prompt = "\n".join([
    LEAN_RESEARCH_WORKFLOW_INSTRUCTIONS,
    LEAN_EVOLUTION_INSTRUCTIONS
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
        meta_evolution_orchestrator,
        multi_skill_orchestrator,
        list_skills,
        list_memory_rules,
        optimize_skill_topology,
        qveris_discover,
        qveris_inspect,
        qveris_call,
        *skill_tools
    ],
    system_prompt=system_prompt,
)
