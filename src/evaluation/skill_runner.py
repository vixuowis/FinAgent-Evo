import asyncio
import json
import os
import argparse
from typing import List, Dict, Any, Optional
from src.agent import invoke_skill, skill_library, evolution_engine, memory, model

async def run_skill_test(test_case: Dict[str, Any], library_path: Optional[str] = None) -> Dict[str, Any]:
    skill_id = test_case["skill_id"]
    input_data = test_case["input_snapshot"]
    expected_keys = test_case["expected_keys"]
    
    # Reload library if specified
    if library_path:
        skill_library.load_from_json(library_path)
    
    print(f"  [Skill: {skill_id}] [Library: {library_path or 'current'}] Running...")
    
    task_input = f"Using the data: {json.dumps(input_data)}, please {test_case['description']} and return a JSON object."
    
    try:
        result = await invoke_skill(skill_id, task_input)
        
        # Schema validation
        schema_passed = False
        try:
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                schema_passed = all(k in data for k in expected_keys)
            else:
                data = {}
        except Exception:
            data = {}
            
        return {
            "test_id": test_case["id"],
            "skill_id": skill_id,
            "library_path": library_path,
            "output": result,
            "parsed_json": data,
            "schema_passed": schema_passed,
            "success": schema_passed
        }
    except Exception as e:
        return {
            "test_id": test_case["id"],
            "skill_id": skill_id,
            "library_path": library_path,
            "error": str(e),
            "success": False
        }

async def run_memory_test(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test memory recurrence. 
    1. Run Task A (triggers failure/memory update).
    2. Run Task B (check if memory avoids same failure).
    """
    from src.agent import run_multi_skill_orchestrator_with_logs, memory
    
    print(f"  [Memory: {test_case['id']}] Running recurrence test...")
    
    # Reset memory for a clean start
    memory.clear()
    
    task_a = test_case["tasks"][0]["description"]
    task_b = test_case["tasks"][1]["description"]
    
    # 1. Run Task A
    os.environ["FINAGENT_DISABLE_MEMORY"] = "0"
    res_a = await run_multi_skill_orchestrator_with_logs(task_a)
    
    rules_after_a = memory.get_procedural_rules()
    
    # 2. Run Task B
    res_b = await run_multi_skill_orchestrator_with_logs(task_b)
    
    # Simple heuristic: if Task B succeeded and used memory rules
    memory_used = any(rule.content in str(res_b.get("execution_logs", [])) for rule in rules_after_a)
    
    return {
        "test_id": test_case["id"],
        "task_a_success": res_a.get("success"),
        "task_b_success": res_b.get("success"),
        "rules_extracted": [r.content for r in rules_after_a],
        "memory_used_in_b": memory_used,
        "success": res_b.get("success")
    }

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evo_input", default="src/benchmarks/skill_unit/evo_samples.json")
    parser.add_argument("--memory_input", default="src/benchmarks/skill_unit/memory_samples.json")
    parser.add_argument("--static_library", default="src/data/initial_skill_library.json")
    parser.add_argument("--output_dir", default="src/benchmarks/results/skill_eval/")
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Evolution tests
    all_results = {"evolution": [], "memory": []}
    
    if os.path.exists(args.evo_input):
        with open(args.evo_input, "r") as f:
            evo_tests = json.load(f)
            
        print("--- Evolution Tests ---")
        for test in evo_tests:
            # Static
            if os.path.exists(args.static_library):
                res_s = await run_skill_test(test, library_path=args.static_library)
                all_results["evolution"].append(res_s)
            
            # Current (Evolved)
            res_e = await run_skill_test(test, library_path=None)
            all_results["evolution"].append(res_e)
            
    # Memory tests
    if os.path.exists(args.memory_input):
        with open(args.memory_input, "r") as f:
            mem_tests = json.load(f)
            
        print("\n--- Memory Recurrence Tests ---")
        for test in mem_tests:
            res_m = await run_memory_test(test)
            all_results["memory"].append(res_m)
        
    output_path = os.path.join(args.output_dir, "skill_results.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
        
    print(f"\nResults saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
