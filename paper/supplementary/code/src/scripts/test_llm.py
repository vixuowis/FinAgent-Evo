import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DASHSCOPE_API_KEY")
base_url = os.getenv("DASHSCOPE_BASE_URL")
model_name = os.getenv("DASHSCOPE_MODEL")

print(f"Testing DashScope: {model_name} at {base_url}")

model = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url,
    timeout=30,
    max_retries=1
)

try:
    resp = model.invoke("Hello, are you there?")
    print(f"Success: {resp.content}")
except Exception as e:
    print(f"Error: {e}")
