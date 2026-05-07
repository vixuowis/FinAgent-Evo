import asyncio
import json
import os
from src.scripts.post_hoc_review import review_and_revise
from dotenv import load_dotenv

load_dotenv()

async def test_t01():
    input_run_path = 'src/benchmarks/results/n100_full_run/1776708903_full/run.json'
    with open(input_run_path, 'r') as f:
        data = json.load(f)
    
    # Get T01
    t01 = next(r for r in data['results'] if r['task_id'] == 'T01')
    
    task_query = t01['query']
    criteria = t01['evaluation_criteria']
    trajectory = t01['agent']['trajectory']
    initial_ans = t01['agent']['final_answer']
    
    config = {
        "model": "claude-opus-4-6"
    }
    
    print("--- Original Answer ---")
    print(initial_ans)
    print("\n--- Running Review & Revise ---")
    
    # We need to see the intermediate review_text. 
    # Let's modify post_hoc_review.py temporarily to print it or just copy the logic here.
    from src.scripts.post_hoc_review import call_llm
    
    evidence_json = json.dumps(trajectory, ensure_ascii=False)
    review_prompt = (
        "### 金融分析审计指令 (V2 零容忍模式)\n\n"
        "你是一名极度严苛的金融审计员。你的任务是根据 execution_logs（唯一事实来源）审阅 Draft Answer。\n\n"
        "**审计准则：**\n"
        "1. **证据为王**：任何出现在答案中的具体数字、日期、百分比，必须在 execution_logs 的工具输出中找到精确对应。若找不到，标记为【编造】。\n"
        "2. **识别占位符**：若工具返回 'illustrative', 'placeholder', 'N/A', 或 Python 报错，则该工具未提供有效数据。任何基于此生成的数字均为【编造】。\n"
        "3. **逻辑闭环**：如果 execution_logs 显示某项工具调用失败，答案中不得出现该工具理应返回的数据。\n\n"
        f"**Task Query:** {task_query}\n\n"
        f"**Execution Logs (Facts):** {evidence_json}\n\n"
        f"**Draft Answer to Audit:** {initial_ans}\n\n"
        "**请输出审计报告：**\n"
        "| 答案中的事实/数字 | 轨迹证据来源 (Step #) | 验证状态 (Verified/Fabricated) |\n"
        "| :--- | :--- | :--- |\n"
        "汇总：1. 必须删除的数字；2. 必须更正的结论。"
    )
    
    review_text = await call_llm(review_prompt, "You are a Zero-Tolerance Financial Auditor.", config)
    print("\n--- Auditor Report ---")
    print(review_text)
    
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
    
    revised_ans = await call_llm(revise_prompt, "Maximize fidelity. Ground everything in logs.", config)
    print("\n--- Revised Answer ---")
    print(revised_ans)

if __name__ == "__main__":
    asyncio.run(test_t01())
