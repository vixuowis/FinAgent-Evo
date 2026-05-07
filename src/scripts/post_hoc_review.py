import json
import asyncio
import os
import re
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def call_llm(prompt: str, system_message: str = "You are a helpful assistant.", config: Dict = None) -> str:
    """
    Helper to call LLM using ChatOpenAI.
    """
    api_key = config.get("api_key") or os.getenv("UNIFY_API_KEY")
    base_url = config.get("base_url") or os.getenv("UNIFY_BASE_URL") or "https://apicn.unifyllm.top/v1"
    model_name = config.get("model") or os.getenv("AGENT_MODEL") or "qwen3.6-plus"
    
    llm = ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=0.0, # Use 0 for deterministic review
        timeout=300,
        max_retries=3
    )
    
    response = await llm.ainvoke([
        SystemMessage(content=system_message),
        HumanMessage(content=prompt)
    ])
    return response.content

async def review_and_revise(task: str, criteria: Dict, trajectory: List, initial_ans: str, task_id: str = "Unknown", config: Dict = None) -> str:
    """
    Post-hoc review and revise logic (V2 Zero-Tolerance Auditor).
    """
    # 1. Prepare evidence
    evidence_json = json.dumps(trajectory, ensure_ascii=False)
    if len(evidence_json) > 15000:
        evidence_json = evidence_json[:15000] + "\n...[truncated]..."

    # 2. Review (Strict Audit)
    review_prompt = (
        "### 金融分析审计指令 (V2 零容忍模式)\n\n"
        "你是一名极度严苛的金融审计员。你的任务是根据 execution_logs（唯一事实来源）审阅 Draft Answer。\n\n"
        "**审计准则：**\n"
        "1. **证据为王**：任何出现在答案中的具体数字、日期、百分比，必须在 execution_logs 的工具输出中找到精确对应。若找不到，标记为【编造】。\n"
        "2. **识别占位符**：若工具返回 'illustrative', 'placeholder', 'N/A', 或 Python 报错，则该工具未提供有效数据。任何基于此生成的数字均为【编造】。\n"
        "3. **逻辑闭环**：如果 execution_logs 显示某项工具调用失败，答案中不得出现该工具理应返回的数据。\n\n"
        f"**Task Query:** {task}\n\n"
        f"**Execution Logs (Facts):** {evidence_json}\n\n"
        f"**Draft Answer to Audit:** {initial_ans}\n\n"
        "**请输出审计报告：**\n"
        "| 答案中的事实/数字 | 轨迹证据来源 (Step #) | 验证状态 (Verified/Fabricated) |\n"
        "| :--- | :--- | :--- |\n"
        "汇总：1. 必须删除的数字；2. 必须更正的结论。"
    )
    
    try:
        print(f"[{task_id}] Calling auditor...")
        review_text = await call_llm(review_prompt, "You are a Zero-Tolerance Financial Auditor.", config)
        print(f"[{task_id}] Auditor responded.")
    except Exception as e:
        logger.error(f"Review failed: {e}")
        return initial_ans

    # 3. Revise (Purge and Ground)
    revise_prompt = (
        "### 答案重写指令\n\n"
        "请根据审计报告重写金融分析报告。你的目标是确保 100% 的数值保真度。\n\n"
        "**重写要求：**\n"
        "1. **物理剔除**：将审计报告中标记为【编造】或【无法追溯】的数字全部删除。如果是核心指标，请写‘未能通过工具获取’。\n"
        "2. **严禁引用常识**：即使你（LLM）知道某个宏观数据或股价，只要轨迹中没有，就不准写。\n"
        "3. **结论对齐**：如果关键数据缺失导致无法得出确定性结论（如 DCF），请改为描述‘由于数据不全，无法完成精确估值，仅提供方法论框架’。\n"
        "4. **格式要求**：保持专业分析师风格，但优先保证数据的真实性。\n\n"
        f"**Auditor Critique:** {review_text}\n\n"
        f"**Execution Logs:** {evidence_json}\n\n"
        f"**Original Answer:** {initial_ans}\n"
    )
    
    try:
        print(f"[{task_id}] Calling reviser...")
        revised_ans = await call_llm(revise_prompt, "Maximize fidelity. Ground everything in logs.", config)
        print(f"[{task_id}] Reviser responded.")
        return revised_ans
    except Exception as e:
        logger.error(f"Revise failed: {e}")
        return initial_ans

async def process_task(semaphore, r, i, total, config, output_run_path, run_data_lock):
    async with semaphore:
        task_id = r.get("task_id")
        
        # In V2 mode, we don't skip to ensure all results use the strict gpt-5.4 auditor
        task_query = r.get("query")
        criteria = r.get("evaluation_criteria", {})
        trajectory = r.get("agent", {}).get("trajectory", [])
        initial_ans = r.get("agent", {}).get("final_answer", "")
        
        if not initial_ans or not trajectory:
            print(f"[{i+1}/{total}] Skipping {task_id}: No answer or trajectory")
            return

        print(f"[{i+1}/{total}] Reviewing {task_id}...")
        
        # Run review & revise
        revised_ans = await review_and_revise(task_query, criteria, trajectory, initial_ans, task_id, config)
        
        # Update results with a lock to prevent concurrent write issues to the dict
        async with run_data_lock:
            r["agent"]["final_answer_original"] = initial_ans
            r["agent"]["final_answer"] = revised_ans
            
            # Save progress immediately
            with open(output_run_path, 'w') as f:
                json.dump(GLOBAL_RUN_DATA, f, indent=2, ensure_ascii=False)
        
        print(f"[{i+1}/{total}] Finished and Saved {task_id}")

GLOBAL_RUN_DATA = {}

async def main():
    global GLOBAL_RUN_DATA
    input_run_path = 'src/benchmarks/results/n100_full_run/1776708903_full/run.json'
    output_run_path = 'src/benchmarks/results/n100_full_run/1776708903_full/run_reviewed_v2.json'
    
    # Load original data
    print(f"Loading data from {input_run_path}")
    
    with open(input_run_path, 'r') as f:
        GLOBAL_RUN_DATA = json.load(f)

    results = GLOBAL_RUN_DATA.get("results", [])
    total = len(results)
    
    config = {
        "api_key": os.getenv("UNIFY_API_KEY"),
        "base_url": os.getenv("UNIFY_BASE_URL") or "https://apicn.unifyllm.top/v1",
        "model": "claude-opus-4-6" # Use claude-opus-4-6 for speed and context
    }

    print(f"Starting V2 post-hoc review (Zero-Tolerance) for {total} tasks...")
    
    semaphore = asyncio.Semaphore(3) # Use 3 to be safe on Unify while maintaining speed
    run_data_lock = asyncio.Lock()
    tasks = []
    for i, r in enumerate(results): # Run all 100 tasks
        # Force re-review for V2
        tasks.append(process_task(semaphore, r, i, total, config, output_run_path, run_data_lock))
    
    await asyncio.gather(*tasks)
    
    print(f"All done! Final file saved to {output_run_path}")

if __name__ == "__main__":
    asyncio.run(main())
