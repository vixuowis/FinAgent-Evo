import os
import json
import urllib.parse
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from loguru import logger
import httpx
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
try:
    # deepagents 仅用于 ReAct baseline；在纯 Full/Orchestration 路径中不应成为硬依赖
    from deepagents import create_deep_agent  # type: ignore
except Exception:  # pragma: no cover
    create_deep_agent = None  # type: ignore
from langgraph.checkpoint.memory import MemorySaver

from src.core.qveris_cache import get_qveris_cache

# --- QVeris Shell Tools for Orchestration ---
@tool
async def qveris_discover(query: str) -> str:
    """
    Discover available remote tools in the QVeris marketplace based on a natural language query.
    Use this to find financial data APIs, technical indicators, or alternative data sources.
    ID: qveris:discover
    """
    return "QVeris Discover called. (This tool will be intercepted by the Orchestrator for remote call)"

@tool
async def qveris_inspect(tool_ids: list) -> str:
    """
    Inspect specific remote tools in QVeris to see their parameters, description, and usage examples.
    ID: qveris:inspect
    """
    return "QVeris Inspect called. (This tool will be intercepted by the Orchestrator for remote call)"

@tool
async def qveris_call(tool_id: str, search_id: str, params: dict) -> str:
    """
    Execute a remote tool from QVeris with the provided parameters.
    Requires a tool_id and search_id from a previous discover call.
    ID: qveris:call
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
disable_evolution = os.getenv("FINAGENT_DISABLE_EVOLUTION", "").strip() in {"1", "true", "True", "yes", "YES"}
disable_memory = os.getenv("FINAGENT_DISABLE_MEMORY", "").strip() in {"1", "true", "True", "yes", "YES"}
disable_orchestration = os.getenv("FINAGENT_DISABLE_ORCHESTRATION", "").strip() in {"1", "true", "True", "yes", "YES"}
is_plan_only = os.getenv("FINAGENT_PLAN_ONLY", "").strip() in {"1", "true", "True", "yes", "YES"}
is_fault_injection = os.getenv("FINAGENT_FAULT_INJECTION", "").strip() in {"1", "true", "True", "yes", "YES"}
llm_timeout_s = int(os.getenv("LLM_TIMEOUT_SECONDS", "600").strip() or "600")
llm_max_retries = int(os.getenv("LLM_MAX_RETRIES", "5").strip() or "5")

if llm_provider == "maas":
    maas_api_key = os.getenv("MAAS_API_KEY")
    maas_base_url = os.getenv("MAAS_BASE_URL", "https://api.modelarts-maas.com/openai/v1")
    model = ChatOpenAI(
        model=os.getenv("MAAS_MODEL", "glm-5.1"),
        api_key=maas_api_key,
        base_url=maas_base_url,
        timeout=llm_timeout_s,
        max_retries=llm_max_retries,
        temperature=0.6,
    )
elif llm_provider == "openai":
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        api_key=openai_api_key,
        base_url=openai_base_url,
        timeout=llm_timeout_s,
        max_retries=llm_max_retries,
        temperature=0.6,
    )
else:
    model = ChatOpenAI(
        model=os.getenv("DASHSCOPE_MODEL", "qwen3.6-plus"),
        api_key=os.getenv("DASHSCOPE_API_KEY", "dummy"),
        base_url=os.getenv("DASHSCOPE_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1"),
        timeout=llm_timeout_s,
        max_retries=llm_max_retries,
        temperature=0.6,
    )

# --- Initialize Core Components ---
skill_library = SkillLibrary()
memory = HierarchicalMemory(meta_model=model, enabled=not disable_memory)
evolution_engine = EvolutionEngine(meta_model=model)

QVERIS_API_KEY = os.getenv("QVERIS_API_KEY")
QVERIS_BASE_URL = "https://qveris.ai/api/v1"

def maybe_inject_fault(tool_id: str) -> Optional[str]:
    """Randomly injects tool failures if FINAGENT_FAULT_INJECTION is enabled."""
    if not is_fault_injection:
        return None
    
    import random
    # Inject faults with a certain probability (e.g., 15%)
    if random.random() < 0.15:
        faults = [
            f"Error: Tool '{tool_id}' timed out after 20.0s (Fault Injection).",
            f"Error: Rate limit exceeded for '{tool_id}'. Please retry after 60s (Fault Injection).",
            f"Error: Invalid tool output for '{tool_id}'. Expected JSON, got truncated data (Fault Injection).",
            f"Error: Internal server error (500) during execution of '{tool_id}' (Fault Injection)."
        ]
        chosen = random.choice(faults)
        logger.warning(f"FAULT INJECTED for tool '{tool_id}': {chosen}")
        return chosen
    return None

def execute_qveris_tool(tool_id: str, parameters: Dict[str, Any]) -> str:
    fault = maybe_inject_fault(tool_id)
    if fault:
        return fault
        
    cache = get_qveris_cache()
    cached, hit = cache.get(tool_id, parameters)
    if hit and cached is not None:
        return cached

    if not QVERIS_API_KEY:
        return "QVeris API key missing."

    url = f"{QVERIS_BASE_URL}/tools/execute?tool_id={urllib.parse.quote(tool_id)}"
    headers = {
        "Authorization": f"Bearer {QVERIS_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"parameters": parameters, "max_response_size": 20480}
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("success"):
                data = res_json.get("result", {}).get("data", res_json.get("result", {}))
                out = json.dumps(data, ensure_ascii=False)[:2000]
                cache.set(tool_id, parameters, out)
                return out
            else:
                return f"QVeris Execution failed: {res_json.get('error_message')}"
        return f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return f"Request failed: {str(e)}"

@tool
def get_historical_data(symbol: str, period: str = "30d") -> str:
    """
    Get historical OHLCV price data for a stock or cryptocurrency.
    period can be '7d', '30d', '90d', '1y'.
    """
    # Map symbols to QVeris expected formats if needed
    # For simplicity, we use the FMP tool for stocks and AlphaVantage for crypto
    if "/" in symbol or "-" in symbol or any(c.islower() for c in symbol):
        # Likely crypto
        clean_symbol = symbol.replace("-USD", "").replace("/USD", "").upper()
        return execute_qveris_tool("alphavantage.digital_currency_daily.retrieve.v1.7aca3c4a", {"symbol": clean_symbol, "market": "USD", "function": "DIGITAL_CURRENCY_DAILY"})
    else:
        return execute_qveris_tool("financialmodelingprep.historical_price_eod.non_split_adjusted.retrieve.v1.4c43e8ed", {"symbol": symbol})

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
def get_macro_data(indicator: str, country: str = "US") -> str:
    """
    Get macroeconomic data. 
    Supported indicators: 'CPI', 'FEDERAL_FUNDS_RATE', 'TREASURY_YIELD_10Y', 'INTEREST_RATE'.
    Countries supported for 'INTEREST_RATE': US, Japan, Australia, UK, Eurozone.
    """
    indicator = indicator.upper()
    country = country.upper()
    
    if country == "US":
        if indicator == "CPI":
            return execute_qveris_tool("alphavantage.economic.cpi.retrieve.v1.7aca3c4a", {"interval": "monthly"})
        elif indicator == "FEDERAL_FUNDS_RATE" or indicator == "INTEREST_RATE":
            return execute_qveris_tool("alphavantage.economic.federal_funds_rate.retrieve.v1.7aca3c4a", {"interval": "daily"})
        elif indicator == "TREASURY_YIELD_10Y":
            return execute_qveris_tool("alphavantage.economic.treasury_yield.retrieve.v1.7aca3c4a", {"interval": "daily", "maturity": "10year"})
    
    # Fallback to web search for non-US or other indicators
    query = f"current {country} {indicator}"
    return tavily_search.run(query)

@tool
def get_crypto_price(symbol: str) -> str:
    """Get real-time cryptocurrency price in USD (e.g., 'BTC', 'ETH')."""
    return execute_qveris_tool("twelvedata.exchangerate.retrieve.v1.9eeb3b0d", {"symbol": f"{symbol}/USD"})
# --- Specialized Tools ---

@tool
def tavily_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for general real-time information.
    LOWER PRIORITY: Only use this if specialized QVeris tools (like search_financial_news) are insufficient.
    """
    fault = maybe_inject_fault("tavily_search")
    if fault:
        return fault
        
    search = TavilySearch(max_results=max_results)
    try:
        results = search.run(query)
        # Check if the result is an error dict (some versions of TavilySearch return errors as strings or dicts)
        if isinstance(results, dict) and "error" in results:
            error_msg = str(results["error"])
            if "432" in error_msg or "limit" in error_msg.lower():
                logger.warning(f"Tavily quota exceeded (432). Falling back to QVeris Search...")
                # Fallback to QVeris Web Search if available
                return execute_qveris_tool("brave_search.web.search.retrieve.v1.f02ed09d", {"q": query})
        elif isinstance(results, str) and ("432" in results or "usage limit" in results.lower()):
            logger.warning(f"Tavily quota exceeded (432) detected in string output. Falling back to QVeris Search...")
            return execute_qveris_tool("brave_search.web.search.retrieve.v1.f02ed09d", {"q": query})
            
        return str(results)
    except Exception as e:
        error_msg = str(e)
        if "432" in error_msg or "limit" in error_msg.lower():
            logger.warning(f"Tavily Search failed with quota error. Falling back to QVeris Search...")
            return execute_qveris_tool("brave_search.web.search.retrieve.v1.f02ed09d", {"q": query})
        return f"Error executing tavily_search: {error_msg}"

@tool
def search_financial_news(query: str, max_results: int = 5) -> str:
    """
    Search recent financial news for an entity/topic.
    HIGH PRIORITY: Always use this tool for financial news instead of general web search.
    """
    # Try QVeris (Brave Search) first as prioritized news source
    qveris_query = f"{query} financial news"
    res = execute_qveris_tool("brave_search.web.search.retrieve.v1.f02ed09d", {"q": qveris_query})
    
    # Check if the result is valid and not just an error message
    if res and "Error" not in res and "failed" not in res.lower() and len(res) > 50:
        return f"[QVeris News Search Result]\n{res}"
        
    # Fallback to Tavily if QVeris fails or returns nothing useful
    return tavily_search.run(qveris_query, max_results=max_results)

@tool
def think_tool(reflection: str) -> str:
    """
    A strategic reflection mechanism to pause and assess progress, analyze findings, 
    identify gaps, and plan next steps.
    """
    return f"Reflection recorded: {reflection}"

_repl_sessions = {}

@tool
def python_interpreter(code: str, config: RunnableConfig = None) -> str:
    """
    A Python REPL to execute code for complex calculations, data analysis, or simulations.
    Always use print() to see results.
    """
    try:
        # Clean up code: remove markdown blocks if present
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]
        
        code = code.strip()
        
        # Security: Basic check to prevent malicious imports if needed, 
        # though this is a research environment.
        
        thread_id = config.get("configurable", {}).get("thread_id", "default") if config else "default"
        if thread_id not in _repl_sessions:
            _repl_sessions[thread_id] = PythonREPL()
        
        repl = _repl_sessions[thread_id]
        result = repl.run(code)
        
        # If result is empty but no error, maybe they forgot to print?
        if not result.strip() and "print(" not in code:
            return "Execution successful, but no output. Please use print() to output results."
            
        return result
    except Exception as e:
        return f"Error executing code: {str(e)}"

@tool
def calculator(expression: str) -> str:
    """Evaluate a single mathematical expression safely (no builtins). Supports basic arithmetic."""
    try:
        # Pre-process: remove currency symbols and commas
        clean_expr = expression.replace("$", "").replace(",", "")
        # Safe evaluation with limited scope
        result = eval(clean_expr, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        # Fallback: try to extract numbers and calculate if it's a simple division/multiplication
        import re
        nums = re.findall(r"[-+]?\d*\.\d+|\d+", expression)
        if len(nums) == 2:
            try:
                n1, n2 = float(nums[0]), float(nums[1])
                if "/" in expression: return str(n1 / n2)
                if "*" in expression: return str(n1 * n2)
                if "+" in expression: return str(n1 + n2)
                if "-" in expression: return str(n1 - n2)
            except:
                pass
        return f"Error evaluating expression: {e}. Hint: Ensure input is a pure numerical expression."

@tool
def calculate_dcf(fcf: float, discount_rate: float, growth_rate: float, years: int = 10) -> str:
    """Calculate a simple multi-year DCF enterprise value from a starting free cash flow."""
    try:
        fcf_val = float(fcf)
        r = float(discount_rate)
        g = float(growth_rate)
        n = int(years)
        if r <= g:
            return "Error: discount_rate must be greater than growth_rate."
        pv = 0.0
        for t in range(1, n + 1):
            pv += (fcf_val * ((1 + g) ** t)) / ((1 + r) ** t)
        terminal = (fcf_val * ((1 + g) ** (n + 1))) / (r - g)
        pv_terminal = terminal / ((1 + r) ** n)
        return json.dumps({"pv_cashflows": pv, "pv_terminal": pv_terminal, "enterprise_value": pv + pv_terminal}, ensure_ascii=False)
    except Exception as e:
        return f"Error calculating DCF: {e}"

@tool
async def extract_experience(task: str, outcome: str, importance: float):
    """
    Store task outcomes and lessons in the agent's memory system.
    """
    logger.info(f"Memory: Extracting experience for task: {task[:50]}... Importance: {importance}")
    if disable_memory:
        logger.warning("Memory: Attempted to extract experience but memory is disabled.")
        return "Hierarchical Memory disabled."
    
    t0 = time.time()
    await memory.write(Experience(
        id=f"exp_{int(datetime.now().timestamp())}",
        task=task,
        context={},
        outcome=outcome,
        lessons=["Auto-extracted lesson based on task success."],
        importance=importance,
    ))
    dt = time.time() - t0
    logger.info(f"Memory: Experience stored in {dt:.2f}s.")
    return "Experience successfully extracted and stored in Hierarchical Memory."

@tool
async def evolve_skill(skill_id: str, feedback: str) -> str:
    """
    Explicitly trigger the evolution of a specific skill based on performance feedback.
    This will mutate the skill's prompt chromosome using the evolution engine.
    """
    logger.info(f"Evolution: Mutation triggered for skill '{skill_id}'. Feedback: {feedback[:100]}...")
    if disable_evolution:
        logger.warning("Evolution: Attempted to evolve skill but evolution is disabled.")
        return "Evolution disabled."
    skill = skill_library.get_skill(skill_id)
    if not skill:
        logger.error(f"Evolution: Skill '{skill_id}' not found.")
        return f"Skill {skill_id} not found."
    
    t0 = time.time()
    mutated_genotype = await evolution_engine.mutate(skill.genotype, feedback)
    dt = time.time() - t0
    logger.info(f"Evolution: Skill '{skill_id}' evolved into '{mutated_genotype.skill_id}' in {dt:.2f}s.")
    
    new_skill = Skill(mutated_genotype)
    skill_library.add_skill(new_skill)
    
    # Also update the fitness score of the original skill based on negative feedback
    skill.update_fitness(0.1) 
    
    return f"Skill {skill_id} evolved into {mutated_genotype.skill_id}. New Prompt: {mutated_genotype.prompt_chromosome[:100]}... Use 'invoke_skill' with the new ID to test it."

@tool
async def invoke_skill(skill_id: str, input: str, params: Optional[Dict[str, Any]] = None, config: RunnableConfig = None) -> str:
    """
    Invokes a specialized skill from the library by its ID.
    This will execute the skill's specific analysis logic using the LLM.
    """
    # Normalize skill_id by removing prefixes for internal mapping if necessary
    clean_id = skill_id.split(":")[-1] if ":" in skill_id else skill_id

    # 1. Check if it's a built-in tool first
    if clean_id == "python_interpreter":
        code = (params or {}).get("code") if isinstance(params, dict) else None
        return await python_interpreter.ainvoke({"code": code or input}, config=config)
    if clean_id == "calculator":
        expression = (params or {}).get("expression") if isinstance(params, dict) else None
        return calculator.run(expression or input)
    if clean_id == "calculate_dcf":
        if not isinstance(params, dict):
            return "Error: calculate_dcf requires params."
        fcf = params.get("fcf")
        if fcf is None:
            fcf = params.get("cash_flow")
        discount_rate = params.get("discount_rate")
        growth_rate = params.get("growth_rate")
        years = params.get("years", 10)
        try:
            return calculate_dcf.invoke({"fcf": fcf, "discount_rate": discount_rate, "growth_rate": growth_rate, "years": years})
        except Exception as e:
            return f"Error executing calculate_dcf: {str(e)}"
    if clean_id == "search_financial_news":
        query = (params or {}).get("query") if isinstance(params, dict) else None
        max_results = (params or {}).get("max_results") if isinstance(params, dict) else None
        if max_results is None:
            return search_financial_news.run(query or input)
        return search_financial_news.invoke({"query": query or input, "max_results": int(max_results)})
    if clean_id == "tavily_search":
        return tavily_search.run(input)
    if clean_id == "qveris_discover" or clean_id == "discover":
        return await qveris_discover.ainvoke({"query": input})
    if clean_id == "qveris_inspect" or clean_id == "inspect":
        return await qveris_inspect.ainvoke({"tool_ids": [input]})
    if clean_id == "qveris_call" or clean_id == "call":
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
        "get_crypto_price": get_crypto_price,
        "get_historical_data": get_historical_data
    }
    
    if clean_id in qveris_map:
        # Extract the core parameter from input string if LLM passed it weirdly
        import re
        # Simple heuristic to extract symbol/indicator
        param_val = input.split(":")[-1].strip() if ":" in input else input.strip()
        # For safety, if params are passed correctly, use them
        if params and len(params) > 0:
            param_val = list(params.values())[0]
        else:
            # try to find uppercase letters
            words = re.findall(r'[A-Z/_.-]+', input)
            if words:
                param_val = words[0]
                
        try:
            res = qveris_map[clean_id].invoke(param_val)
            return f"[QVeris Tool {clean_id} Executed]\n{res}"
        except Exception as e:
            return f"Error executing QVeris tool {clean_id}: {str(e)}"
            
    skill = skill_library.get_skill(skill_id) # Try full ID first
    if not skill:
        skill = skill_library.get_skill(f"builtin:{clean_id}") # Then try builtin prefix
    
    if not skill:
        return f"Skill {skill_id} not found in the library."
    
    # Execute the skill using the meta_model and the prompt_chromosome
    from langchain_core.messages import SystemMessage, HumanMessage
    
    system_msg = SystemMessage(content=skill.genotype.prompt_chromosome)
    user_content = f"Input: {input}"
    if params:
        user_content += f"\nParameters: {json.dumps(params)}"
        
    try:
        t0 = time.time()
        # If deepagents is available, use it to allow the skill to call tools if needed
        if create_deep_agent is not None:
            # We provide a subset of tools to avoid recursive complexity
            skill_tools_subset = [tavily_search, search_financial_news, get_stock_price, get_historical_data, get_financial_statements, get_exchange_rate, get_macro_data, get_crypto_price, python_interpreter, calculator, calculate_dcf]
            skill_agent = create_deep_agent(model=model, tools=skill_tools_subset, system_prompt=skill.genotype.prompt_chromosome)
            response_msg = await skill_agent.ainvoke({"messages": [HumanMessage(content=user_content)]})
            response = response_msg["messages"][-1]
            
            # --- Handle Skill Tool Simulation ---
            # If the response contains <tool_call> but was not executed, manually execute it.
            import re
            content = response.content
            tool_call_match = re.search(r"<tool_call>(.*?)</tool_call>", content, re.DOTALL)
            if tool_call_match:
                try:
                    tool_call_json = json.loads(tool_call_match.group(1).strip())
                    # Expecting {"tool_name": {"param": "val"}}
                    tool_name = list(tool_call_json.keys())[0]
                    tool_args = list(tool_call_json.values())[0]
                    
                    # Find tool in subset
                    target_tool = next((t for t in skill_tools_subset if t.name == tool_name), None)
                    if target_tool:
                        logger.info(f"Skill {skill_id} simulated tool call '{tool_name}'. Executing manually...")
                        tool_res = await target_tool.ainvoke(tool_args)
                        content = f"[Tool {tool_name} Executed]\n{tool_res}\n\n[Original Analysis]\n{content}"
                except Exception as e:
                    logger.warning(f"Failed to manually execute skill tool call: {e}")
            
            final_content = content
        else:
            response = await ainvoke_with_retry(model, [system_msg, HumanMessage(content=user_content)])
            final_content = response.content
        
        dt = time.time() - t0
        
        meta = getattr(response, "response_metadata", {}) or {}
        tu = meta.get("token_usage", {}) or {}
        in_tokens = tu.get("prompt_tokens", 0)
        out_tokens = tu.get("completion_tokens", 0)
        
        logger.info(f"Skill {skill_id}: Inference finished in {dt:.2f}s. Tokens: IN={in_tokens}, OUT={out_tokens}")
        return f"[Skill {skill_id} Execution Result]\n{final_content}"
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

async def ainvoke_with_retry(model, messages, max_retries=7, initial_delay=5, **kwargs):
    """Helper to invoke model with exponential backoff on 429/rate limit errors."""
    import random
    for attempt in range(max_retries):
        try:
            return await model.ainvoke(messages, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "throttling" in err_str or "rate limit" in err_str:
                # Add significant jitter and longer delay to prevent shards from synchronized retries
                delay = initial_delay * (1.5 ** attempt) + random.uniform(1, 10)
                logger.warning(f"Rate limit hit (429). Retrying in {delay:.2f}s... (Attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(delay)
                continue
            raise e
    return await model.ainvoke(messages, **kwargs)

async def run_multi_skill_orchestrator_with_logs(complex_task: str, config: RunnableConfig = None) -> Dict[str, Any]:
    from langchain_core.messages import SystemMessage, HumanMessage
    import re
    import hashlib

    # Generate a session-specific thread_id for variable persistence
    # Use the existing thread_id if available, otherwise hash the task
    base_thread_id = config.get("configurable", {}).get("thread_id", "default") if config else "default"
    session_id = f"{base_thread_id}_{hashlib.md5(complex_task.encode()).hexdigest()[:8]}"
    session_config = {"configurable": {"thread_id": session_id}}

    skills_info = []
    if not is_plan_only:
        skills = skill_library.get_all_skills()
        for s in skills:
            deps = f" (Depends on: {', '.join(s.genotype.tool_deps)})" if s.genotype.tool_deps else ""
            skills_info.append(f"- {s.genotype.skill_id}: {s.genotype.prompt_chromosome[:200]}...{deps}")

    built_in_tools = [
        "- qveris:get_stock_price: [QVeris] Get real-time stock price (e.g. 'AAPL')",
        "- qveris:get_financial_statements: [QVeris] Get latest annual income statement data",
        "- qveris:get_exchange_rate: [QVeris] Get forex exchange rate (e.g. 'EUR/USD')",
        "- qveris:get_macro_data: [QVeris] Get US macroeconomic data (CPI, FEDERAL_FUNDS_RATE, TREASURY_YIELD_10Y)",
        "- qveris:get_crypto_price: [QVeris] Get real-time cryptocurrency price (e.g. 'BTC')",
        "- qveris:search_financial_news: [HIGH PRIORITY] Search recent financial news using QVeris",
        "- tavily:tavily_search: [LOW PRIORITY] General web search (only if QVeris tools are insufficient)",
        "- builtin:python_interpreter: Execute Python code for calculations (use this for ALL math, DCF, and calculations — NEVER use calculator or calculate_dcf)"
    ]
    skills_info.extend(built_in_tools)
    skills_str = "\n".join(skills_info)
    logger.info(f"Orchestrator: Available skills for planning: {len(skills_info)} items loaded.")

    # In Plan-only mode, we skip memory injection and evolution-related logic.
    if is_plan_only:
        rules_str = "No specific rules provided (Plan-only mode)."
        logger.info("Orchestrator: Plan-only mode enabled. Skipping procedural memory injection.")
    else:
        rules = memory.get_procedural_rules()
        if rules:
            logger.info(f"Orchestrator: Injected {len(rules)} procedural rules from memory.")
        else:
            logger.info("Orchestrator: No procedural rules found in memory to inject.")
        rules_str = "\n".join([f"- {r.content}" for r in rules]) if rules else "No specific rules yet."

    # Estimate task complexity to constrain plan length
    import re as _re
    _skill_keywords = len(_re.findall(r'获取|查询|计算|分析|检索|评估|对比', complex_task))
    if _skill_keywords <= 2:
        complexity_hint = "SIMPLE TASK (≤2 data points needed): Generate a plan with AT MOST 3 steps. Do NOT add data_extraction or strategic_decision_making unless the task explicitly requires analysis."
    elif _skill_keywords <= 4:
        complexity_hint = "MEDIUM TASK: Generate a plan with 4-6 steps. Only add strategic_decision_making if the task requires a final investment recommendation."
    else:
        complexity_hint = "COMPLEX TASK: Use full orchestration pipeline as needed."

    plan_prompt = f"""
    You are the Strategic Orchestration Engine for EvoFinAgent.
    Your goal is to solve the complex financial task below by orchestrating specialized skills.
    
    ### Task:
    {complex_task}
    
    ### Available Skills:
    {skills_str}
    
    ### Procedural Memory (Best Practices):
    {rules_str}
    
    ### COMPLEXITY GUIDANCE:
    {complexity_hint}

    ### MANDATORY EXECUTION RULES:
    - **QVERIS PRIORITY**: You MUST prioritize using QVeris tools (get_*, search_financial_news) for financial data and news. Only use 'tavily_search' as a last resort for general information not available via QVeris.
    - **NO SIMULATION**: You MUST actually call the skills.
    - **DATA EXTRACTION FIRST**: Before using 'python_interpreter' or 'technical_analysis', you MUST use 'data_extraction' to get clean numerical strings if the source is complex JSON or unstructured text.
    - **PYTHON INPUT (STRICT)**: In 'python_interpreter', ALWAYS use `print()` to see results. NEVER use hardcoded numbers from your knowledge; use placeholders like `{{step_1_output}}`.
    - **NO HALLUCINATION ON FAILURE**: If a calculation or search tool fails (e.g., SyntaxError, 404), you MUST NOT guess the result. Instead, try a different approach or report the failure.
    - **DATA VERIFICATION**: Every claim must be backed by a skill output.
    - **SYNTHESIS RIGOR**: The final step MUST use 'strategic_decision_making'.
    
    ### PLACEHOLDER USAGE:
    Use {{step_N_output}} to refer to previous results. 
    
    Output your plan as a JSON list of steps. 
    IMPORTANT: You MUST use the exact 'skill_id' as listed in the Available Skills section above, including any prefixes (e.g., 'qveris:', 'builtin:', 'tavily:').
    Format: [{{"step": 1, "skill_id": "...", "reasoning": "...", "input": "...", "params": {{"symbol": "AAPL"}}}}]
    """

    logger.info(f"Orchestrator: Planning started for complex task: {complex_task[:100]}...")
    t0 = time.time()
    plan_response = await ainvoke_with_retry(model, [
        SystemMessage(content="You are an expert financial strategist and orchestration engine. You NEVER simulate tool calls; you ALWAYS execute them."),
        HumanMessage(content=plan_prompt)
    ])
    dt = time.time() - t0
    
    meta = getattr(plan_response, "response_metadata", {}) or {}
    tu = meta.get("token_usage", {}) or {}
    in_tokens = tu.get("prompt_tokens", 0)
    out_tokens = tu.get("completion_tokens", 0)
    
    logger.info(f"Orchestrator: Planning completed in {dt:.2f}s. Tokens: IN={in_tokens}, OUT={out_tokens}")

    plan_raw = plan_response.content
    plan_usage = getattr(plan_response, "response_metadata", {}) or {}
    json_match = re.search(r"\[.*\]", plan_raw, re.DOTALL)
    if not json_match:
        logger.warning(f"Orchestrator: Failed to parse plan JSON. Raw output: {plan_raw[:500]}...")
        return {
            "success": False,
            "failure_mode": "planning",
            "error": "Failed to generate a structured plan.",
            "plan_raw": plan_raw,
            "plan": [],
            "execution_logs": [],
            "final_answer": "",
            "llm_usage": {"plan": plan_usage},
        }

    _plan_str = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', json_match.group(0))
    try:
        plan = json.loads(_plan_str)
    except Exception:
        try:
            from json_repair import repair_json
            plan = json.loads(repair_json(_plan_str))
        except Exception as e:
            logger.warning(f"Orchestrator: Failed to parse plan JSON after repair: {e}")
            return {
                "success": False,
                "failure_mode": "planning",
                "error": str(e),
                "plan_raw": plan_raw,
                "plan": [],
                "execution_logs": [],
                "final_answer": "",
                "llm_usage": {"plan": plan_usage},
            }
    logger.info(f"Orchestrator: Plan generated with {len(plan)} steps.")

    results = []
    context_accumulator = ""
    execution_logs = []
    for step in plan:
        skill_id = step.get("skill_id")
        step_input = step.get("input")
        reasoning = step.get("reasoning", "")
        params = step.get("params", None)

        logger.info(f"Orchestrator: [Step {step.get('step')}/{len(plan)}] - {reasoning} (Using {skill_id})")

        # --- Placeholder Replacement Logic ---
        def _extract_first_number(text: str) -> str:
            """Extract first numeric value from text for use in python_interpreter."""
            import re as _re
            # Try JSON field first: "key": 123.45
            m = _re.search(r'["\'][\w_]+["\']\s*:\s*([-+]?\d[\d,]*\.?\d*)', text)
            if m:
                return m.group(1).replace(',', '')
            # Fall back to first standalone number
            m = _re.search(r'(?<!["\w])([-+]?\d[\d,]*\.?\d*)(?![\d"])', text)
            return m.group(1).replace(',', '') if m else text

        def replace_placeholders(obj, logs, for_python=False):
            import re
            if isinstance(obj, str):
                sorted_logs = sorted(logs, key=lambda x: x['step'], reverse=True)
                for log in sorted_logs:
                    step_num = log['step']
                    raw_val = str(log["output"])
                    val = _extract_first_number(raw_val) if for_python else raw_val
                    patterns = [
                        rf'\{{\{{step_{step_num}(_[a-zA-Z0-9_]+)?\}}\}}',
                        rf'\{{step_{step_num}(_[a-zA-Z0-9_]+)?\}}',
                        rf'\[step_{step_num}(_[a-zA-Z0-9_ ]+)?\]',
                        rf'\[step {step_num}( [a-zA-Z0-9_ ]+)?\]',
                        rf'<output_step_{step_num}>',
                        rf'<step_{step_num}_output>'
                    ]
                    for p in patterns:
                        obj = re.compile(p, re.IGNORECASE).sub(val, obj)
                return obj
            elif isinstance(obj, dict):
                return {k: replace_placeholders(v, logs, for_python) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_placeholders(i, logs, for_python) for i in obj]
            return obj

        is_python_step = skill_id in ('builtin:python_interpreter', 'python_interpreter')
        params = replace_placeholders(params, execution_logs, for_python=is_python_step)
        step_input = replace_placeholders(step_input, execution_logs, for_python=is_python_step)
        # ---------------------------------------

        enriched_input = f"Task: {step_input}\nPrevious Context: {context_accumulator[:2000]}"

        t0 = time.time()
        try:
            # For python_interpreter steps, generate actual Python code via LLM first
            if is_python_step:
                _py_prompt = (
                    f"Write a short Python script to complete this calculation task. "
                    f"Use only the numeric values already present in the task description. "
                    f"Always use print() to output results. No imports needed for basic math.\n\n"
                    f"Task: {step_input}\n\nContext (for reference only):\n{context_accumulator[:1500]}\n\n"
                    f"Output ONLY the Python code, no explanation, no markdown fences."
                )
                _code_msg = await ainvoke_with_retry(model, [
                    SystemMessage(content="You are a Python code generator. Output only executable Python code."),
                    HumanMessage(content=_py_prompt)
                ])
                _generated_code = _code_msg.content.strip()
                if _generated_code.startswith("```"):
                    _generated_code = _generated_code.split("```")[1]
                    if _generated_code.startswith("python"):
                        _generated_code = _generated_code[6:]
                    _generated_code = _generated_code.rstrip("`").strip()
                res = await python_interpreter.ainvoke({"code": _generated_code}, config=session_config)
            else:
                res = await invoke_skill.ainvoke(
                    {"skill_id": skill_id, "input": enriched_input, "params": params},
                    config=session_config
                )
            dt = time.time() - t0
            logger.info(f"Orchestrator: [Step {step.get('step')}/{len(plan)}] - Execution finished in {dt:.2f}s.")

            # Detect tool failure and try fallback if declared in plan
            _res_str = str(res).lower()
            _tool_failed = any(x in _res_str for x in ['error', '429', '403', 'failed', 'exception', 'no output', '无输出'])
            if _tool_failed:
                fallback_skill = step.get('fallback_skill')
                if fallback_skill:
                    logger.warning(f"Orchestrator: Step {step.get('step')} failed, trying fallback: {fallback_skill}")
                    try:
                        res = await invoke_skill.ainvoke(
                            {"skill_id": fallback_skill, "input": enriched_input, "params": params},
                            config=session_config
                        )
                    except Exception as _fe:
                        res = f"[Fallback {fallback_skill} also failed: {_fe}]"
                else:
                    context_accumulator += f"\n[WARNING: Step {step.get('step')} ({skill_id}) failed. Downstream steps must NOT fabricate this data.]"
        except Exception as _step_exc:
            dt = time.time() - t0
            logger.error(f"Orchestrator: [Step {step.get('step')}/{len(plan)}] - Exception after {dt:.2f}s: {_step_exc}")
            res = f"[Step {step.get('step')} ({skill_id}) failed with exception: {_step_exc}]"
            context_accumulator += f"\n[WARNING: Step {step.get('step')} ({skill_id}) raised an exception. Downstream steps must NOT fabricate this data.]"

        step_record = f"--- STEP {step.get('step')} ({skill_id}) ---\nReasoning: {reasoning}\nOutput: {res}"
        results.append(step_record)
        execution_logs.append({
            "step": step.get("step"),
            "skill_id": skill_id,
            "reasoning": reasoning,
            "input": step_input,
            "params": params,
            "output": res[:4000],
        })
        context_accumulator += f"\n[Result from Step {step.get('step')} ({skill_id})]: {res[:1000]}"

    logs_str = "\n\n".join(results)
    synthesis_prompt = f"""
        You are the Senior Financial Analyst for EvoFinAgent.
        Task: {complex_task}
        
        Detailed Execution Logs (VERIFIED EVIDENCE):
        {logs_str}
        
        ### Final Instructions:
        1. **STRICT FAITHFULNESS**: Your answer MUST ONLY contain data points that are present in the logs above. 
        2. **NO HALLUCINATION**: If a tool (like Python or technical_analysis) failed or was not called, DO NOT invent results for it. Explicitly state that the data was unavailable.
        3. **DATA TRACEABILITY**: Every number you cite must be traceable to a specific Step in the logs.
        4. **PYTHON VERIFICATION**: If 'python_interpreter' was used, YOU MUST SHOW THE PYTHON CODE AND THE OUTPUT. If it returned an error, report the error, do not bypass it.
        5. **SYNTHESIS**: Unify all findings into a high-conviction recommendation.
        """
    
    logger.info("Orchestrator: Starting final synthesis...")
    t0 = time.time()
    final_res = await ainvoke_with_retry(model, [
        SystemMessage(content="You are a senior financial analyst providing a final recommendation based on verified execution logs. You provide PROOF of work."),
        HumanMessage(content=synthesis_prompt)
    ])
    dt = time.time() - t0
    
    meta = getattr(final_res, "response_metadata", {}) or {}
    tu = meta.get("token_usage", {}) or {}
    in_tokens = tu.get("prompt_tokens", 0)
    out_tokens = tu.get("completion_tokens", 0)
    
    logger.info(f"Orchestrator: Final synthesis completed in {dt:.2f}s. Tokens: IN={in_tokens}, OUT={out_tokens}")
    synthesis_usage = getattr(final_res, "response_metadata", {}) or {}

    chain_str = " -> ".join([f"{log['skill_id']}" for log in execution_logs])
    appendix = f"\n\n---\n## Execution Skill Call Chain\n⛓️ {chain_str}\n\n### 🛠 Execution Logs\n"
    for log in execution_logs:
        appendix += f"- **Step {log['step']} ({log['skill_id']})**: {str(log.get('input', ''))[:100]}...\n"

    # --- Post-Task Reflection (Memory & Evolution) ---
    if not disable_memory and not is_plan_only:
        try:
            logger.info("Orchestrator: Triggering post-task experience extraction...")
            await extract_experience.ainvoke({
                "task": complex_task,
                "outcome": final_res.content[:500],
                "importance": 0.8 # Standard importance for benchmark tasks
            })
        except Exception as e:
            logger.error(f"Orchestrator: Failed to extract experience: {e}")

    return {
        "success": True,
        "failure_mode": None,
        "error": None,
        "plan_prompt": plan_prompt,
        "plan_raw": plan_raw,
        "plan": plan,
        "execution_logs": execution_logs,
        "final_answer": final_res.content + appendix,
        "final_answer_no_appendix": final_res.content,
        "llm_usage": {"plan": plan_usage, "synthesis": synthesis_usage},
    }
    
async def run_sop_baseline_with_logs(complex_task: str, config: RunnableConfig = None) -> Dict[str, Any]:
    """
    MetaGPT-style SOP baseline: Planner -> Executor -> Reviewer -> Writer.
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    import re
    
    logger.info(f"SOP Baseline: Starting for task: {complex_task[:100]}...")
    
    # 1. Planner
    planner_prompt = f"You are a Financial Planner. Break down this task into steps: {complex_task}"
    res_p = await ainvoke_with_retry(model, [SystemMessage(content="Plan the task."), HumanMessage(content=planner_prompt)], config=config)
    plan = res_p.content
    
    # 2. Executor (Simplified: one big call to tools or a loop)
    executor_prompt = f"Execute this plan: {plan}\nTask: {complex_task}\nUse tools as needed."
    # For simplicity in baseline, we'll use a ReAct agent or a single call if we want to be "sop-like"
    # Let's use the standard agent for execution
    from deepagents import create_deep_agent
    
    # Use the same tools as the main agent
    tools = [
        tavily_search,
        search_financial_news,
        get_stock_price,
        get_financial_statements,
        get_exchange_rate,
        get_macro_data,
        get_crypto_price,
        python_interpreter,
        calculator,
        calculate_dcf
    ]
    exec_agent = create_deep_agent(model=model, tools=tools, system_prompt="Execute the plan.")
    res_e = await exec_agent.ainvoke({"messages": [HumanMessage(content=executor_prompt)]}, config=config)
    exec_out = res_e["messages"][-1].content
    
    # 3. Reviewer
    reviewer_prompt = f"Review this execution: {exec_out}\nTask: {complex_task}\nProvide feedback."
    res_r = await ainvoke_with_retry(model, [SystemMessage(content="Review the execution."), HumanMessage(content=reviewer_prompt)], config=config)
    review = res_r.content
    
    # 4. Writer
    writer_prompt = f"Synthesize final answer. Task: {complex_task}\nExecution: {exec_out}\nReview: {review}"
    res_w = await ainvoke_with_retry(model, [SystemMessage(content="Write final answer."), HumanMessage(content=writer_prompt)], config=config)
    
    return {
        "success": True,
        "final_answer": res_w.content,
        "execution_logs": [{"step": "sop_flow", "output": exec_out}],
        "llm_usage": {} # Simplified
    }

async def run_finagent_dvampire_style_with_logs(complex_task: str, config: RunnableConfig = None) -> Dict[str, Any]:
    """
    DVampire-style FinAgent baseline: Market Intelligence -> Low-level Reflection -> High-level Reflection -> Decision.
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    
    logger.info(f"FinAgent (DVampire Style): Starting for task: {complex_task[:100]}...")
    execution_logs = []
    
    # 1. Market Intelligence (Execution)
    # We use the orchestrator's planning/execution but strictly follow the 3-step reflection loop
    mi_prompt = f"Gather all necessary market intelligence for this task: {complex_task}"
    # Use standard tool set
    tools_list = [tavily_search, search_financial_news, get_stock_price, get_financial_statements, get_exchange_rate, get_macro_data, get_crypto_price, python_interpreter, calculator, calculate_dcf]
    exec_agent = create_deep_agent(model=model, tools=tools_list, system_prompt="Gather market data.")
    res_mi = await exec_agent.ainvoke({"messages": [HumanMessage(content=mi_prompt)]}, config=config)
    mi_out = res_mi["messages"][-1].content
    execution_logs.append({"step": "market_intelligence", "output": mi_out})
    
    # 2. Low-level Reflection
    ll_prompt = f"Perform low-level reflection on this data: {mi_out}\nTask: {complex_task}"
    res_ll = await ainvoke_with_retry(model, [SystemMessage(content="Perform low-level reflection."), HumanMessage(content=ll_prompt)], config=config)
    ll_out = res_ll.content
    execution_logs.append({"step": "low_level_reflection", "output": ll_out})
    
    # 3. High-level Reflection
    hl_prompt = f"Perform high-level reflection. Data: {mi_out}\nLow-level analysis: {ll_out}\nTask: {complex_task}"
    res_hl = await ainvoke_with_retry(model, [SystemMessage(content="Perform high-level reflection."), HumanMessage(content=hl_prompt)], config=config)
    hl_out = res_hl.content
    execution_logs.append({"step": "high_level_reflection", "output": hl_out})
    
    # 4. Decision
    decision_prompt = f"Final decision/answer. Task: {complex_task}\nContext: {mi_out}\nAnalysis: {hl_out}"
    res_d = await ainvoke_with_retry(model, [SystemMessage(content="Make final decision."), HumanMessage(content=decision_prompt)], config=config)
    
    return {
        "success": True,
        "final_answer": res_d.content,
        "execution_logs": execution_logs,
        "llm_usage": {}
    }

async def run_finmem_style_with_logs(complex_task: str, config: RunnableConfig = None) -> Dict[str, Any]:
    """
    FinMem-style baseline: Short/Mid/Long-term Memory Retrieval -> Reflection -> Action.
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    
    logger.info(f"FinMem Style: Starting for task: {complex_task[:100]}...")
    execution_logs = []
    
    # 1. Retrieval (Simulated as a data gathering step)
    retrieve_prompt = f"Retrieve relevant information from short/mid/long term memory (Web/Tools) for: {complex_task}"
    tools_list = [tavily_search, search_financial_news, get_stock_price, get_financial_statements, get_exchange_rate, get_macro_data, get_crypto_price, python_interpreter, calculator, calculate_dcf]
    exec_agent = create_deep_agent(model=model, tools=tools_list, system_prompt="Retrieve information.")
    res_ret = await exec_agent.ainvoke({"messages": [HumanMessage(content=retrieve_prompt)]}, config=config)
    ret_out = res_ret["messages"][-1].content
    execution_logs.append({"step": "memory_retrieval", "output": ret_out})
    
    # 2. Reflection
    reflect_prompt = f"Reflect on retrieved information: {ret_out}\nTask: {complex_task}"
    res_ref = await ainvoke_with_retry(model, [SystemMessage(content="Reflect on memory."), HumanMessage(content=reflect_prompt)], config=config)
    ref_out = res_ref.content
    execution_logs.append({"step": "reflection", "output": ref_out})
    
    # 3. Action (Final Answer)
    action_prompt = f"Final answer based on reflection: {ref_out}\nTask: {complex_task}"
    res_act = await ainvoke_with_retry(model, [SystemMessage(content="Take final action."), HumanMessage(content=action_prompt)], config=config)
    
    return {
        "success": True,
        "final_answer": res_act.content,
        "execution_logs": execution_logs,
        "llm_usage": {}
    }

async def run_review_revise_baseline_with_logs(task_or_query: Any, config: RunnableConfig = None) -> Dict[str, Any]:
    """
    AFlow-inspired review & revise baseline: Plan -> Execute -> Self-review -> Revise.
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    
    if isinstance(task_or_query, dict):
        complex_task = (task_or_query.get("query") or task_or_query.get("task") or "").strip()
        evaluation_criteria = task_or_query.get("evaluation_criteria") or {}
    else:
        complex_task = str(task_or_query or "").strip()
        evaluation_criteria = {}

    logger.info(f"Review & Revise Baseline: Starting for task: {complex_task[:100]}...")
    
    # 1. Generate & Execute (Initial attempt)
    # We'll use the orchestrator but with a flag or just a simplified version
    initial_res = await run_multi_skill_orchestrator_with_logs(complex_task, config=config)
    if not initial_res.get("success"):
        return initial_res
        
    initial_ans = initial_res.get("final_answer_no_appendix")
    execution_logs = initial_res.get("execution_logs", []) or []

    has_tool_failure = False
    for x in execution_logs:
        if not isinstance(x, dict):
            continue
        out = x.get("output")
        if isinstance(out, str) and (
            "Error executing QVeris tool" in out
            or "Request failed" in out
            or "validation error" in out
            or "Connection reset by peer" in out
        ):
            has_tool_failure = True
            break

    # 2. Self-Review
    evidence_json = json.dumps(execution_logs, ensure_ascii=False)
    if len(evidence_json) > 15000:
        evidence_json = evidence_json[:15000] + "\n...[truncated]..."

    review_prompt = (
        "你将对一份金融分析回答进行严格审阅（目标：对齐评测打分标准）。\n"
        "必须遵守：\n"
        "- 任何数字若未在 execution_logs 的工具输出中出现，则视为 fabrication，必须在修订版中剔除或标注为无法获取。\n"
        "- 如 python_interpreter 报错，最终答案不得声称“已验证输出”。\n\n"
        f"Task: {complex_task}\n\n"
        f"Evaluation Criteria: {json.dumps(evaluation_criteria, ensure_ascii=False)}\n\n"
        f"Execution Logs (evidence): {evidence_json}\n\n"
        f"Draft Answer: {initial_ans}\n\n"
        "请简要列出：1. 缺失指标；2. 无法追溯的数字；3. 修正建议。"
    )
    
    # Use a faster/more direct call if possible, but keep it consistent
    res_rev = await ainvoke_with_retry(
        model,
        [SystemMessage(content="You are a strict financial auditor."), HumanMessage(content=review_prompt)],
        config=config,
    )
    critique = res_rev.content
    
    # 3. Revise
    revise_prompt = (
        "根据审计意见改写答案。\n"
        "硬性约束：\n"
        "- 严禁编造轨迹中不存在的数字；\n"
        "- 如果某项指标无法从证据中获得，必须明确写“未能通过工具获取”；\n"
        "- 不要在答案里写 placeholder/proxy/人工校验。\n\n"
        f"Task: {complex_task}\n\n"
        f"Auditor Critique: {critique}\n\n"
        f"Execution Logs: {evidence_json}\n\n"
        f"Original Answer: {initial_ans}\n"
    )
    res_final = await ainvoke_with_retry(
        model,
        [SystemMessage(content="Revise to maximize fidelity and criteria coverage."), HumanMessage(content=revise_prompt)],
        config=config,
    )
    
    revised_ans = res_final.content
    
    # Combine results
    final_res = initial_res.copy()
    final_res["final_answer"] = revised_ans
    final_res["review_critique"] = critique
    
    return final_res

@tool
async def multi_skill_orchestrator(complex_task: str, config: RunnableConfig = None) -> str:
    """
    A high-level orchestrator that plans and executes a sequence of skills to solve a hard task.
    It uses procedural memory (Rules of Thumb) to guide the planning process.
    """
    if disable_orchestration:
        return "Dynamic Orchestration disabled."
    try:
        res = await run_multi_skill_orchestrator_with_logs(complex_task, config=config)
        if res.get("success"):
            return res.get("final_answer", "")
        return f"Error during orchestration: {res.get('error') or res.get('failure_mode')}"
        
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
        skill_id="builtin:fetch_market_data",
        category=SkillCategory.DATA,
        llm_config={"model_tier": ModelTier.STANDARD, "temperature": 0.1, "max_tokens": 1000},
        prompt_chromosome="""You are a specialized financial data fetcher. 
        Your goal is to retrieve historical and real-time price data, volume, and volatility metrics for the requested asset.
        
        ### MANDATORY:
        - **SPOT PRICE PREFERENCE**: Always prioritize REAL SPOT PRICE over funds, trusts, or derivatives.
        - If the user asks for 30 days, you MUST ensure the output contains data covering the full 30-day period.
        - Output the raw data clearly.
        """,
        tool_deps=[],
        input_schema={"asset": "string", "timeframe": "string"},
        output_schema={"data": "string"}
    )
    skill_library.add_skill(Skill(market_data_genotype))

    sentiment_genotype = SkillGenotype(
        skill_id="builtin:analyze_sentiment",
        category=SkillCategory.ANALYSIS,
        llm_config={"model_tier": ModelTier.HEAVY, "temperature": 0.3, "max_tokens": 1500},
        prompt_chromosome="""You are an expert financial sentiment analyst. 
        Evaluate the provided news headlines and reports.
        
        ### MANDATORY:
        1. **NO CLARIFICATION**: Do not ask the user for clarification. Analyze the provided text as-is.
        2. **QUANTIFY**: Always provide a sentiment score between -1.0 (extremely bearish) and 1.0 (extremely bullish).
        3. **EVIDENCE**: List the specific keywords or phrases from the input that drove your score.
        4. **NO HALLUCINATION**: If the input is empty or insufficient, return a score of 0.0 and state "Insufficient data for analysis".
        """,
        tool_deps=["builtin:fetch_market_data"],
        input_schema={"query": "string"},
        output_schema={"sentiment": "string", "score": "number", "drivers": "list"}
    )
    skill_library.add_skill(Skill(sentiment_genotype))

    tech_analysis_genotype = SkillGenotype(
        skill_id="builtin:technical_analysis",
        category=SkillCategory.ANALYSIS,
        llm_config={"model_tier": ModelTier.STANDARD, "temperature": 0.1, "max_tokens": 1000},
        prompt_chromosome="""You are a quantitative technical analyst. 
        Analyze the provided price and volume data.
        
        ### DATA FORMAT:
        You expect a string containing OHLCV data or a list of prices.
        If you see a placeholder like "[Step N Output]", STOP and tell the user to provide the actual data.
        
        ### ANALYSIS STEPS:
        1. Calculate SMA-5 (5-day Simple Moving Average) and compare it to the current price.
        2. Calculate RSI-5 (5-day Relative Strength Index).
        3. Identify trend strength: Strong Bullish, Bullish, Neutral, Bearish, Strong Bearish.
        4. Provide clear Support and Resistance levels based on recent price action.
        """,
        tool_deps=["builtin:fetch_market_data"],
        input_schema={"data": "string"},
        output_schema={"sma_5": "number", "rsi_5": "number", "trend": "string", "levels": "dict"}
    )
    skill_library.add_skill(Skill(tech_analysis_genotype))

    python_genotype = SkillGenotype(
        skill_id="builtin:python_interpreter",
        category=SkillCategory.EXECUTION,
        llm_config={"model_tier": ModelTier.STANDARD, "temperature": 0.0, "max_tokens": 1000},
        prompt_chromosome="""You are a Python Interpreter. Execute the provided code and return the output. 
        
        ### EXECUTION RULES:
        1. **CLEAN CODE ONLY**: Your input should be valid Python code. 
        2. **NO RAW TEXT**: If you receive a prompt like "Calculate {{step_1_output}}", you MUST first extract the specific numbers and write them as variables.
        3. **ERROR HANDLING**: If the input is not code but a request, respond with "Error: Received natural language instead of code. Please provide a Python snippet."
        4. **VARIABLE PERSISTENCE**: Remember that variables persist across calls in the same thread.
        
        Output ONLY the result of the code execution.
        """,
        tool_deps=[],
        input_schema={"code": "string"},
        output_schema={"output": "string"}
    )
    skill_library.add_skill(Skill(python_genotype))

    data_extraction_genotype = SkillGenotype(
        skill_id="builtin:data_extraction",
        category=SkillCategory.DATA,
        llm_config={"model_tier": ModelTier.STANDARD, "temperature": 0.0, "max_tokens": 1000},
        prompt_chromosome="""You are a high-precision Data Extraction tool.
        
        ### GOAL:
        Extract raw numerical values and core summaries.
        
        ### PYTHON-FRIENDLY OUTPUT:
        If the next step is a calculation, you MUST output the data as a clean Python dictionary string.
        Example: `{"price": 150.5, "shares": 1000000}`
        
        ### GENERAL OUTPUT:
        Return a clean, structured summary.
        """,
        tool_deps=[],
        input_schema={"text": "string"},
        output_schema={"extracted_data": "string"}
    )
    skill_library.add_skill(Skill(data_extraction_genotype))

    decision_making_genotype = SkillGenotype(
        skill_id="builtin:strategic_decision_making",
        category=SkillCategory.ANALYSIS,
        llm_config={"model_tier": ModelTier.HEAVY, "temperature": 0.0, "max_tokens": 2000},
        prompt_chromosome="""You are an Expert Alpha-Seeking Quant Trader. Your goal is to MAXIMIZE Alpha while maintaining a high Sharpe Ratio.
        
        ### MANDATORY FIDELITY RULES:
        1. **NO EXTRAPOLATION**: ONLY use data points explicitly provided in the 'execution_logs'. 
        2. **STRICT SOURCE CHECK**: If a value (like RSI, SMA, or Price) is not in the logs, you MUST state "Data unavailable in logs" instead of inventing a proxy value.
        3. **FABRICATION = FAILURE**: Any use of data not grounded in tool outputs will result in a zero score for the entire task.
        
        ### STRATEGY CORE:
        1. **Trend is Friend**: If price is above SMA-5 and RSI-5 < 70, MAINTAIN 100% exposure. Only sell if trend breaks.
        2. **Volatility Scaling**: In high volatility, scale exposure to 50-70% if unsure, but stay at 100% if the trend is strong.
        3. **Sentiment as Lead**: If News Sentiment is strongly positive (>0.7), anticipate a breakout and increase exposure BEFORE it happens.
        4. **Drawdown Protection**: If price drops >3% from recent peak AND RSI < 30, it might be a crash. Exit immediately (0% exposure).
        
        ### ANALYSIS PILLARS:
        - **Momentum & Trend**: Analyze SMA distance and RSI slope (based on Log Data).
        - **Sentiment Divergence**: Is news positive while price is flat? (Bullish divergence).
        - **Volume Confirmation**: (If available in Logs) Use volume to confirm trend.
        
        ### OUTPUT FORMAT (MANDATORY):
        - Reasoning: <analysis_of_trend_and_sentiment_grounded_in_logs>
        - Target Exposure: <X>% (0-100)
        - Final Recommendation: <BUY/SELL/HOLD>
        """,
        tool_deps=["builtin:technical_analysis", "builtin:analyze_sentiment"],
        input_schema={"context": "string", "analysis_results": "string"},
        output_schema={"reasoning": "string", "target_exposure": "number", "recommendation": "string"}
    )
    skill_library.add_skill(Skill(decision_making_genotype))

    # --- QVeris Skills ---
    qveris_genotype = SkillGenotype(
        skill_id="qveris:remote_execution",
        category=SkillCategory.EXECUTION,
        llm_config={"model_tier": ModelTier.STANDARD, "temperature": 0.1, "max_tokens": 1000},
        prompt_chromosome="""You are a QVeris Bridge. You can discover, inspect, and call remote financial tools.
        1. Use 'qveris:discover' to find new tools for a query.
        2. Use 'qveris:inspect' to understand how to use a tool.
        3. Use 'qveris:call' to execute the tool.
        
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

# Create the agent.
# deepagents 在部分环境下可能不可用；此时提供一个最小 fallback，
# 以保证评测/脚本仍可跑通（Full variant 主要走 multi_skill_orchestrator，不依赖 deepagents）。
if create_deep_agent is None:
    logger.warning("deepagents 未安装：将使用最小 fallback agent（不支持工具自动调用）。")

    class _FallbackAgent:
        async def ainvoke(self, inputs: Dict[str, Any], config: RunnableConfig = None, **kwargs) -> Dict[str, Any]:
            msgs = inputs.get("messages", inputs)
            resp = await ainvoke_with_retry(model, msgs, config=config, **kwargs)
            return {"messages": [resp]}

    agent = _FallbackAgent()
else:
    agent = create_deep_agent(
        model=model,
        tools=[
            tavily_search,
            search_financial_news,
            get_stock_price,
            get_financial_statements,
            get_exchange_rate,
            get_macro_data,
            get_crypto_price,
            think_tool,
            python_interpreter,
            calculator,
            calculate_dcf,
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
            *skill_tools,
        ],
        system_prompt=system_prompt,
    )
