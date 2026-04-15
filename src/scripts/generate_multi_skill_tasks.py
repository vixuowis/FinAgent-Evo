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
    model=os.environ.get("DASHSCOPE_MODEL")
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

Available QVeris Tool Categories/Names you can assume:
- `get_stock_price`: Get real-time or historical stock prices.
- `get_financial_statements`: Get income statements, balance sheets, cash flow.
- `get_exchange_rate`: Real-time forex rates.
- `get_macro_data`: Interest rates, CPI, GDP.
- `search_financial_news`: Get recent news for a specific entity.
- `calculator`: Perform math calculations.
- `calculate_dcf`: Calculate Discounted Cash Flow.
- `get_crypto_price`: Get cryptocurrency prices.

Constraints for the generated tasks:
1. Each task MUST require AT LEAST 3 tool calls.
2. The tools MUST be dependent on each other (e.g., fetch stock A's price, fetch stock B's price, then calculate ratio; or fetch news, extract entity, then fetch its financials).
3. The query should be realistic, like a query from a hedge fund manager or equity researcher.
4. Provide the queries in Chinese.
5. Output must be in JSON format matching the schema.
"""),
    ("human", "Please generate {num_tasks} complex financial tasks for the benchmark.\n\n{format_instructions}")
])

async def main():
    chain = prompt | llm | parser
    print(f"Generating tasks using {os.environ.get('DASHSCOPE_MODEL')}...")
    
    try:
        result = await chain.ainvoke({
            "num_tasks": 20,
            "format_instructions": parser.get_format_instructions()
        })
        
        output_path = "benchmarks/complex_tasks_real_api.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
        print(f"Successfully generated {len(result['tasks'])} tasks and saved to {output_path}")
    except Exception as e:
        print(f"Error generating tasks: {e}")

if __name__ == "__main__":
    asyncio.run(main())