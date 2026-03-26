import asyncio
import os
import sys
from dotenv import load_dotenv
from deepagents_acp.server import AgentServerACP, run_acp_agent
from src.agent import agent

# Load environment variables
load_dotenv()

async def main():
    # Redirect all stdout (console.log) to stderr so it doesn't break the ACP protocol
    # In Python, we just use print(..., file=sys.stderr) but this is for safety
    print("Starting FinAgent-Evo ACP Server...", file=sys.stderr)
    
    # Expose the agent over ACP
    server = AgentServerACP(
        agent=agent
    )
    
    await run_acp_agent(server)

if __name__ == "__main__":
    asyncio.run(main())
