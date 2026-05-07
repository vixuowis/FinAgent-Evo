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
    must_call_sequence: List[List[str]] = Field(description="Required sequences of tool calls, e.g. [['get_stock_price', 'calculator']]")

class Task(BaseModel):
    task_id: str = Field(description="Unique ID for the task")
    query: str = Field(description="The complex financial task prompt for the agent")
    difficulty: str = Field(description="Difficulty level: 'medium' or 'hard'")
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

Constraints for the generated tasks:
1. Each task MUST require AT LEAST 3 tool calls.
2. The tools MUST be dependent on each other (e.g., fetch stock A's price, fetch stock B's price, then calculate ratio; or fetch news, extract entity, then fetch its financials).
3. The query should be realistic, like a query from a hedge fund manager or equity researcher.
4. Provide the queries in Chinese.
5. Output must be in JSON format matching the schema.
6. The theme for this batch is: {theme}.
7. Difficulty distribution: {num_hard} Hard tasks, {num_medium} Medium tasks."""),
    ("human", "Please generate {total_tasks} complex financial tasks for the benchmark starting from task ID {start_id}.\n\n{format_instructions}")
])

async def generate_batch(theme, num_hard, num_medium, start_idx):
    chain = prompt | llm | parser
    total = num_hard + num_medium
    print(f"Generating {total} tasks for theme: {theme}...")
    
    try:
        result = await chain.ainvoke({
            "theme": theme,
            "num_hard": num_hard,
            "num_medium": num_medium,
            "total_tasks": total,
            "start_id": f"T{start_idx:03d}",
            "format_instructions": parser.get_format_instructions()
        })
        if result is None:
            print(f"LLM returned None for {theme}")
            return []
        return result.get("tasks", [])
    except Exception as e:
        print(f"Error generating batch for {theme}: {e}")
        # If it's a parsing error, try to get the raw response if possible
        # Langchain doesn't easily expose raw response in the middle of a chain
        # but we can try to use a simpler chain to debug if needed.
        return []

async def main():
    themes = [
        ("Equity Research & Valuation", 11, 9),
        ("Macro Strategy & Forex", 11, 9),
        ("Portfolio Risk & Sector Rotation", 11, 9),
        ("Crypto & Alternative Assets", 11, 9),
        ("Event-Driven & Policy Analysis", 11, 9)
    ]
    
    output_path = "src/benchmarks/tasks/complex_tasks_100_unique.json"
    all_tasks = []
    
    # Try to load existing tasks if resuming
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_tasks = data.get("tasks", [])
                print(f"Resuming from {len(all_tasks)} existing tasks.")
        except:
            pass

    start_idx = len(all_tasks) + 1
    
    for theme, total_hard, total_medium in themes:
        # Check if we already have tasks for this theme (approximate check)
        # We need 20 tasks per theme.
        theme_tasks_needed = 20
        # This is a bit simplistic, but since we are running from scratch mostly:
        current_theme_idx = (start_idx - 1) // 20
        if themes.index((theme, total_hard, total_medium)) < current_theme_idx:
            continue
            
        # Split 20 tasks into twenty batches of 1 to be extremely safe
        batches = [(1, 0) if i < 11 else (0, 1) for i in range(20)]
        
        for n_hard, n_medium in batches:
            if start_idx > 100: break
            
            print(f"Task {start_idx}/100 for {theme}: {'Hard' if n_hard else 'Medium'}")
            batch = await generate_batch(theme, n_hard, n_medium, start_idx)
            if not batch:
                print(f"Failed to generate batch for {theme}. Retrying once...")
                await asyncio.sleep(5)
                batch = await generate_batch(theme, n_hard, n_medium, start_idx)
            
            if batch:
                # Fix IDs
                for i, t in enumerate(batch):
                    t["task_id"] = f"T{start_idx + i:03d}"
                
                all_tasks.extend(batch)
                start_idx += len(batch)
                
                # Save progress
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump({"tasks": all_tasks}, f, indent=2, ensure_ascii=False)
                print(f"Saved progress: {len(all_tasks)}/100 tasks.")
            
            await asyncio.sleep(2)
        
    print(f"Successfully generated {len(all_tasks)} unique tasks and saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
