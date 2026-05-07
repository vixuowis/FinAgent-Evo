
import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

async def test_model(model_name, base_url, api_key):
    print(f"Testing model: {model_name}...")
    try:
        llm = ChatOpenAI(
            model=model_name,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0,
            max_tokens=50
        )
        resp = await llm.ainvoke([HumanMessage(content="Hello, please respond with 'OK' and your model name.")])
        print(f"✅ {model_name} Success: {resp.content.strip()}")
        return True
    except Exception as e:
        print(f"❌ {model_name} Failed: {str(e)}")
        return False

async def main():
    base_url = os.getenv("UNIFY_BASE_URL")
    api_key = os.getenv("UNIFY_API_KEY")
    models = os.getenv("JUDGE_MODELS", "gpt-5.4,claude-opus-4-6").split(",")
    
    print(f"Base URL: {base_url}")
    print(f"API Key: {api_key[:10]}...")
    
    tasks = [test_model(m.strip(), base_url, api_key) for m in models]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
