# FinAgent-Evo ACP Server

This is a demo implementation of the **FinAgent-Evo** framework, an autonomous evolving dynamic skill orchestration framework for financial investment research, exposed as an **ACP (Agent Client Protocol)** server.

## Features
- **ACP Integration**: Standardized communication with code editors like Zed, JetBrains, and VS Code.
- **FinAgent-Evo Core**: 
  - **Skill Evolution**: Placeholder tools for optimizing skill genotypes and topologies.
  - **Dynamic Orchestration**: Context-aware routing for financial tasks.
  - **Hierarchical Memory**: Simulated memory system for experience reuse.
- **Financial Tools**:
  - `fetch_market_data`: Real-time market data retrieval.
  - `analyze_sentiment`: Financial news sentiment analysis.

## Setup

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Configure Environment**:
   Create a `.env` file and add your API keys:
   ```env
   ANTHROPIC_API_KEY=your_key_here
   ```

3. **Start the Server**:
   ```bash
   npm start
   ```

## Usage with Zed

Add the following to your Zed `settings.json`:

```json
{
  "agent": {
    "profiles": {
      "finagent-evo": {
        "name": "FinAgent-Evo",
        "command": "npx",
        "args": ["tsx", "/absolute/path/to/FinAgent/src/server.ts"],
        "env": {
          "ANTHROPIC_API_KEY": "your_key_here"
        }
      }
    }
  }
}
```

## Proposal Reference
Based on the research proposal: `docs/proposal.md`.
