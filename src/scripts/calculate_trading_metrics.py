import numpy as np

def calculate_cumulative_return(returns):
    """Calculate the cumulative return of a series of returns."""
    return (1 + returns).prod() - 1

def calculate_drawdown(returns):
    """Calculate the maximum drawdown of a series of returns."""
    rets = np.asarray(returns, dtype=float)
    if rets.size == 0:
        return 0.0
    cumulative_returns = np.cumprod(1.0 + rets)
    peak = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns / peak) - 1.0
    return float(np.min(drawdown))

def calculate_sharpe_ratio(returns, risk_free_rate=0.02, trading_days=252):
    """Calculate the annualized Sharpe Ratio."""
    if len(returns) < 2 or np.std(returns) == 0:
        return 0.0
    excess_returns = returns - risk_free_rate / trading_days
    return np.sqrt(trading_days) * np.mean(excess_returns) / np.std(returns)

def calculate_annualized_volatility(returns, trading_days=252):
    """Calculate the annualized volatility."""
    if len(returns) < 2:
        return 0.0
    return np.std(returns) * np.sqrt(trading_days)

def calculate_correlation(asset1_returns, asset2_returns):
    """Calculate the correlation between two assets."""
    return np.corrcoef(asset1_returns, asset2_returns)[0, 1]

def calculate_all_metrics(returns, risk_free_rate=0.02, trading_days=252):
    """Calculate all standard financial metrics used in InvestorBench."""
    rets = np.array(returns)
    return {
        "cr": calculate_cumulative_return(rets),
        "sr": calculate_sharpe_ratio(rets, risk_free_rate, trading_days),
        "av": calculate_annualized_volatility(rets, trading_days),
        "mdd": calculate_drawdown(rets)
    }
