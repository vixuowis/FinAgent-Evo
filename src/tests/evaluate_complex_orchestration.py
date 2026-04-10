import asyncio
import json
import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.agent import agent, multi_skill_orchestrator

load_dotenv()

# Evaluation Model (Judge)
judge_model = ChatOpenAI(
    model="glm-5",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://coding.dashscope.aliyuncs.com/v1",
)

async def evaluate_with_judge(task, agent_response):
    judge_prompt = f"""
    You are an Expert Financial Auditor. Evaluate the performance of an AI Agent on a complex multi-skill orchestration task.
    
    ### Task Description:
    {task['task']}
    
    ### Required Skills:
    {', '.join(task['required_skills'])}
    
    ### Agent Response:
    {agent_response}
    
    ### Evaluation Criteria:
    {chr(10).join(['- ' + c for c in task['evaluation_criteria']])}
    
    Please rate the agent on a scale of 0-10 for the following categories:
    1. **Orchestration Accuracy**: Did it call the right skills in the right order?
    2. **Analytical Depth**: Is the analysis detailed and data-driven?
    3. **Decision Soundness**: Is the final recommendation justified by the findings?
    
    Provide your response as JSON: {{"scores": {{"orchestration": 8, "depth": 7, "decision": 9}}, "reasoning": "..."}}
    """
    
    try:
        response = await judge_model.ainvoke([SystemMessage(content="You are a strict financial judge."), HumanMessage(content=judge_prompt)])
        import re
        json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return {"error": "Failed to parse judge response"}
    except Exception as e:
        return {"error": str(e)}

async def main():
    with open("benchmarks/complex_tasks.json", "r") as f:
        tasks = json.load(f)
        
    results = []
    print(f"--- Starting Complex Orchestration Evaluation ({len(tasks)} tasks) ---\n")
    
    for task in tasks:
        print(f"\n[Task {task['id']}]: {task['name']}")
        print(f"Running Orchestrator...")
        
        # Use a fresh thread for each task
        config = {"configurable": {"thread_id": f"eval_{task['id']}"}}
        
        try:
            # We explicitly trigger the orchestrator via a natural language prompt to the main agent
            prompt = f"Use the multi_skill_orchestrator to solve this: {task['task']}"
            res = await agent.ainvoke({"messages": [HumanMessage(content=prompt)]}, config=config)
            agent_output = res['messages'][-1].content
            
            print("Evaluating with Judge...")
            evaluation = await evaluate_with_judge(task, agent_output)
            
            results.append({
                "task_id": task['id'],
                "name": task['name'],
                "agent_output": agent_output,
                "evaluation": evaluation
            })
            
            if "scores" in evaluation:
                avg_score = sum(evaluation['scores'].values()) / len(evaluation['scores'])
                print(f"Average Score: {avg_score:.1f}/10")
            else:
                print(f"Evaluation Error: {evaluation.get('error')}")
                
        except Exception as e:
            print(f"Error executing task: {str(e)}")
            
    # Save results
    os.makedirs("benchmarks/results", exist_ok=True)
    with open("benchmarks/results/complex_eval_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"\nEvaluation complete. Results saved to benchmarks/results/complex_eval_results.json")

if __name__ == "__main__":
    asyncio.run(main())
