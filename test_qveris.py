import asyncio
from src.agent import invoke_skill

async def test():
    res = await invoke_skill.ainvoke({"skill_id": "get_macro_data", "input": "FEDERAL_FUNDS_RATE"})
    print("get_macro_data:", res)
    
    res = await invoke_skill.ainvoke({"skill_id": "get_crypto_price", "input": "BTC"})
    print("get_crypto_price:", res)

if __name__ == "__main__":
    asyncio.run(test())
