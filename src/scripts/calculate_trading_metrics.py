import numpy as np
import pandas as pd

def calculate_drawdown(returns):
    """Calculate the maximum drawdown of a series of returns."""
    cumulative_returns = (1 + returns).cumprod()
    peak = cumulative_returns.expanding(min_periods=1).max()
    drawdown = (cumulative_returns / peak) - 1
    return drawdown.min()

def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """Calculate the annualized Sharpe Ratio."""
    excess_returns = returns - risk_free_rate / 252
    return np.sqrt(252) * excess_returns.mean() / excess_returns.std()

def calculate_correlation(asset1_returns, asset2_returns):
    """Calculate the correlation between two assets."""
    return np.corrcoef(asset1_returns, asset2_returns)[0, 1]

# Example usage in PythonREPL:
# from src.scripts.calculate_trading_metrics import calculate_drawdown
# drawdown = calculate_drawdown(np.random.normal(0.001, 0.02, 252))
