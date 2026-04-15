import json
import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

load_dotenv()

llm = ChatOpenAI(
    api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url=os.environ.get("DASHSCOPE_BASE_URL"),
    model=os.environ.get("DASHSCOPE_MODEL")
)

class EvaluationResult(BaseModel):
    score: int = Field(description="Score out of 100")
    reasoning: str = Field(description="Reasoning for the score, comparing the trajectory against criteria")
    met_metrics: list[str] = Field(description="List of criteria metrics that were met")
    missed_metrics: list[str] = Field(description="List of criteria metrics that were missed")

parser = JsonOutputParser(pydantic_object=EvaluationResult)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert financial evaluator assessing an AI agent's performance.
You will be provided with:
1. The Task Query
2. The Agent's Final Answer
3. The Agent's Execution Trajectory (Tool calls made)
4. The Evaluation Criteria

You need to evaluate:
- Did the final answer include all required metrics (final_answer_metrics)?
- Did the trajectory show the agent using tools reasonably to fetch data instead of making it up?
- Note: The agent only had 'tavily_search_results_json' and 'calculator' tools. So the 'must_call_sequence' might not map directly to specific API tools, but check if the *intent* of the sequence was followed (e.g. search -> calculate).

Output a JSON matching the schema.
"""),
    ("human", """Task Query:
{query}

Evaluation Criteria:
{criteria}

Agent Final Answer:
{final_answer}

Agent Trajectory:
{trajectory}

{format_instructions}
""")
])

async def main():
    with open("benchmarks/complex_tasks_real_api.json", "r", encoding="utf-8") as f:
        tasks = json.load(f)["tasks"]
        
    try:
        with open("benchmarks/finagent_real_api_results_merged.json", "r", encoding="utf-8") as f:
            results = json.load(f)["results"]
    except FileNotFoundError:
        print("Results file not found. Run the baseline first.")
        return
        
    evaluations = []
    total_score = 0
    
    print(f"Evaluating {len(results)} results...")
    chain = prompt | llm | parser
    
    for task, res in zip(tasks, results):
        if task["task_id"] != res["task_id"]:
            print("Task ID mismatch!")
            continue
            
        print(f"Evaluating Task {task['task_id']}...")
        
        try:
            eval_res = await chain.ainvoke({
                "query": task["query"],
                "criteria": json.dumps(task["evaluation_criteria"], ensure_ascii=False),
                "final_answer": res["final_answer"],
                "trajectory": json.dumps(res["trajectory"], ensure_ascii=False),
                "format_instructions": parser.get_format_instructions()
            })
            
            eval_res["task_id"] = task["task_id"]
            evaluations.append(eval_res)
            total_score += eval_res["score"]
            print(f"  -> Score: {eval_res['score']}/100")
            
        except Exception as e:
            print(f"  -> Error: {e}")
            
    avg_score = total_score / len(evaluations) if evaluations else 0
    print(f"\\nAverage Score: {avg_score:.2f}/100")
    
    with open("benchmarks/finagent_real_api_eval.json", "w", encoding="utf-8") as f:
        json.dump({
            "average_score": avg_score,
            "evaluations": evaluations
        }, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())