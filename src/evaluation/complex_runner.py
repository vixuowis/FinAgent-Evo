import argparse
import asyncio
import importlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from src.core.qveris_cache import get_qveris_cache
from src.evaluation.judge import create_judge_configs, run_judge
from src.evaluation.utils import percentile, safe_json_dumps, sha256_text, utc_now_iso

load_dotenv()


SCHEMA_VERSION = "neurips_eval.v2"


@dataclass
class Variant:
    name: str
    disable_evolution: bool = False
    disable_memory: bool = False
    disable_orchestration: bool = False
    plan_only: bool = False
    sop_baseline: bool = False
    review_revise_baseline: bool = False
    react_baseline: bool = False
    finagent_dvampire: bool = False
    finmem: bool = False
    fault_injection: bool = False
    recursion_limit: Optional[int] = None


def _bool_env(name: str) -> bool:
    return os.getenv(name, "").strip() in {"1", "true", "True", "yes", "YES"}


def llm_key_present() -> bool:
    provider = os.getenv("LLM_PROVIDER", "dashscope").strip().lower()
    if provider == "maas":
        return bool(os.getenv("MAAS_API_KEY", "").strip())
    key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    return bool(key and key != "dummy")


def load_tasks(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, dict) and "tasks" in obj:
        return obj["tasks"]
    if isinstance(obj, list):
        return obj
    raise ValueError(f"Unsupported benchmark format: {path}")


def _extract_tool_trajectory(messages: List[Any]) -> Tuple[List[Dict[str, Any]], str]:
    trajectory: List[Dict[str, Any]] = []
    final_answer = ""
    tool_outputs_by_id: Dict[str, str] = {}

    for msg in messages:
        msg_type = getattr(msg, "type", None)
        if msg_type == "tool":
            tool_call_id = getattr(msg, "tool_call_id", None)
            content = getattr(msg, "content", None)
            if tool_call_id and content is not None:
                tool_outputs_by_id[tool_call_id] = str(content)

    for msg in messages:
        if getattr(msg, "type", None) != "ai":
            continue
        tool_calls = getattr(msg, "tool_calls", None) or []
        if tool_calls:
            for tc in tool_calls:
                tc_id = tc.get("id")
                out = tool_outputs_by_id.get(tc_id)
                trajectory.append(
                    {
                        "tool": tc.get("name"),
                        "input": tc.get("args"),
                        "output": (out[:4000] if isinstance(out, str) else out),
                    }
                )
        if getattr(msg, "content", None):
            final_answer = msg.content

    return trajectory, final_answer


def _set_variant_env(v: Variant) -> None:
    os.environ["FINAGENT_DISABLE_EVOLUTION"] = "1" if v.disable_evolution else "0"
    os.environ["FINAGENT_DISABLE_MEMORY"] = "1" if v.disable_memory else "0"
    os.environ["FINAGENT_DISABLE_ORCHESTRATION"] = "1" if v.disable_orchestration else "0"
    os.environ["FINAGENT_PLAN_ONLY"] = "1" if v.plan_only else "0"
    os.environ["FINAGENT_FREEZE_STATE"] = "1" # Evaluation 期间默认冻结状态更新
    os.environ["FINAGENT_SOP_BASELINE"] = "1" if v.sop_baseline else "0"
    os.environ["FINAGENT_REVIEW_REVISE_BASELINE"] = "1" if v.review_revise_baseline else "0"
    os.environ["FINAGENT_FAULT_INJECTION"] = "1" if v.fault_injection else "0"


def _load_agent_module(v: Variant):
    _set_variant_env(v)
    mod = importlib.import_module("src.agent")
    return importlib.reload(mod)


def _create_react_baseline_agent(agent_mod):
    from deepagents import create_deep_agent

    tools = [
        agent_mod.tavily_search,
        agent_mod.search_financial_news,
        agent_mod.get_stock_price,
        agent_mod.get_financial_statements,
        agent_mod.get_exchange_rate,
        agent_mod.get_macro_data,
        agent_mod.get_crypto_price,
        agent_mod.python_interpreter,
        agent_mod.calculator,
        agent_mod.calculate_dcf,
    ]
    return create_deep_agent(
        model=agent_mod.model,
        tools=tools,
        system_prompt="你是金融研究助手。必须用工具获取数据与进行计算；禁止编造数值。",
    )


def _extract_token_usage(meta: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(meta, dict):
        return None
    tu = meta.get("token_usage")
    if isinstance(tu, dict):
        return {
            "prompt_tokens": tu.get("prompt_tokens"),
            "completion_tokens": tu.get("completion_tokens"),
            "total_tokens": tu.get("total_tokens"),
        }
    return None


def _compute_run_summary(results: List[Dict[str, Any]], judge_enabled: bool) -> Dict[str, Any]:
    elapsed_all = [
        x.get("run", {}).get("elapsed_s")
        for x in results
        if isinstance(x.get("run", {}).get("elapsed_s"), (int, float))
    ]
    tool_calls_all = [
        x.get("metrics", {}).get("tool_calls")
        for x in results
        if isinstance(x.get("metrics", {}).get("tool_calls"), int)
    ]
    cost_all = [
        x.get("metrics", {}).get("llm_cost_estimate_usd")
        for x in results
        if isinstance(x.get("metrics", {}).get("llm_cost_estimate_usd"), (int, float))
    ]

    hard_success_count = sum(1 for x in results if x.get("derived", {}).get("hard_success"))
    judge_success_count = sum(1 for x in results if x.get("derived", {}).get("judge_success"))

    avg_score = 0.0
    judge_scores_by_model: Dict[str, float] = {}
    if judge_enabled:
        scores: List[float] = []
        score_buckets: Dict[str, List[float]] = {}
        for x in results:
            sc = (
                x.get("judge", {}).get("parsed_agg", {}).get("score")
                if isinstance(x.get("judge", {}).get("parsed_agg"), dict)
                else x.get("judge", {}).get("parsed", {}).get("score")
            )
            if isinstance(sc, (int, float)):
                scores.append(float(sc))
            items = x.get("judge", {}).get("items")
            if isinstance(items, list):
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    model = str(it.get("model") or it.get("name") or "unknown")
                    p = it.get("parsed") if isinstance(it.get("parsed"), dict) else {}
                    s2 = p.get("score")
                    if isinstance(s2, (int, float)):
                        score_buckets.setdefault(model, []).append(float(s2))
        avg_score = (sum(scores) / len(scores)) if scores else 0.0
        judge_scores_by_model = {
            k: (sum(v) / len(v)) for k, v in sorted(score_buckets.items()) if v
        }

    failure_modes: Dict[str, int] = {}
    for x in results:
        fm = x.get("run", {}).get("failure_mode")
        if fm:
            failure_modes[fm] = failure_modes.get(fm, 0) + 1

    return {
        "task_count": len(results),
        "hard_success_count": hard_success_count,
        "judge_success_count": judge_success_count,
        "hard_success_rate": (hard_success_count / len(results)) if results else 0.0,
        "judge_success_rate": (judge_success_count / len(results)) if results else 0.0,
        "avg_score": avg_score,
        "judge_scores_by_model": judge_scores_by_model,
        "elapsed_s_avg": (sum(elapsed_all) / len(elapsed_all)) if elapsed_all else None,
        "elapsed_s_p50": percentile(elapsed_all, 50),
        "elapsed_s_p90": percentile(elapsed_all, 90),
        "tool_calls_avg": (sum(tool_calls_all) / len(tool_calls_all)) if tool_calls_all else None,
        "llm_cost_estimate_usd_total": (sum(cost_all) if cost_all else None),
        "failure_modes": dict(sorted(failure_modes.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def _load_existing_from_judge_logs(
    judge_logs_path: str, judge_success_threshold: float
) -> Tuple[List[Dict[str, Any]], Set[Tuple[str, int]], int, Optional[str], Optional[str]]:
    """
    从已有 judge_logs.jsonl 重建最小可用的 results，用于断点续跑：
    - 跳过已完成 task_id/trial_idx
    - 续跑结束后仍能产出完整 run.json（即使中断时没有保存 run.json）
    """
    if not os.path.exists(judge_logs_path):
        return [], set(), 0, None, None

    results_by_key: Dict[Tuple[str, int], Dict[str, Any]] = {}
    done: Set[Tuple[str, int]] = set()
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    judge_lines = 0

    with open(judge_logs_path, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            judge_lines = idx + 1
            try:
                obj = json.loads(line)
            except Exception:
                continue

            task_id = obj.get("task_id") or "unknown"
            trial_idx = int(obj.get("trial_idx") or 0)
            done.add((task_id, trial_idx))

            logged_at = obj.get("logged_at")
            if isinstance(logged_at, str):
                if started_at is None:
                    started_at = logged_at
                ended_at = logged_at

            parsed = obj.get("judge_parsed") if isinstance(obj.get("judge_parsed"), dict) else {}
            score = parsed.get("score", 0) if isinstance(parsed, dict) else 0
            fabrication_detected = parsed.get("fabrication_detected", False) if isinstance(parsed, dict) else False

            judge_input = obj.get("judge_input") if isinstance(obj.get("judge_input"), dict) else {}
            query = judge_input.get("query") if isinstance(judge_input, dict) else None
            trajectory = judge_input.get("trajectory") if isinstance(judge_input, dict) else None
            final_answer = judge_input.get("final_answer") if isinstance(judge_input, dict) else None
            evaluation_criteria = judge_input.get("evaluation_criteria") if isinstance(judge_input, dict) else None

            tool_calls = len(trajectory) if isinstance(trajectory, list) else 0
            hard_success = bool(final_answer) or bool(trajectory)
            judge_success = (score >= judge_success_threshold) and (not fabrication_detected)

            key = (task_id, trial_idx)
            if key not in results_by_key:
                results_by_key[key] = {
                    "task_id": task_id,
                    "query": query,
                    "difficulty": None,
                    "evaluation_criteria": evaluation_criteria,
                    "budget": {"timeout_s": None, "recursion_limit": None, "max_retries": None},
                    "run": {
                        "started_at": None,
                        "ended_at": None,
                        "elapsed_s": None,
                        "success": hard_success,
                        "failure_mode": None if hard_success else "resume_unknown",
                        "error": None,
                    },
                    "agent": {
                        "final_answer": final_answer or "",
                        "trajectory": trajectory or [],
                        "orchestrator": None,
                    },
                    "metrics": {
                        "tool_calls": tool_calls,
                        "qveris_calls_estimate": None,
                        "llm_usage": None,
                        "llm_token_usage": None,
                        "llm_cost_estimate_usd": None,
                        "qveris_cache": None,
                    },
                    "trial_idx": trial_idx,
                    "judge": {"items": [], "parsed_agg": None, "log_ref": {"path": judge_logs_path, "line": idx}},
                    "derived": {"hard_success": hard_success, "judge_success": judge_success},
                }

            results_by_key[key]["judge"]["items"].append(
                {
                    "name": obj.get("judge_name") or f"line_{idx}",
                    "model": (obj.get("judge_config") or {}).get("model"),
                    "parsed": parsed,
                    "raw_text": obj.get("judge_raw_text"),
                    "parse_error": obj.get("judge_parse_error"),
                }
            )
            # Backward-compatible single parsed slot
            results_by_key[key]["judge"]["parsed"] = parsed

    # Aggregate multi-judge lines into one result per (task_id, trial_idx)
    results: List[Dict[str, Any]] = []
    for key in sorted(results_by_key.keys()):
        r = results_by_key[key]
        items = r.get("judge", {}).get("items", [])
        scores = []
        fabrication = False
        met_set = set()
        missed_set = set()
        for it in items:
            parsed_obj = it.get("parsed") if isinstance(it.get("parsed"), dict) else {}
            sc = parsed_obj.get("score")
            reasoning = str(parsed_obj.get("reasoning", ""))
            
            # Skip failed judges in aggregation
            if "judge_error" in reasoning or "run_judge_exception" in reasoning:
                continue
                
            if isinstance(sc, (int, float)):
                scores.append(float(sc))
            fabrication = fabrication or bool(parsed_obj.get("fabrication_detected", False))
            for m in (parsed_obj.get("met_metrics") or []):
                met_set.add(str(m))
            for m in (parsed_obj.get("missed_metrics") or []):
                missed_set.add(str(m))
        agg_score = (sum(scores) / len(scores)) if scores else 0.0
        r["judge"]["parsed_agg"] = {
            "score": agg_score,
            "reasoning": "resume_ensemble_mean_score",
            "met_metrics": sorted(met_set),
            "missed_metrics": sorted(missed_set),
            "fabrication_detected": fabrication,
        }
        r["derived"]["judge_success"] = (agg_score >= judge_success_threshold) and (not fabrication)
        results.append(r)

    return results, done, judge_lines, started_at, ended_at


def _write_checkpoint_run_json(
    run_path: str,
    run_obj: Dict[str, Any],
) -> None:
    # best-effort checkpoint：避免因写文件失败影响主流程
    try:
        with open(run_path, "w", encoding="utf-8") as f:
            json.dump(run_obj, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _verify_numerical_fidelity(trajectory: List[Dict[str, Any]], final_answer: str) -> bool:
    """
    严格校验最终答案中的数值是否在轨迹工具输出中出现过（支持简单的舍入容差）。
    """
    import re
    
    def extract_numbers(text: str) -> Set[float]:
        # 匹配数字，支持逗号分隔符和百分号
        clean_text = text.replace(",", "")
        # 寻找形如 123, 123.45, 10% 的数字
        matches = re.findall(r"[-+]?\d*\.\d+|\d+", clean_text)
        nums = set()
        for m in matches:
            try:
                nums.add(round(float(m), 2))
            except ValueError:
                continue
        return nums

    if not final_answer:
        return False
        
    # 从轨迹中提取所有工具输出的数值
    tool_outputs = " ".join([str(step.get("output", "")) for step in trajectory])
    ground_truth_nums = extract_numbers(tool_outputs)
    
    # 从最终答案中提取数值
    answer_nums = extract_numbers(final_answer)
    
    # 允许一些常见的常数或小数字不校验
    ignored_nums = {0.0, 1.0, 2.0, 5.0, 10.0, 100.0}
    check_nums = answer_nums - ignored_nums
    
    if not check_nums:
        return True # 没有需要校验的数值
        
    # 检查答案中的每个数字是否在轨迹中出现过（或接近）
    found_count = 0
    for n in check_nums:
        # 简单匹配：直接存在或误差在 0.01 以内
        if any(abs(n - gt) <= 0.01 for gt in ground_truth_nums):
            found_count += 1
            
    # 如果答案中超过 20% 的数字无法在轨迹中找到来源，则视为不保真
    # (阈值可以根据实际情况调整，这里设为 80% 匹配即视为通过)
    fidelity_rate = found_count / len(check_nums) if check_nums else 1.0
    return fidelity_rate >= 0.8


async def run_single_task(task: Dict[str, Any], v: Variant, agent_mod, trial_idx: int = 0) -> Dict[str, Any]:
    started_at = utc_now_iso()
    t0 = time.time()
    failure_mode = None
    error = None
    trajectory: List[Dict[str, Any]] = []
    final_answer = ""
    orchestrator: Optional[Dict[str, Any]] = None
    
    timeout_s_str = os.getenv("FINAGENT_TASK_TIMEOUT_SECONDS", "180").strip()
    try:
        timeout_s = int(timeout_s_str)
    except Exception:
        timeout_s = 180

    recursion_limit = v.recursion_limit or int(os.getenv("REACT_RECURSION_LIMIT", "25"))
    
    # Generate a unique thread_id for this specific trial to avoid variable clobbering
    task_id = task.get("task_id") or task.get("id") or "unknown"
    thread_id = f"eval_{task_id}_trial_{trial_idx}"
    config = {"configurable": {"thread_id": thread_id}}

    if not llm_key_present():
        failure_mode = "dry_run_missing_llm_key"
    else:
        try:
            if v.react_baseline:
                baseline_agent = _create_react_baseline_agent(agent_mod)
                resp = await asyncio.wait_for(
                    baseline_agent.ainvoke(
                        {"messages": [("user", task.get("query") or task.get("task") or "")]},
                        config={**config, "recursion_limit": recursion_limit},
                    ),
                    timeout=timeout_s,
                )
                trajectory, final_answer = _extract_tool_trajectory(resp.get("messages", []))
            elif v.sop_baseline:
                orch_res = await asyncio.wait_for(
                    agent_mod.run_sop_baseline_with_logs(task.get("query") or task.get("task") or "", config=config),
                    timeout=timeout_s,
                )
                orchestrator = {
                    "execution_logs": orch_res.get("execution_logs", []),
                    "llm_usage": orch_res.get("llm_usage"),
                }
                final_answer = orch_res.get("final_answer", "")
                trajectory = orch_res.get("execution_logs", [])
            elif v.review_revise_baseline:
                orch_res = await asyncio.wait_for(
                    agent_mod.run_review_revise_baseline_with_logs(task, config=config),
                    timeout=timeout_s,
                )
                orchestrator = {
                    "execution_logs": orch_res.get("execution_logs", []),
                    "llm_usage": orch_res.get("llm_usage"),
                }
                final_answer = orch_res.get("final_answer", "")
                trajectory = orch_res.get("execution_logs", [])
            elif v.finagent_dvampire:
                orch_res = await asyncio.wait_for(
                    agent_mod.run_finagent_dvampire_style_with_logs(task.get("query") or task.get("task") or "", config=config),
                    timeout=timeout_s,
                )
                orchestrator = {
                    "execution_logs": orch_res.get("execution_logs", []),
                    "llm_usage": orch_res.get("llm_usage"),
                }
                final_answer = orch_res.get("final_answer", "")
                trajectory = orch_res.get("execution_logs", [])
            elif v.finmem:
                orch_res = await asyncio.wait_for(
                    agent_mod.run_finmem_style_with_logs(task.get("query") or task.get("task") or "", config=config),
                    timeout=timeout_s,
                )
                orchestrator = {
                    "execution_logs": orch_res.get("execution_logs", []),
                    "llm_usage": orch_res.get("llm_usage"),
                }
                final_answer = orch_res.get("final_answer", "")
                trajectory = orch_res.get("execution_logs", [])
            elif not v.disable_orchestration:
                orch_res = await asyncio.wait_for(
                    agent_mod.run_multi_skill_orchestrator_with_logs(task.get("query") or task.get("task") or "", config=config),
                    timeout=timeout_s,
                )
                orchestrator = {
                    "plan": orch_res.get("plan", []),
                    "execution_logs": orch_res.get("execution_logs", []),
                    "plan_raw": orch_res.get("plan_raw"),
                    "plan_prompt_sha256": sha256_text(orch_res.get("plan_prompt", "") or ""),
                    "llm_usage": orch_res.get("llm_usage"),
                }
                final_answer = orch_res.get("final_answer", "")
                if orch_res.get("success"):
                    trajectory = orch_res.get("execution_logs", [])
                else:
                    failure_mode = orch_res.get("failure_mode") or "execution"
                    error = orch_res.get("error")
            else:
                resp = await asyncio.wait_for(
                    agent_mod.agent.ainvoke(
                        {"messages": [HumanMessage(content=task.get("query") or task.get("task") or "")]},
                        config=config,
                    ),
                    timeout=timeout_s,
                )
                trajectory, final_answer = _extract_tool_trajectory(resp.get("messages", []))
        except asyncio.TimeoutError:
            failure_mode = failure_mode or "timeout"
            error = f"task_timeout_{timeout_s}s"
        except Exception as e:
            failure_mode = failure_mode or "execution"
            error = str(e)

    elapsed_s = time.time() - t0
    ended_at = utc_now_iso()

    tool_calls = len(trajectory) if trajectory else 0
    qveris_calls = sum(1 for x in trajectory if (x.get("tool") or x.get("skill_id", "")).startswith("get_") or "qveris" in (x.get("tool") or ""))

    cache_stats = get_qveris_cache().stats
    llm_usage = orchestrator.get("llm_usage") if orchestrator else None
    token_usage = None
    if isinstance(llm_usage, dict):
        token_usage = {
            "plan": _extract_token_usage(llm_usage.get("plan")),
            "synthesis": _extract_token_usage(llm_usage.get("synthesis")),
        }
        if token_usage["plan"] is None and token_usage["synthesis"] is None:
            token_usage = None

    cost_estimate_usd = None
    if token_usage:
        in_rate_str = os.getenv("LLM_COST_INPUT_PER_1K_USD", "").strip()
        out_rate_str = os.getenv("LLM_COST_OUTPUT_PER_1K_USD", "").strip()
        try:
            in_rate = float(in_rate_str) if in_rate_str else None
            out_rate = float(out_rate_str) if out_rate_str else None
        except Exception:
            in_rate, out_rate = None, None

        if in_rate is not None or out_rate is not None:
            prompt_tokens = 0
            completion_tokens = 0
            for phase in ["plan", "synthesis"]:
                tu = token_usage.get(phase) or {}
                prompt_tokens += int(tu.get("prompt_tokens") or 0)
                completion_tokens += int(tu.get("completion_tokens") or 0)
            cost_estimate_usd = 0.0
            if in_rate is not None:
                cost_estimate_usd += (prompt_tokens / 1000.0) * in_rate
            if out_rate is not None:
                cost_estimate_usd += (completion_tokens / 1000.0) * out_rate

    record: Dict[str, Any] = {
        "task_id": task.get("task_id") or task.get("id"),
        "query": task.get("query") or task.get("task"),
        "difficulty": task.get("difficulty"),
        "evaluation_criteria": task.get("evaluation_criteria") or task.get("evaluation_criteria", {}),
        "budget": {
            "timeout_s": timeout_s,
            "recursion_limit": recursion_limit if v.react_baseline else None,
            "max_retries": int(os.getenv("FINAGENT_MAX_RETRIES", "3")),
        },
        "run": {
            "started_at": started_at,
            "ended_at": ended_at,
            "elapsed_s": elapsed_s,
            "success": failure_mode is None and error is None,
            "failure_mode": failure_mode,
            "error": error,
        },
        "agent": {
            "final_answer": final_answer,
            "trajectory": trajectory,
            "orchestrator": orchestrator,
        },
        "metrics": {
            "tool_calls": tool_calls,
            "qveris_calls_estimate": qveris_calls,
            "llm_usage": llm_usage,
            "llm_token_usage": token_usage,
            "llm_cost_estimate_usd": cost_estimate_usd,
            "qveris_cache": {
                "enabled": cache_stats.enabled,
                "ttl_seconds": cache_stats.ttl_seconds,
                "hits": cache_stats.hits,
                "misses": cache_stats.misses,
                "writes": cache_stats.writes,
            },
        },
    }
    return record


def format_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    else:
        return f"{s}s"


async def run_benchmark(
    benchmark_path: str,
    variants: List[Variant],
    limit: Optional[int] = None,
    output_dir: str = "src/benchmarks/results",
    judge: bool = True,
    repeat: int = 1,
    judge_success_threshold: float = 70.0,
    resume_run_id: Optional[str] = None,
) -> List[str]:
    tasks = load_tasks(benchmark_path)
    if limit is not None:
        tasks = tasks[:limit]

    run_ids: List[str] = []
    for v in variants:
        agent_mod = _load_agent_module(v)
        if resume_run_id:
            run_id = resume_run_id
            if not run_id.endswith(f"_{v.name}"):
                raise ValueError(f"--resume-run-id 必须以 _{v.name} 结尾，当前: {run_id}")
        else:
            run_id = f"{int(time.time())}_{v.name}"
        run_dir = os.path.join(output_dir, run_id)
        os.makedirs(run_dir, exist_ok=True)

        judge_cfgs = create_judge_configs()
        judge_cfg_primary = judge_cfgs[0]
        judge_logs_path = os.path.join(run_dir, "judge_logs.jsonl")
        run_path = os.path.join(run_dir, "run.json")

        started_at = utc_now_iso()
        ended_at = None
        results: List[Dict[str, Any]] = []
        judge_lines = 0
        done_trials: Set[Tuple[str, int]] = set()

        if resume_run_id:
            existing_results, done_trials, judge_lines, started_at_from_logs, ended_at = _load_existing_from_judge_logs(
                judge_logs_path=judge_logs_path,
                judge_success_threshold=judge_success_threshold,
            )
            if started_at_from_logs:
                started_at = started_at_from_logs
            results = existing_results
            print(f"🔁 Resume enabled. Loaded {len(existing_results)} existing judged trials from: {judge_logs_path}")

        print(f"\n🚀 Starting variant: {v.name} (repeat={repeat}, disable_evo={v.disable_evolution}, disable_mem={v.disable_memory}, disable_orch={v.disable_orchestration}, react={v.react_baseline})")
        
        # Calculate total trials to run
        total_trials_to_run = 0
        for task in tasks:
            task_id = task.get("task_id") or task.get("id")
            for r_idx in range(repeat):
                if (task_id, r_idx) not in done_trials:
                    total_trials_to_run += 1
        
        completed_in_run = 0
        cumulative_time_in_run = 0.0

        for i, task in enumerate(tasks):
            task_id = task.get("task_id") or task.get("id")
            for r_idx in range(repeat):
                if (task_id, r_idx) in done_trials:
                    print(f"  [Variant: {v.name}] [Task {i+1}/{len(tasks)}] [Trial {r_idx+1}/{repeat}] Skipping (already done): {task_id}", flush=True)
                    continue
                
                # Progress and ETC
                remaining = total_trials_to_run - completed_in_run
                etc_text = "N/A"
                if completed_in_run > 0:
                    avg_time = cumulative_time_in_run / completed_in_run
                    etc_seconds = avg_time * remaining
                    etc_text = format_duration(etc_seconds)
                
                print(f"  [Variant: {v.name}] [Progress: {completed_in_run + 1}/{total_trials_to_run}] [Task {i+1}/{len(tasks)}] [Trial {r_idx+1}/{repeat}] Running Task: {task_id} (ETC: {etc_text})", flush=True)
                
                # Add a small jittered delay to prevent concurrent API spikes
                import random
                await asyncio.sleep(random.uniform(1.0, 5.0))
                
                r = await run_single_task(task, v, agent_mod, trial_idx=r_idx)
                r["trial_idx"] = r_idx
                
                completed_in_run += 1
                cumulative_time_in_run += r["run"]["elapsed_s"]
                
                score = 0
                fabrication_detected = False
                if judge:
                    judge_items: List[Dict[str, Any]] = []
                    for cfg in judge_cfgs:
                        try:
                            parsed, raw, parse_error, judge_input = await run_judge(
                                task=task,
                                final_answer=r["agent"]["final_answer"],
                                trajectory=r["agent"]["trajectory"],
                                cfg=cfg,
                            )
                        except Exception as e:
                            print(f"CRITICAL: run_judge failed for {cfg.name}: {str(e)}")
                            parsed = {"score": 0, "reasoning": f"run_judge_exception: {str(e)}"}
                            raw = ""
                            parse_error = str(e)
                            judge_input = {}
                        
                        judge_items.append(
                            {
                                "name": cfg.name,
                                "model": cfg.model,
                                "base_url": cfg.base_url,
                                "temperature": cfg.temperature,
                                "prompt_sha256": cfg.prompt_sha256,
                                "parsed": parsed,
                                "raw_text": raw,
                                "parse_error": parse_error,
                                "judge_input": judge_input,
                            }
                        )
                        with open(judge_logs_path, "a", encoding="utf-8") as f:
                            f.write(
                                safe_json_dumps(
                                    {
                                        "task_id": r["task_id"],
                                        "trial_idx": r_idx,
                                        "judge_name": cfg.name,
                                        "judge_config": {
                                            "model": cfg.model,
                                            "base_url": cfg.base_url,
                                            "temperature": cfg.temperature,
                                            "prompt_sha256": cfg.prompt_sha256,
                                        },
                                        "judge_input": judge_input,
                                        "judge_raw_text": raw,
                                        "judge_parsed": parsed,
                                        "judge_parse_error": parse_error,
                                        "logged_at": utc_now_iso(),
                                    }
                                )
                                + "\n"
                            )
                        judge_lines += 1

                    # Ensemble aggregation: mean score of SUCCESSFUL judges + union of missed/met + any fabrication flag.
                    valid_scores = [
                        float(it["parsed"].get("score", 0))
                        for it in judge_items
                        if isinstance(it.get("parsed"), dict) 
                        and isinstance(it["parsed"].get("score"), (int, float))
                        and "judge_error" not in str(it["parsed"].get("reasoning", ""))
                        and "run_judge_exception" not in str(it["parsed"].get("reasoning", ""))
                    ]
                    
                    if valid_scores:
                        score = sum(valid_scores) / len(valid_scores)
                    else:
                        # Fallback to the default 0 if all judges failed, but we should know it's an error
                        score = 0.0

                    fabrication_detected = any(
                        bool(it["parsed"].get("fabrication_detected", False))
                        for it in judge_items
                        if isinstance(it.get("parsed"), dict)
                    )

                    met_set = set()
                    missed_set = set()
                    for it in judge_items:
                        parsed_obj = it.get("parsed") if isinstance(it.get("parsed"), dict) else {}
                        for m in (parsed_obj.get("met_metrics") or []):
                            met_set.add(str(m))
                        for m in (parsed_obj.get("missed_metrics") or []):
                            missed_set.add(str(m))

                    parsed_agg = {
                        "score": score,
                        "reasoning": "ensemble_mean_score",
                        "met_metrics": sorted(met_set),
                        "missed_metrics": sorted(missed_set),
                        "fabrication_detected": fabrication_detected,
                    }
                    r["judge"] = {
                        "parsed_agg": parsed_agg,
                        "items": [
                            {
                                "name": it["name"],
                                "model": it["model"],
                                "parsed": it["parsed"],
                                "raw_text": it["raw_text"],
                                "parse_error": it["parse_error"],
                            }
                            for it in judge_items
                        ],
                        "log_ref": {"path": judge_logs_path, "line": judge_lines},
                    }
                
                # Derive success metrics
                fidelity_pass = _verify_numerical_fidelity(r["agent"]["trajectory"], r["agent"]["final_answer"])
                r["derived"] = {
                    "hard_success": r["run"]["success"] and fidelity_pass,
                    "judge_success": (score >= judge_success_threshold) and not fabrication_detected,
                    "fidelity_pass": fidelity_pass
                }
                
                status_icon = "✅" if r["run"]["success"] else "❌"
                judge_icon = "⭐" if r["derived"]["judge_success"] else "💀"
                judge_score_text = ""
                items = r.get("judge", {}).get("items")
                if isinstance(items, list) and items:
                    parts: List[str] = []
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        model = str(it.get("model") or it.get("name") or "judge")
                        parsed_obj = it.get("parsed") if isinstance(it.get("parsed"), dict) else {}
                        s = parsed_obj.get("score")
                        if isinstance(s, (int, float)):
                            parts.append(f"{model}={float(s):.1f}")
                    if parts:
                        judge_score_text = ", JudgeScores: [" + ", ".join(parts) + "]"
                print(
                    f"  [Variant: {v.name}] [Task {i+1}/{len(tasks)}] Trial {r_idx+1} Completed. "
                    f"Hard: {status_icon}, Judge: {judge_icon}, Score(agg): {score:.1f}{judge_score_text}, "
                    f"Time: {r['run']['elapsed_s']:.1f}s"
                )
                results.append(r)
                done_trials.add((task_id, r_idx))

                # checkpoint：每个 trial 落盘一次，保证可断点续跑
                ended_at_ckpt = utc_now_iso()
                run_obj_ckpt = {
                    "schema_version": SCHEMA_VERSION,
                    "run_id": run_id,
                    "started_at": started_at,
                    "ended_at": ended_at_ckpt,
                    "benchmark": {"path": benchmark_path, "task_count": len(tasks), "limit": limit},
                    "variant": {
                        "name": v.name,
                        "disable_evolution": v.disable_evolution,
                        "disable_memory": v.disable_memory,
                        "disable_orchestration": v.disable_orchestration,
                        "plan_only": v.plan_only,
                        "sop_baseline": v.sop_baseline,
                        "review_revise_baseline": v.review_revise_baseline,
                        "react_baseline": v.react_baseline,
                        "finagent_dvampire": v.finagent_dvampire,
                        "finmem": v.finmem,
                    },
                    "judge": {
                        "enabled": judge,
                        "models": [cfg.model for cfg in judge_cfgs],
                        "base_url": judge_cfg_primary.base_url,
                        "temperature": judge_cfg_primary.temperature,
                        "prompt_sha256": judge_cfg_primary.prompt_sha256,
                        "judge_logs_path": judge_logs_path,
                    },
                    "qveris_cache": {
                        "enabled": get_qveris_cache().stats.enabled,
                        "ttl_seconds": get_qveris_cache().stats.ttl_seconds,
                    },
                    "summary": _compute_run_summary(results, judge_enabled=judge),
                    "results": results,
                }
                _write_checkpoint_run_json(run_path, run_obj_ckpt)

        ended_at_final = utc_now_iso()
        summary = _compute_run_summary(results, judge_enabled=judge)

        print(
            f"🏁 Finished variant: {v.name}. "
            f"Hard Success: {summary['hard_success_count']}/{len(results)}, "
            f"Judge Success: {summary['judge_success_count']}/{len(results)}, "
            f"Avg Score: {summary['avg_score']:.1f}"
        )

        run_obj = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "started_at": started_at,
            "ended_at": ended_at_final,
            "benchmark": {"path": benchmark_path, "task_count": len(tasks), "limit": limit},
            "variant": {
                "name": v.name,
                "disable_evolution": v.disable_evolution,
                "disable_memory": v.disable_memory,
                "disable_orchestration": v.disable_orchestration,
                "plan_only": v.plan_only,
                "sop_baseline": v.sop_baseline,
                "review_revise_baseline": v.review_revise_baseline,
                "react_baseline": v.react_baseline,
                "finagent_dvampire": v.finagent_dvampire,
                "finmem": v.finmem,
            },
            "judge": {
                "enabled": judge,
                "models": [cfg.model for cfg in judge_cfgs],
                "base_url": judge_cfg_primary.base_url,
                "temperature": judge_cfg_primary.temperature,
                "prompt_sha256": judge_cfg_primary.prompt_sha256,
                "judge_logs_path": judge_logs_path,
            },
            "qveris_cache": {
                "enabled": get_qveris_cache().stats.enabled,
                "ttl_seconds": get_qveris_cache().stats.ttl_seconds,
            },
            "summary": summary,
            "results": results,
        }

        _write_checkpoint_run_json(run_path, run_obj)
        run_ids.append(run_id)

    return run_ids


def build_variants(names: List[str], react_recursion_limit: Optional[int] = None) -> List[Variant]:
    out: List[Variant] = []
    for name in names:
        if name == "full":
            out.append(Variant(name="full"))
        elif name in {"wo_evolution", "no_evolution"}:
            out.append(Variant(name="wo_evolution", disable_evolution=True))
        elif name in {"wo_memory", "no_memory"}:
            out.append(Variant(name="wo_memory", disable_memory=True))
        elif name in {"wo_orchestration", "no_orchestration"}:
            out.append(Variant(name="wo_orchestration", disable_orchestration=True))
        elif name in {"plan_only"}:
            out.append(Variant(name="plan_only", plan_only=True, disable_evolution=True, disable_memory=True))
        elif name in {"sop", "sop_baseline"}:
            out.append(Variant(name="sop_baseline", sop_baseline=True, disable_evolution=True, disable_memory=True, disable_orchestration=True))
        elif name in {"review_revise", "aflow_baseline"}:
            out.append(Variant(name="review_revise_baseline", review_revise_baseline=True, disable_evolution=True, disable_memory=True, disable_orchestration=True))
        elif name in {"finagent_dvampire", "dvampire"}:
            out.append(Variant(name="finagent_dvampire", finagent_dvampire=True, disable_evolution=True, disable_memory=True, disable_orchestration=True))
        elif name in {"finmem"}:
            out.append(Variant(name="finmem", finmem=True, disable_evolution=True, disable_memory=True, disable_orchestration=True))
        elif name in {"react", "react_baseline"}:
            out.append(Variant(
                name="react_baseline", 
                react_baseline=True, 
                disable_orchestration=True, 
                disable_memory=True, 
                disable_evolution=True,
                recursion_limit=react_recursion_limit
            ))
        elif name in {"fault_injection", "robustness"}:
            out.append(Variant(name="fault_injection", fault_injection=True))
        else:
            # Check if it's a sensitivity scan variant like react_limit_15
            if name.startswith("react_limit_"):
                try:
                    limit = int(name.split("_")[-1])
                    out.append(Variant(
                        name=name,
                        react_baseline=True,
                        disable_orchestration=True,
                        disable_memory=True,
                        disable_evolution=True,
                        recursion_limit=limit
                    ))
                    continue
                except ValueError:
                    pass
            raise ValueError(f"Unknown variant: {name}")
    return out


async def main():
    parser = argparse.ArgumentParser(description="NeurIPS complex benchmark runner (unified schema + judge logs).")
    parser.add_argument("--benchmark", type=str, default="src/benchmarks/tasks/complex_tasks_real_api.json")
    parser.add_argument("--variants", type=str, default="full,wo_evolution,wo_memory,wo_orchestration,react_baseline")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--judge-success-threshold", type=float, default=70.0)
    parser.add_argument("--react-recursion-limit", type=int, default=None)
    parser.add_argument("--output-dir", type=str, default="src/benchmarks/results")
    parser.add_argument("--no-judge", action="store_true")
    parser.add_argument(
        "--resume-run-id",
        type=str,
        default=None,
        help="断点续跑：复用已有 run_id（例如 1776695516_full）。将从现有 judge_logs.jsonl 推断已完成 task/trial 并跳过。",
    )
    args = parser.parse_args()

    variants = build_variants(
        [x.strip() for x in args.variants.split(",") if x.strip()],
        react_recursion_limit=args.react_recursion_limit
    )
    if args.resume_run_id and len(variants) != 1:
        raise ValueError("--resume-run-id 目前仅支持单个 variant（例如只跑 full）")
    await run_benchmark(
        benchmark_path=args.benchmark,
        variants=variants,
        limit=args.limit,
        output_dir=args.output_dir,
        judge=not args.no_judge,
        repeat=args.repeat,
        judge_success_threshold=args.judge_success_threshold,
        resume_run_id=args.resume_run_id,
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
