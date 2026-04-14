
import os
import sys
import asyncio
import json
import numpy as np
import re
import argparse
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

sys.path.insert(0, os.path.abspath("."))
sys.path.append(os.path.abspath("benchmarks/investorbench"))

from ib_src.market_env import MarketEnv
from src.agent import agent
from src.scripts.calculate_trading_metrics import calculate_all_metrics

load_dotenv()

logger.remove()
def _log_filter(record):
    if record["name"] == "ib_src.market_env" and record["level"].name == "INFO":
        return False
    return True

logger.add(sys.stderr, level="INFO", filter=_log_filter)

async def run_symbol_iteration(
    symbol,
    warmup_start_str,
    test_start_str,
    test_end_str,
    initial_capital=100000.0,
    eval_days: int | None = None,
    skip_warmup: bool = False,
):
    """Runs a full simulation for a single symbol with warmup and evaluation phases."""
    
    test_start_date = datetime.strptime(test_start_str, "%Y-%m-%d").date()
    test_end_date = datetime.strptime(test_end_str, "%Y-%m-%d").date()
    warmup_start_date = datetime.strptime(warmup_start_str, "%Y-%m-%d").date()
    
    env_data_path = {symbol: f"benchmarks/investorbench/data/{symbol.lower()}.json"}
    
    # We need to find the actual closest available date in the data for warmup
    with open(env_data_path[symbol], "r") as f:
        data = json.load(f)
        available_dates = sorted([datetime.strptime(d, "%Y-%m-%d").date() for d in data.keys()])
    
    start_anchor = test_start_date if skip_warmup else warmup_start_date
    actual_start_date_obj = next((d for d in available_dates if d >= start_anchor), available_dates[0])
    
    # Find actual end date (the latest date <= test_end_date)
    actual_end_date_obj = next((d for d in reversed(available_dates) if d <= test_end_date), available_dates[-1])
    
    actual_start_date_str = actual_start_date_obj.strftime("%Y-%m-%d")
    actual_end_date_str = actual_end_date_obj.strftime("%Y-%m-%d")

    env = MarketEnv(
        env_data_path=env_data_path,
        start_date=actual_start_date_str,
        end_date=actual_end_date_str,
        symbol=symbol,
        momentum_window_size=5
    )
    
    initial_date_series = list(env.final_date_series)
    warmup_total = 0 if skip_warmup else sum(1 for d in initial_date_series if d < test_start_date)
    eval_total = len(initial_date_series) if skip_warmup else sum(1 for d in initial_date_series if d >= test_start_date)
    if eval_days is not None:
        eval_total = min(eval_total, eval_days)

    cash = initial_capital
    position = 0.0
    eval_history = []
    daily_returns = []
    current_exposure = 0.0 # 0.0 to 1.0
    eval_count = 0
    warmup_count = 0
    
    if skip_warmup:
        logger.info(f">>> [{symbol}] Phase 1: EVALUATION ({actual_start_date_str} to {actual_end_date_str})")
    else:
        logger.info(f">>> [{symbol}] Phase 1: WARMUP ({actual_start_date_str} to {test_start_str})")
    
    while True:
        obs = env.step()
        if obs.termination_flag:
            break
            
        cur_date = obs.cur_date
        cur_price = obs.cur_price[symbol]
        cur_news = obs.cur_news[symbol] if obs.cur_news and symbol in obs.cur_news else []
        cur_momentum = obs.cur_momentum[symbol]
        
        is_warmup = (not skip_warmup) and (cur_date < test_start_date)
        
        # Advanced Technical Indicators
        price_series = env.market_price_series[symbol]
        sma_5 = np.mean(price_series[-5:]) if len(price_series) >= 5 else cur_price
        
        # Context
        recent_prices = price_series[-5:].tolist()
        price_context = ", ".join([f"${p:.2f}" for p in recent_prices])
        news_str = "\n".join([f"- {n}" for n in cur_news]) if cur_news else "No news available."
        
        analysis_input = f"""
        Asset: {symbol} | Date: {cur_date}
        Current Price: ${cur_price:.2f}
        SMA-5: ${sma_5:.2f}
        Price History (Last 5d): [{price_context}]
        Momentum: {cur_momentum}
        News: {news_str}
        """
        
        phase_name = "WARMUP" if is_warmup else "EVALUATION"
        
        try:
            reasoning_prompt = f"""
            You are an Expert Quantitative Trader. 
            Task: Direct Reasoning for {symbol} on {cur_date} ({phase_name}).
            
            Current Data:
            {analysis_input}
            
            Based on the data, provide your analysis and target exposure.
            
            ### MANDATORY OUTPUT FORMAT:
            Reasoning: <detailed_analysis>
            Target Exposure: <X>% (0-100)
            Final Recommendation: <BUY/SELL/HOLD>
            """
            
            if is_warmup:
                warmup_count += 1
                logger.info(f"[{symbol}] {phase_name} {warmup_count}/{max(warmup_total, 1)} | {cur_date} | Price: ${cur_price:.2f}")
            else:
                logger.info(f"[{symbol}] {phase_name} {eval_count + 1}/{max(eval_total, 1)} | {cur_date} | Price: ${cur_price:.2f}")
            res = await agent.ainvoke({"messages": [("user", reasoning_prompt)]})
            agent_output = res["messages"][-1].content
            
            if is_warmup:
                logger.info(f"  🧠 Warmup Reasoning: {agent_output[:200]}...")
            else:
                target_exposure = current_exposure 
                exp_match = re.search(r"Target Exposure:\s*(\d+)%", agent_output)
                if exp_match:
                    target_exposure = float(exp_match.group(1)) / 100.0
                
                total_equity_before = cash + position * cur_price
                
                target_pos_value = total_equity_before * target_exposure
                current_pos_value = position * cur_price
                diff = target_pos_value - current_pos_value
                
                if abs(diff) > 10:
                    units_to_trade = diff / cur_price
                    position += units_to_trade
                    cash -= diff
                    current_exposure = target_exposure
                    logger.info(f"  💰 Rebalance: {target_exposure*100:.0f}% exposure | Equity: ${total_equity_before:.2f}")
                
                eval_history.append({
                    "date": str(cur_date),
                    "price": cur_price,
                    "portfolio_value": total_equity_before,
                    "exposure": target_exposure
                })
                
                if len(eval_history) > 1:
                    daily_ret = (total_equity_before - eval_history[-2]["portfolio_value"]) / eval_history[-2]["portfolio_value"]
                    daily_returns.append(daily_ret)
                
                eval_count += 1
                if eval_days is not None and eval_count >= eval_days:
                    break

        except Exception as e:
            logger.error(f"Error on {cur_date}: {e}")

    # Calculate Metrics for Evaluation Phase
    if not eval_history:
        return None
        
    metrics = calculate_all_metrics(daily_returns)
    
    # Calculate Buy & Hold for comparison
    start_price = eval_history[0]["price"]
    end_price = eval_history[-1]["price"]
    bh_return = (end_price - start_price) / start_price
    alpha = metrics["cr"] - bh_return
    
    logger.info(f"DONE {symbol} | CR: {metrics['cr']*100:.2f}% | ALPHA: {alpha*100:.2f}% | SR: {metrics['sr']:.2f} | AV: {metrics['av']*100:.2f}% | MDD: {metrics['mdd']*100:.2f}%")
    
    return {
        "symbol": symbol,
        "cr": metrics["cr"],
        "sr": metrics["sr"],
        "av": metrics["av"],
        "mdd": metrics["mdd"],
        "bh": bh_return,
        "alpha": alpha
    }

async def run_full_evaluation(concurrency: int = 4, eval_days: int | None = None, skip_warmup: bool = False):
    test_configs = [
        {"symbol": "BTC", "warmup_start": "2023-02-11", "test_start": "2023-04-05", "test_end": "2023-11-05"},
        {"symbol": "ETH", "warmup_start": "2023-02-11", "test_start": "2023-04-05", "test_end": "2023-11-05"},
        
        {"symbol": "HON", "warmup_start": "2020-07-01", "test_start": "2020-10-01", "test_end": "2021-05-06"},
        {"symbol": "JNJ", "warmup_start": "2020-07-01", "test_start": "2020-10-01", "test_end": "2021-05-06"},
        {"symbol": "MSFT", "warmup_start": "2020-07-01", "test_start": "2020-10-01", "test_end": "2021-05-06"},
        {"symbol": "NFLX", "warmup_start": "2020-07-01", "test_start": "2020-10-01", "test_end": "2021-05-06"},
        {"symbol": "UVV", "warmup_start": "2020-07-01", "test_start": "2020-10-01", "test_end": "2021-05-06"},
    ]
    
    semaphore = asyncio.Semaphore(concurrency) 
    
    async def sem_run(config):
        for attempt in range(3):
            try:
                async with semaphore:
                    return await run_symbol_iteration(
                        config["symbol"], 
                        config["warmup_start"], 
                        config["test_start"], 
                        config["test_end"],
                        eval_days=eval_days,
                        skip_warmup=skip_warmup,
                    )
            except Exception as e:
                if "429" in str(e):
                    await asyncio.sleep((attempt + 1) * 10)
                else:
                    logger.error(f"Failed {config['symbol']}: {e}")
                    return None
        return None

    logger.info(">>> Starting InvestorBench Evaluation with Warmup...")
    results = await asyncio.gather(*[sem_run(c) for c in test_configs], return_exceptions=True)
    final_results = [r for r in results if isinstance(r, dict)]
    
    if not final_results:
        logger.error("No valid results collected.")
        return

    print("\n" + "="*115)
    print(f"{'SYMBOL':<10} | {'CR (%)':<10} | {'B&H (%)':<10} | {'ALPHA (%)':<12} | {'SR':<8} | {'AV (%)':<10} | {'MDD (%)':<10}")
    print("-" * 115)
    for r in final_results:
        print(f"{r['symbol']:<10} | {r['cr']*100:>9.2f}% | {r['bh']*100:>9.2f}% | {r['alpha']*100:>11.2f}% | {r['sr']:>7.2f} | {r['av']*100:>9.2f}% | {r['mdd']*100:>9.2f}%")
    print("="*115)
    
    avg_alpha = sum([r['alpha'] for r in final_results]) / len(final_results)
    print(f"AVERAGE ALPHA: {avg_alpha*100:.2f}%")
    
    os.makedirs("benchmarks/investorbench/results", exist_ok=True)
    with open("benchmarks/investorbench/results/investorbench_aligned_summary.json", "w") as f:
        json.dump(final_results, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-days", type=int, default=None)
    parser.add_argument("--skip-warmup", action="store_true")
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    asyncio.run(run_full_evaluation(concurrency=args.concurrency, eval_days=args.eval_days, skip_warmup=args.skip_warmup))
