import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_judge():
    base_url = "https://apicn.unifyllm.top/v1"
    api_key = os.getenv("UNIFY_API_KEY")
    model = "claude-opus-4-7"
    
    print(f"Testing model {model} at {base_url}")
    
    headers = {
        "Authorization": f"Bearer {api_key}@default",
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Hello, are you available?"}
        ],
        "temperature": 0
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_judge())
