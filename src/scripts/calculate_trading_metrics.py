
import numpy as np
import pandas as pd
from typing import List, Union

def calculate_cumulative_return(returns: Union[List[float], np.ndarray]) -> float:
    """
    Calculate Cumulative Return (CR).
    CR = product(1 + r_t) - 1
    """
    returns = np.array(returns)
    return np.prod(1 + returns) - 1

def calculate_sharpe_ratio(returns: Union[List[float], np.ndarray], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe Ratio (SR).
    SR = (mean(r_t) - r_f) / std(r_t) * sqrt(252)
    """
    returns = np.array(returns)
    if len(returns) < 2 or np.std(returns) == 0:
        return 0.0
    
    avg_return = np.mean(returns)
    std_return = np.std(returns)
    
    return (avg_return - risk_free_rate) / std_return * np.sqrt(252)

def calculate_daily_volatility(returns: Union[List[float], np.ndarray]) -> float:
    """
    Calculate Daily Volatility (DV).
    DV = std(r_t)
    """
    returns = np.array(returns)
    return np.std(returns)

def calculate_annualized_volatility(returns: Union[List[float], np.ndarray]) -> float:
    """
    Calculate Annualized Volatility (AV).
    AV = std(r_t) * sqrt(252)
    """
    returns = np.array(returns)
    return np.std(returns) * np.sqrt(252)

def calculate_max_drawdown(returns: Union[List[float], np.ndarray]) -> float:
    """
    Calculate Maximum Drawdown (MD).
    MD = max((Peak - Trough) / Peak)
    """
    returns = np.array(returns)
    # Convert returns to cumulative wealth index
    wealth_index = np.cumprod(1 + returns)
    
    # Calculate peak value at each point
    peaks = np.maximum.accumulate(wealth_index)
    
    # Calculate drawdown at each point
    drawdowns = (peaks - wealth_index) / peaks
    
    return np.max(drawdowns)

def report_financial_metrics(returns: Union[List[float], np.ndarray]):
    """
    Print a summary of financial metrics.
    """
    cr = calculate_cumulative_return(returns)
    sr = calculate_sharpe_ratio(returns)
    dv = calculate_daily_volatility(returns)
    av = calculate_annualized_volatility(returns)
    md = calculate_max_drawdown(returns)
    
    print(f"--- Financial Performance Summary ---")
    print(f"Cumulative Return (CR):    {cr*100:.2f}%")
    print(f"Sharpe Ratio (SR):         {sr:.4f}")
    print(f"Daily Volatility (DV):     {dv*100:.4f}%")
    print(f"Annualized Volatility (AV): {av*100:.2f}%")
    print(f"Maximum Drawdown (MD):     {md*100:.2f}%")
    print(f"------------------------------------")

if __name__ == "__main__":
    # Demo with dummy return data
    # Simulate 252 days of daily returns (average 0.05% per day, std 1%)
    np.random.seed(42)
    demo_returns = np.random.normal(0.0005, 0.01, 252)
    
    print("Demo with simulated returns (252 days):")
    report_financial_metrics(demo_returns)
