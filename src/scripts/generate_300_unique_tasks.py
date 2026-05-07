import os
import json
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List

load_dotenv()

# Setup Qwen model via DashScope
llm = ChatOpenAI(
    api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url=os.environ.get("DASHSCOPE_BASE_URL"),
    model=os.environ.get("DASHSCOPE_MODEL", "qwen-max")
)

class EvaluationCriteria(BaseModel):
    final_answer_metrics: List[str] = Field(description="List of required points in the final answer")
    min_tool_calls: int = Field(description="Minimum number of tool calls required")
    must_call_sequence: List[List[str]] = Field(description="Required sequences of tool calls")

class Task(BaseModel):
    task_id: str = Field(description="Unique ID for the task")
    query: str = Field(description="The complex financial task prompt for the agent")
    difficulty: str = Field(description="Difficulty level: 'easy', 'medium', or 'hard'")
    required_skills_subset: List[str] = Field(description="List of skills that the agent must use")
    evaluation_criteria: EvaluationCriteria = Field(description="Metrics for evaluating the agent's performance")

class TaskList(BaseModel):
    tasks: List[Task] = Field(description="List of generated tasks")

parser = JsonOutputParser(pydantic_object=TaskList)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert financial engineer designing an evaluation benchmark for an AI Agent.
The agent has access to various QVeris financial tools and a calculator.
Your job is to generate complex financial queries that require **multi-step reasoning and dynamic tool orchestration**.

Available QVeris Tool Categories/Names:
- `get_stock_price`: Get real-time or historical stock prices.
- `get_financial_statements`: Get income statements, balance sheets, cash flow.
- `get_exchange_rate`: Real-time forex rates.
- `get_macro_data`: Interest rates, CPI, GDP.
- `search_financial_news`: Get recent news for a specific entity.
- `tavily_search`: Search for general information.
- `python_interpreter`: Run code for data analysis or complex math.
- `calculator`: Perform simple math calculations.
- `calculate_dcf`: Calculate Discounted Cash Flow.
- `get_crypto_price`: Get cryptocurrency prices.

Difficulty Definitions:
- **Easy**: 1-2 tool calls, direct logic (e.g., fetch price and calculate growth).
- **Medium**: 3-4 tool calls, intermediate dependencies (e.g., fetch financials, extract data, then calculate ratio).
- **Hard**: 5+ tool calls, complex multi-tool orchestration (e.g., cross-currency valuation with news sentiment and macro overlays).

Constraints for the generated tasks:
1. The query should be realistic, like a query from a hedge fund manager or equity researcher.
2. Provide the queries in Chinese.
3. Output must be in JSON format matching the schema.
4. The theme for this batch is: {theme}.
5. Difficulty: {difficulty}.
"""),
    ("human", "Please generate {count} unique financial tasks for the benchmark starting from task ID {start_id}.\n\n{format_instructions}")
])

async def generate_task(theme, difficulty, start_idx, count=1):
    chain = prompt | llm | parser
    try:
        print(f"Invoking LLM for {difficulty} task...")
        # Add a timeout to avoid hanging
        result = await asyncio.wait_for(
            chain.ainvoke({
                "theme": theme,
                "difficulty": difficulty,
                "count": count,
                "start_id": f"T{start_idx:03d}",
                "format_instructions": parser.get_format_instructions()
            }),
            timeout=180
        )
        if result and "tasks" in result:
            return result["tasks"]
        return []
    except asyncio.TimeoutError:
        print(f"Timeout generating {difficulty} task for {theme}")
        return []
    except Exception as e:
        print(f"Error generating {difficulty} task for {theme}: {e}")
        return []

async def main():
    themes = [
        "Equity Research & Valuation",
        "Macro Strategy & Forex",
        "Portfolio Risk & Sector Rotation",
        "Crypto & Alternative Assets",
        "Event-Driven & Policy Analysis",
        "Fixed Income & Credit Analysis",
        "Commodities & Supply Chain",
        "ESG & Sustainable Investing",
        "Quantitative Factors & Technicals",
        "Global Banking & Fintech"
    ]
    
    output_path = "src/benchmarks/tasks/complex_tasks_300_unique.json"
    all_tasks = []
    
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_tasks = data.get("tasks", [])
                print(f"Resuming from {len(all_tasks)} existing tasks.")
        except:
            pass

    start_idx = len(all_tasks) + 1
    
    for theme_idx, theme in enumerate(themes):
        # Each theme needs 10 Easy, 10 Medium, 10 Hard
        theme_start_idx = theme_idx * 30 + 1
        if start_idx > theme_start_idx + 29:
            continue
            
        for difficulty in ["easy", "medium", "hard"]:
            # Check how many we already have for this difficulty in this theme
            existing_diff_tasks = [t for t in all_tasks if t.get("difficulty") == difficulty and (all_tasks.index(t) // 30 == theme_idx)]
            needed = 10 - len(existing_diff_tasks)
            
            if needed <= 0:
                continue
                
            print(f"Generating 10 {difficulty} tasks for {theme}...")
            
            # Generate one by one for maximum reliability
            for i in range(needed):
                print(f"Theme: {theme}, Difficulty: {difficulty}, Progress: {i+1}/10")
                batch = await generate_task(theme, difficulty, start_idx, 1)
                
                if batch:
                    for t in batch:
                        t["task_id"] = f"T{start_idx:03d}"
                        t["difficulty"] = difficulty
                        all_tasks.append(t)
                        start_idx += 1
                    
                    # Save progress every task
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump({"tasks": all_tasks}, f, indent=2, ensure_ascii=False)
                    print(f"Saved progress: {len(all_tasks)}/300 tasks.")
                else:
                    print(f"Failed to generate {difficulty} task {i+1} for {theme}. Skipping...")
                
                await asyncio.sleep(1)
        
    print(f"Successfully generated {len(all_tasks)} unique tasks and saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
