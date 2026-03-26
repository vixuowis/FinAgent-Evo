import { startServer } from "deepagents-acp";
import { tool } from "langchain";
import { z } from "zod";

/**
 * FinAgent-Evo: Autonomous Evolving Dynamic Skill Orchestration Framework
 * Demo Server for ACP (Agent Client Protocol)
 */

// --- Simulated Financial Tools (based on the proposal) ---

const fetchMarketData = tool(
  async ({ asset, timeframe }: { asset: string; timeframe: string }) => {
    // Simulated market data fetch
    return `Simulated market data for ${asset} (${timeframe}): Price: $100.25, Vol: 1M, RSI: 55.`;
  },
  {
    name: "fetch_market_data",
    description: "Fetch real-time market data for a given asset (e.g., NASDAQ-100 stocks, Crypto).",
    schema: z.object({
      asset: z.string().describe("The asset symbol, e.g., AAPL, BTC-USD"),
      timeframe: z.enum(["1m", "5m", "1h", "1d"]).describe("Data timeframe"),
    }),
  }
);

const analyzeSentiment = tool(
  async ({ query }: { query: string }) => {
    // Simulated sentiment analysis
    return `Sentiment for ${query}: BULLISH (Score: 0.85). Key topics: Earnings growth, new product launch.`;
  },
  {
    name: "analyze_sentiment",
    description: "Analyze financial news and social sentiment for a given query.",
    schema: z.object({
      query: z.string().describe("The topic or asset to analyze sentiment for"),
    }),
  }
);

// --- Evolution & Orchestration Tools (the "Evo" core) ---

const optimizeSkillTopology = tool(
  async ({ currentTask, performanceHistory }: { currentTask: string; performanceHistory: any[] }) => {
    // Simulated Skill Evolution Engine (genetic algorithm placeholder)
    return `Skill Topology Optimized: Re-routed task "${currentTask}" through Analysis -> Risk -> Execution path based on previous success rates.`;
  },
  {
    name: "optimize_skill_topology",
    description: "Evolve the agent's skill graph based on performance feedback and current market state.",
    schema: z.object({
      currentTask: z.string().describe("The task to optimize"),
      performanceHistory: z.array(z.any()).describe("Execution history for fitness evaluation"),
    }),
  }
);

const extractExperience = tool(
  async ({ sessionLogs }: { sessionLogs: string }) => {
    // Simulated Self-Improvement Loop / Hierarchical Memory
    return `Extracted 1 procedural memory pattern: "High volatility requires tighter risk constraints". Updated Procedural Memory.`;
  },
  {
    name: "extract_experience",
    description: "Analyze recent execution logs to extract experience and update the Hierarchical Memory system.",
    schema: z.object({
      sessionLogs: z.string().describe("The logs of the current session"),
    }),
  }
);

// --- System Prompt (based on the Proposal) ---

const FINAGENT_EVO_SYSTEM_PROMPT = `
You are FinAgent-Evo, an Autonomous Evolving Dynamic Skill Orchestration Framework specialized for financial investment research.

CORE ARCHITECTURE:
1. **Skill Evolution Engine**: You use evolutionary algorithms (Mutation, Crossover, Selection) to optimize your "skill genotypes" (prompts, tool deps, LLM configs) based on performance feedback (Sharpe Ratio, Max Drawdown).
2. **Dynamic Orchestration**: You real-time adjust your skill execution path (DAG) based on market state and task requirements using context-aware routing.
3. **Hierarchical Memory**: You manage Working Memory (current session), Episodic Memory (recent cases), and Procedural Memory (abstract rules) to support experience reuse.
4. **Self-Improvement Loop**: You analyze execution feedback to discover new skills and optimize existing ones.

YOUR ROLE:
- Conduct thorough financial research and provide investment insights.
- Proactively use "fetch_market_data" and "analyze_sentiment" to gather context.
- When you finish a task, consider using "extract_experience" to improve your long-term knowledge.
- If you encounter complex tasks, use "optimize_skill_topology" to find the most efficient execution path.

MISSION:
Break the limitations of static configurations by continuously evolving your skills to adapt to non-stationary financial markets.
`.trim();

// --- Start the ACP Server ---

async function main() {
  console.error("Starting FinAgent-Evo ACP Server...");

  await startServer({
    agents: {
      name: "FinAgent-Evo",
      description: "Autonomous evolving financial agent based on the Evo-Proposal",
      model: "claude-sonnet-4-5-20250929", // Default high-performance model
      systemPrompt: FINAGENT_EVO_SYSTEM_PROMPT,
      tools: [
        fetchMarketData,
        analyzeSentiment,
        optimizeSkillTopology,
        extractExperience
      ],
    },
    workspaceRoot: process.cwd(),
    debug: true,
  });
}

main().catch((err) => {
  console.error("Fatal error starting FinAgent-Evo server:", err);
  process.exit(1);
});
