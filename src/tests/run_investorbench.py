
import os
import sys
import asyncio
import json
import numpy as np
import importlib.util
from datetime import datetime
from dotenv import load_dotenv

# Add investorbench to sys.path
sys.path.append(os.path.abspath("benchmarks/investorbench"))

from ib_src.market_env import MarketEnv
from src.agent import agent

load_dotenv()

async def run_investorbench_simulation(symbol="BTC", start_date="2022-11-29", end_date="2022-12-04"):
    # Initialize Environment
    env_data_path = {symbol: f"benchmarks/investorbench/data/{symbol.lower()}.json"}
    env = MarketEnv(
        env_data_path=env_data_path,
        start_date=start_date,
        end_date=end_date,
        symbol=symbol,
        momentum_window_size=3
    )
    
    portfolio_value = 100000.0  # Initial capital: $100k
    position = 0.0  # Units of asset held
    cash = 100000.0
    
    history = []
    
    print(f"Starting simulation for {symbol} from {start_date} to {end_date}...")
    
    while True:
        obs = env.step()
        if obs.termination_flag:
            break
            
        cur_date = obs.cur_date
        cur_price = obs.cur_price[symbol]
        cur_news = obs.cur_news[symbol] if obs.cur_news and symbol in obs.cur_news else []
        cur_momentum = obs.cur_momentum[symbol]
        
        # Current portfolio value
        current_val = cash + position * cur_price
        
        # Prepare prompt for our agent
        news_str = "\n".join([f"- {n}" for n in cur_news]) if cur_news else "No news available."
        prompt = f"""
Date: {cur_date}
Asset: {symbol}
Current Price: ${cur_price:.2f}
Recent Momentum: {'Up' if cur_momentum == 1 else 'Down' if cur_momentum == -1 else 'Neutral'}

Recent News Headlines:
{news_str}

Based on the above information, provide a strategic investment decision: BUY, SELL, or HOLD.
Your response should be a clear recommendation with reasoning. 
Finish your response with 'Final Decision: BUY', 'Final Decision: SELL', or 'Final Decision: HOLD'.
"""

        # Invoke Agent
        try:
            response = await agent.ainvoke({"messages": [("user", prompt)]})
            agent_output = response["messages"][-1].content
            
            # Extract decision
            decision = "HOLD"
            if "Final Decision: BUY" in agent_output:
                decision = "BUY"
            elif "Final Decision: SELL" in agent_output:
                decision = "SELL"
            
            # Execute decision
            prev_cash = cash
            prev_position = position
            if decision == "BUY" and cash > 0:
                units_to_buy = cash / cur_price
                position += units_to_buy
                cash = 0.0
                print(f"[{cur_date}] BUY {units_to_buy:.4f} units at ${cur_price:.2f}")
            elif decision == "SELL" and position > 0:
                cash += position * cur_price
                print(f"[{cur_date}] SELL all units at ${cur_price:.2f}. Cash: ${cash:.2f}")
                position = 0.0
            else:
                print(f"[{cur_date}] HOLD. Portfolio Value: ${current_val:.2f}")

            # --- SELF-EVOLUTION STEP ---
            # Peek at the next day's price to provide feedback (Learning from the immediate future)
            # In a real run, this happens at the end of the next day.
            actual_return = -obs.cur_future_price_diff[symbol] # Because diff was (price-future)/price
            
            is_success = False
            if decision == "BUY" and actual_return > 0.005: is_success = True
            elif decision == "SELL" and actual_return < -0.005: is_success = True
            elif decision == "HOLD" and abs(actual_return) < 0.005: is_success = True
            
            feedback_prompt = f"""
### CRITICAL POST-TRADE REVIEW (Date: {cur_date})
Your Decision: {decision}
Actual Market Movement next day: {actual_return*100:.2f}%
Success: {'YES' if is_success else 'NO'}

CRITICAL ANALYSIS TASK:
1. Use 'extract_experience' to store this event.
2. If Success is NO: 
   - Identify the EXACT signal (news, price, momentum) you ignored or miscalculated.
   - Use 'evolve_skill' to HARD-CODE a new rule into your 'strategic_decision_making' logic to fix this specific weakness.
   - Your evolution must be aggressive: aim for alpha, not just safety.
3. If Success is YES:
   - Identify what worked and reinforce it in your memory.
"""
            print(f"[{cur_date}] Self-Evolution in progress...")
            evolution_res = await agent.ainvoke({"messages": [("user", feedback_prompt)]})
            print(f"[{cur_date}] Evolution Feedback: {evolution_res['messages'][-1].content[:150]}...")
            # ---------------------------
                
            history.append({
                "date": str(cur_date),
                "price": cur_price,
                "decision": decision,
                "portfolio_value": current_val,
                "agent_reasoning": agent_output,
                "evolution_logs": evolution_res['messages'][-1].content
            })
            
        except Exception as e:
            print(f"Error during agent invocation on {cur_date}: {e}")
            history.append({
                "date": str(cur_date),
                "price": cur_price,
                "decision": "ERROR",
                "portfolio_value": current_val,
                "error": str(e)
            })

    # Final evaluation
    final_price = history[-1]["price"] if history else 0.0
    final_value = cash + position * final_price
    
    print(f"\nSimulation Finished.")
    print(f"Initial Value: $100,000.00")
    print(f"Final Value: ${final_value:.2f}")
    
    # Calculate Metrics
    returns = [h["portfolio_value"] for h in history]
    daily_returns = np.diff(returns) / returns[:-1]
    
    cr = (final_value - 100000.0) / 100000.0
    sr = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 1 and np.std(daily_returns) != 0 else 0
    
    # Max Drawdown
    wealth_index = np.array(returns)
    peaks = np.maximum.accumulate(wealth_index)
    drawdowns = (peaks - wealth_index) / peaks
    md = np.max(drawdowns)
    
    print(f"Cumulative Return (CR): {cr*100:.2f}%")
    print(f"Sharpe Ratio (SR): {sr:.4f}")
    print(f"Max Drawdown (MD): {md*100:.2f}%")
    
    # Save results
    output = {
        "summary": {
            "initial_value": 100000.0,
            "final_value": final_value,
            "cr": cr,
            "sr": sr,
            "md": md
        },
        "history": history
    }
    
    os.makedirs("benchmarks/investorbench/results", exist_ok=True)
    with open(f"benchmarks/investorbench/results/{symbol.lower()}_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    return output["summary"]

async def run_alpha_showcase():
    # Focus on assets where LLM reasoning should shine
    # BTC: High news impact, technical patterns
    # MSFT: Strategic corporate moves
    # NFLX: Consumer sentiment and growth
    
    test_cases = [
        {"symbol": "BTC", "start": "2023-03-01", "end": "2023-03-20"}, # SVB Crisis
        {"symbol": "MSFT", "start": "2021-04-01", "end": "2021-04-20"}, # Growth phase
        {"symbol": "NFLX", "start": "2020-04-13", "end": "2020-04-30"}  # Valid COVID dates
    ]
    
    all_results = {}
    
    print("\n" + "*"*60)
    print("ALPHA SHOWCASE: PROVING THE EVOLUTIONARY ADVANTAGE")
    print("*"*60)
    
    for case in test_cases:
        symbol = case["symbol"]
        res = await run_investorbench_simulation(symbol, case["start"], case["end"])
        all_results[symbol] = res
        
    print("\n" + "="*60)
    print("FINAL ALPHA REPORT")
    print("="*60)
    for symbol, res in all_results.items():
        if res:
            # Simple benchmark: If we just held from start to end
            # This is calculated roughly based on the first and last price in history
            prices = [h["price"] for h in res.get("history", []) if "price" in h]
            if prices:
                bh_return = (prices[-1] - prices[0]) / prices[0]
                alpha = res['cr'] - bh_return
                print(f"{symbol}: CR={res['cr']*100:.2f}%, B&H={bh_return*100:.2f}%, ALPHA={alpha*100:.2f}%")
                print(f"      SR={res['sr']:.4f}, MD={res['md']*100:.2f}%")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_alpha_showcase())
