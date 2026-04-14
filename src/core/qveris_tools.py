import os
import json
import urllib.parse
import requests
from typing import Any, Dict
from dotenv import load_dotenv

load_dotenv()
QVERIS_API_KEY = os.getenv("QVERIS_API_KEY")
QVERIS_BASE_URL = "https://qveris.ai/api/v1"

def search_qveris_tools(query: str, limit: int = 3) -> list:
    url = f"{QVERIS_BASE_URL}/search"
    headers = {
        "Authorization": f"Bearer {QVERIS_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"query": query, "limit": limit}
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []

def execute_qveris_tool(tool_id: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{QVERIS_BASE_URL}/tools/execute?tool_id={urllib.parse.quote(tool_id)}"
    headers = {
        "Authorization": f"Bearer {QVERIS_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {"parameters": parameters, "max_response_size": 20480}
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    if response.status_code == 200:
        return response.json()
    return {"error": f"HTTP {response.status_code}", "detail": response.text}

def qveris_fetch_data(intent: str, parameters: dict) -> str:
    """
    Unified function to fetch financial data using QVeris APIs.
    intent: The kind of data to fetch (e.g. "stock price", "exchange rate EUR/USD", "AAPL income statement")
    parameters: Guessed parameters like {"symbol": "AAPL"}
    """
    tools = search_qveris_tools(intent)
    if not tools:
        return f"No tools found for intent: {intent}"
    
    # Try executing the top tool
    tool = tools[0]
    tool_id = tool.get("tool_id")
    
    print(f"    [QVeris] Executing {tool_id} with params {parameters}...")
    res = execute_qveris_tool(tool_id, parameters)
    
    if res.get("success"):
        return json.dumps(res.get("result", {}).get("data", res.get("result", {})), ensure_ascii=False)[:2000]
    else:
        # If it fails, maybe try second tool or return error
        return f"Execution failed for {tool_id}: {res.get('error_message', res)}"
