
import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch

load_dotenv()
api_key = os.getenv("TAVILY_API_KEY")
print(f"API Key: {api_key[:5]}...{api_key[-5:] if api_key else ''}")

try:
    search = TavilySearch(max_results=3)
    results = search.run("test query")
    print(f"Results: {results}")
except Exception as e:
    print(f"Error: {e}")
