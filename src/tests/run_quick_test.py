import json
import asyncio
import re
from src.run import run_one_shot

async def evaluate_agent(test_case):
    question = test_case["question"]
    context = test_case["context"]
    ground_truth = test_case["ground_truth"]
    
    prompt = f"Context: {context}\n\nQuestion: {question}\n\nPlease provide your final answer as a number at the end of your response, prefixed with 'Final Answer: '."
    
    print(f"\n--- Testing Question {test_case['question_id']} ---")
    print(f"Question: {question}")
    
    # Run the agent
    # Since run_one_shot prints to stdout, we might need to capture it or modify it.
    # For now, let's just run it and see the output.
    # Note: run_one_shot is async.
    
    # We'll use a modified version of run_one_shot that returns the full response string.
    response = await run_and_capture_response(prompt)
    
    # Extract final answer
    match = re.search(r"Final Answer:\s*([\d\.]+)", response)
    if match:
        agent_answer = float(match.group(1))
        is_correct = abs(agent_answer - float(ground_truth)) < 1e-5
        print(f"\nAgent Answer: {agent_answer}")
        print(f"Ground Truth: {ground_truth}")
        print(f"Result: {'✅ PASS' if is_correct else '❌ FAIL'}")
        return is_correct
    else:
        print("\n❌ Could not find 'Final Answer: ' in agent response.")
        return False

async def run_and_capture_response(prompt: str):
    import subprocess
    import sys
    import os
    
    server = subprocess.Popen(
        ["uv", "run", "python", "-m", "src.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1
    )

    request_id = 1
    full_response = []

    def send(method, params):
        nonlocal request_id
        request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        request_id += 1
        server.stdin.write(json.dumps(request) + "\n")
        server.stdin.flush()

    send("session/new", {
        "cwd": os.getcwd(),
        "mcpServers": [],
        "configOptions": {"agent": "FinAgent-Evo"}
    })

    try:
        while True:
            line = server.stdout.readline()
            if not line: break
            try:
                msg = json.loads(line)
                if msg.get("id") == 1:
                    session_id = msg["result"]["sessionId"]
                    send("session/prompt", {
                        "sessionId": session_id,
                        "prompt": [{"type": "text", "text": prompt}]
                    })
                elif msg.get("method") == "session/update":
                    update = msg["params"]["update"]
                    if update.get("sessionUpdate") == "agent_message_chunk":
                        content = update.get("content", {})
                        text = content.get("text", "") if isinstance(content, dict) else update.get("preview", "")
                        full_response.append(text)
                        print(text, end="", flush=True)
                elif msg.get("id") == 2:
                    break
            except json.JSONDecodeError: pass
    finally:
        server.terminate()
    
    return "".join(full_response)

async def main():
    import sys
    test_file = sys.argv[1] if len(sys.argv) > 1 else "benchmarks/financereasoning/quick.json"
    
    with open(test_file, "r") as f:
        test_cases = json.load(f)
    
    results = []
    for case in test_cases:
        success = await evaluate_agent(case)
        results.append(success)
    
    print("\n" + "="*30)
    print(f"Summary for {test_file}: {sum(results)}/{len(results)} passed")
    print("="*30)

if __name__ == "__main__":
    asyncio.run(main())
