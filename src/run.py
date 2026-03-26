import asyncio
import json
import sys
import subprocess
import os

async def run_one_shot(prompt: str):
    # Spawn the server process
    server = subprocess.Popen(
        ["uv", "run", "python", "-m", "src.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1
    )

    request_id = 1
    session_id = None

    def send(method, params):
        nonlocal request_id
        request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        request_id += 1
        server.stdin.write(json.dumps(request) + "\n")
        server.stdin.flush()

    # Create session
    send("session/new", {
        "cwd": os.getcwd(),
        "mcpServers": [],
        "configOptions": {"agent": "FinAgent-Evo"}
    })

    try:
        while True:
            line = server.stdout.readline()
            if not line:
                break
            
            try:
                msg = json.loads(line)
                if msg.get("id") == 1: # Session created
                    if "error" in msg:
                        print(f"\n❌ Error creating session: {json.dumps(msg['error'], indent=2)}", file=sys.stderr)
                        break
                    session_id = msg["result"]["sessionId"]
                    send("session/prompt", {
                        "sessionId": session_id,
                        "prompt": [{"type": "text", "text": prompt}]
                    })
                elif msg.get("method") == "session/update":
                    update = msg["params"]["update"]
                    if update.get("sessionUpdate") == "agent_message_chunk":
                        content = update.get("content", {})
                        if isinstance(content, dict):
                            print(content.get("text", ""), end="", flush=True)
                        else:
                            print(update.get("preview", ""), end="", flush=True)
                elif msg.get("id") == 2: # Prompt finished
                    if "error" in msg:
                        print(f"\n❌ Error in prompt: {json.dumps(msg['error'], indent=2)}", file=sys.stderr)
                    else:
                        print("\n")
                    break
            except json.JSONDecodeError:
                pass
    finally:
        server.terminate()

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "Hello FinAgent-Evo! Briefly introduce your core mission."
    asyncio.run(run_one_shot(prompt))
