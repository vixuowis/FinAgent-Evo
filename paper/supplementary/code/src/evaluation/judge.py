import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.evaluation.utils import extract_first_json_object, sha256_text, safe_json_dumps

load_dotenv()


JUDGE_PROMPT_TEMPLATE_V1 = """你是严格且专业的金融评测裁判（Institutional-Grade Financial Agent Judge）。
你将评估 Agent 在复杂金融推理任务中的表现。

### 评分维度 (Rubric):
1. **指标完备性 (Final Answer Metrics - 40分)**:
   - 检查回答是否覆盖了 evaluation_criteria 中的所有 final_answer_metrics。
   - 每缺失一个核心指标扣 10-15 分。如果指标数值与轨迹计算逻辑一致但因四舍五入略有差异，不扣分。

2. **逻辑严谨性与数值保真度 (Numerical Fidelity - 30分)**:
   - 轨迹必须体现“数据获取 -> 计算 -> 结论”的闭环。
   - **零容忍数据编造 (Fabrication)**: 如果轨迹中没有获取到某数据，但最终回答中出现了该数据，直接扣除此项全部分数（30分）。
   - 如果 Python 解释器报错但 Agent 在回答中强行给出结果，视为严重失分。

3. **执行效率与工具调用 (Execution Efficiency - 20分)**:
   - 是否满足 must_call_sequence 的意图序列。
   - 工具名不必完全匹配，只要意图对齐即可（例如 `get_financial_statements` 对齐 `fetch_income_statement`）。
   - 冗余的重复调用（例如 3 次获取同一汇率）应扣 5-10 分。

4. **长链推理稳定性 (Long-chain Robustness - 10分)**:
   - 在多步（>4步）任务中，Agent 是否保持了目标一致性，没有发生“目标漂移”。

### 输出要求:
输出必须是严格 JSON 格式：
{
  "score": 0,
  "reasoning": "",
  "met_metrics": [],
  "missed_metrics": [],
  "fabrication_detected": false
}
"""


@dataclass
class JudgeConfig:
    name: str
    model: str
    base_url: str
    api_key: str
    temperature: float

    @property
    def prompt_sha256(self) -> str:
        return sha256_text(JUDGE_PROMPT_TEMPLATE_V1)


def _resolve_judge_models() -> List[str]:
    # Preferred: explicit multi-judge list, e.g. "gpt-5.4,claude-opus-4-6"
    raw = os.getenv("JUDGE_MODELS", "").strip()
    if raw:
        models = [x.strip() for x in raw.split(",") if x.strip()]
        if models:
            return models
    # Backward compatible single-judge envs
    single = os.getenv("JUDGE_MODEL", os.getenv("DASHSCOPE_MODEL", "glm-5")).strip()
    return [single]


def create_judge_configs() -> List[JudgeConfig]:
    models = _resolve_judge_models()
    # Prefer dedicated judge endpoint/key, then Unify endpoint/key, then DashScope envs.
    base_url = os.getenv(
        "JUDGE_BASE_URL",
        os.getenv("UNIFY_BASE_URL", os.getenv("DASHSCOPE_BASE_URL", "https://coding.dashscope.aliyuncs.com/v1")),
    )
    if base_url and "unifyllm.top" in base_url and not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"
    api_key = os.getenv(
        "JUDGE_API_KEY",
        os.getenv("UNIFY_API_KEY", os.getenv("DASHSCOPE_API_KEY", "")),
    )
    temperature_str = os.getenv("JUDGE_TEMPERATURE", "0")
    try:
        temperature = float(temperature_str)
    except Exception:
        temperature = 0.0

    cfgs: List[JudgeConfig] = []
    for i, model in enumerate(models):
        cfgs.append(
            JudgeConfig(
                name=f"judge_{i+1}",
                model=model,
                base_url=base_url,
                api_key=api_key,
                temperature=temperature,
            )
        )
    return cfgs


def create_judge_config() -> JudgeConfig:
    # Backward compatibility for callers expecting a single config.
    return create_judge_configs()[0]


def judge_enabled() -> bool:
    key = os.getenv(
        "JUDGE_API_KEY",
        os.getenv("UNIFY_API_KEY", os.getenv("DASHSCOPE_API_KEY", "")),
    ).strip()
    return bool(key and key != "dummy")


def create_judge_model(cfg: JudgeConfig) -> ChatOpenAI:
    timeout_s = int(os.getenv("JUDGE_TIMEOUT_SECONDS", os.getenv("LLM_TIMEOUT_SECONDS", "600")).strip() or "600")
    max_retries = int(os.getenv("JUDGE_MAX_RETRIES", "3").strip() or "3")
    return ChatOpenAI(
        model=cfg.model,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        temperature=cfg.temperature,
        timeout=timeout_s,
        max_retries=max_retries,
    )


async def run_judge(
    task: Dict[str, Any],
    final_answer: str,
    trajectory: Any,
    cfg: JudgeConfig,
    max_retries: int = 3,
) -> Tuple[Dict[str, Any], str, Optional[str], Dict[str, Any]]:
    judge_input = {
        "query": task.get("query") or task.get("task") or "",
        "evaluation_criteria": task.get("evaluation_criteria") or task.get("evaluation_criteria", {}),
        "final_answer": final_answer or "",
        "trajectory": trajectory,
    }

    if not judge_enabled():
        parsed = {
            "score": 0,
            "reasoning": "judge_disabled_or_missing_key",
            "met_metrics": [],
            "missed_metrics": [],
        }
        return parsed, "", "judge_disabled_or_missing_key", judge_input

    msg = (
        f"Task Query:\n{judge_input['query']}\n\n"
        f"Evaluation Criteria:\n{safe_json_dumps(judge_input['evaluation_criteria'])}\n\n"
        f"Agent Final Answer:\n{judge_input['final_answer']}\n\n"
        f"Agent Trajectory:\n{safe_json_dumps(judge_input['trajectory'])}\n"
    )

    import asyncio
    import httpx
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # We prefer direct HTTP call for judges to avoid LangChain/OpenAI client overhead and proxy issues
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        f"{cfg.base_url.rstrip('/')}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {cfg.api_key}",
                            "X-Group": "default"
                        },
                        json={
                            "model": cfg.model,
                            "messages": [
                                {"role": "system", "content": JUDGE_PROMPT_TEMPLATE_V1},
                                {"role": "user", "content": msg}
                            ],
                            "temperature": cfg.temperature,
                            "response_format": {"type": "json_object"} if "gpt" in cfg.model.lower() else None
                        },
                        timeout=180.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        raw_text = data["choices"][0]["message"]["content"]
                        # Successfully got a response, break retry loop
                        break
                    else:
                        err_text = response.text[:200]
                        print(f"HTTP {response.status_code} from {cfg.name} (Attempt {attempt+1}): {err_text}")
                        # Fallback to LangChain within the same attempt
                        judge_model = create_judge_model(cfg)
                        resp = await judge_model.ainvoke(
                            [SystemMessage(content=JUDGE_PROMPT_TEMPLATE_V1), HumanMessage(content=msg)]
                        )
                        raw_text = getattr(resp, "content", str(resp))
                        break # Successfully got a response from fallback, break retry loop
                except Exception as e:
                    print(f"Request attempt {attempt+1} failed for {cfg.name}: {str(e)}")
                    last_error = e
                    # Try LangChain fallback as a secondary option in each attempt
                    try:
                        judge_model = create_judge_model(cfg)
                        resp = await judge_model.ainvoke(
                            [SystemMessage(content=JUDGE_PROMPT_TEMPLATE_V1), HumanMessage(content=msg)]
                        )
                        raw_text = getattr(resp, "content", str(resp))
                        break # Successfully got a response from fallback, break retry loop
                    except Exception as lc_e:
                        print(f"LangChain fallback attempt {attempt+1} also failed: {str(lc_e)}")
                        last_error = lc_e
        except Exception as global_e:
            print(f"Global judge error (Attempt {attempt+1}): {str(global_e)}")
            last_error = global_e

        if attempt < max_retries - 1:
            wait_time = (attempt + 1) * 5
            await asyncio.sleep(wait_time)
    else:
        # If we exhausted retries and didn't break
        raw_text = f'{{"score": 0, "reasoning": "judge_error_after_retries: {str(last_error)}"}}'

    parsed, parse_error = extract_first_json_object(raw_text)
    if parsed is None:
        parsed = {
            "score": 0,
            "reasoning": "judge_parse_failed",
            "met_metrics": [],
            "missed_metrics": [],
            "fabrication_detected": False,
        }
    for k in ["score", "reasoning", "met_metrics", "missed_metrics", "fabrication_detected"]:
        if k not in parsed:
            if k == "score":
                parsed[k] = 0
            elif k in {"met_metrics", "missed_metrics"}:
                parsed[k] = []
            elif k == "fabrication_detected":
                parsed[k] = False
            else:
                parsed[k] = ""
    return parsed, raw_text, parse_error, judge_input
