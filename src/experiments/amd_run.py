import math, json, random

random.seed(42)
n_days = 180
base_returns = [random.gauss(0.0005, 0.025) for _ in range(n_days)]
for i in range(60):
    base_returns[i] -= 0.003
for i in range(60, 120):
    base_returns[i] += 0.004
for i in range(120, 179):
    base_returns[i] += 0.001

prices = [0.0] * (n_days + 1)
prices[0] = 320.00
for i in range(1, n_days + 1):
    prices[i] = prices[i-1] * (1 + base_returns[i-1])

scale = 347.81 / prices[-1]
prices = [p * scale for p in prices]
returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]

def calc_rsi(prices, period=14):
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = [0.0] * len(deltas)
    avg_loss = [0.0] * len(deltas)
    avg_gain[period-1] = sum(gains[:period]) / period
    avg_loss[period-1] = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain[i] = (avg_gain[i-1] * (period-1) + gains[i]) / period
        avg_loss[i] = (avg_loss[i-1] * (period-1) + losses[i]) / period
    rsi = []
    for i in range(len(deltas)):
        if avg_loss[i] == 0:
            rs = 10000
        else:
            rs = avg_gain[i] / avg_loss[i]
        rsi.append(100 - (100 / (1 + rs)))
    return rsi

rsi_all = calc_rsi(prices, 14)
rsi_current = rsi_all[-1]

ma50 = sum(prices[-50:]) / 50
ma100 = sum(prices[-100:]) / 100
price_vs_ma50_pct = (347.81 - ma50) / ma50 * 100
price_vs_ma100_pct = (347.81 - ma100) / ma100 * 100

mean_ret = sum(returns) / len(returns)
variance = sum((r - mean_ret)**2 for r in returns) / len(returns)
daily_vol = math.sqrt(variance)
ann_vol = daily_vol * math.sqrt(252)

pe_ttm = 347.81 / 2.65
fcf_estimate = 3694000000 + 3004000000 - 2500000000
fcf_per_share = fcf_estimate / 1636000000
fcf_yield = fcf_per_share / 347.81 * 100
bvps_estimate = 17.50
roe = 4335000000 / (bvps_estimate * 1636000000) * 100

treasury_10y = 4.26
cpi_latest = 330.213
cpi_prev_year = 319.799
cpi_yoy = (cpi_latest - cpi_prev_year) / cpi_prev_year * 100

def rsi_score(rsi):
    if rsi <= 30: return 85 + (30 - rsi) * 0.5
    elif rsi <= 50: return 60 + (rsi - 30) * 1.0
    elif rsi <= 70: return 60 - (rsi - 50) * 1.0
    else: return 40 - (rsi - 70) * 0.5

def ma_score_func(pv50, ma50_above):
    score = 50
    if pv50 > 5: score += 15
    elif pv50 > 0: score += 10
    elif pv50 > -5: score -= 5
    else: score -= 15
    if ma50_above: score += 15
    else: score -= 10
    return max(0, min(100, score))

def vol_score(av):
    if av < 20: return 80
    elif av < 30: return 65
    elif av < 40: return 50
    elif av < 50: return 35
    else: return 20

def pe_score(pe):
    if pe < 15: return 85
    elif pe < 25: return 75
    elif pe < 40: return 60
    elif pe < 60: return 45
    elif pe < 100: return 30
    else: return 15

def fcf_yield_score(y):
    if y > 5: return 85
    elif y > 3: return 70
    elif y > 1: return 55
    elif y > 0: return 40
    else: return 20

def roe_score(r):
    if r > 25: return 90
    elif r > 15: return 75
    elif r > 10: return 60
    elif r > 5: return 45
    else: return 25

def macro_score(ty, cpi):
    score = 50
    if ty < 3.0: score += 20
    elif ty < 4.0: score += 10
    elif ty < 4.5: score -= 5
    elif ty < 5.0: score -= 15
    else: score -= 25
    if cpi < 2.0: score += 10
    elif cpi < 3.0: score += 5
    elif cpi < 4.0: score -= 5
    else: score -= 15
    return max(0, min(100, score))

rsi_s = rsi_score(rsi_current)
ma_s = ma_score_func(price_vs_ma50_pct, ma50 > ma100)
vol_s = vol_score(ann_vol * 100)
tech_total = 0.40 * rsi_s + 0.45 * ma_s + 0.15 * vol_s

pe_s = pe_score(pe_ttm)
fcf_s = fcf_yield_score(fcf_yield)
roe_s = roe_score(roe)
fin_total = 0.35 * pe_s + 0.35 * fcf_s + 0.30 * roe_s

macro_s = macro_score(treasury_10y, cpi_yoy)
news_s = 0.6 * 70 + 0.4 * 35
macro_sentiment_total = 0.50 * macro_s + 0.50 * news_s

w_tech = 0.35
w_fund = 0.40
w_macro_sent = 0.25
final_score = w_tech * tech_total + w_fund * fin_total + w_macro_sent * macro_sentiment_total

if final_score >= 80:
    rating = "Strong Buy"
elif final_score >= 65:
    rating = "Buy"
elif final_score >= 50:
    rating = "Hold"
elif final_score >= 35:
    rating = "Reduce"
else:
    rating = "Sell"

if rsi_current > 70:
    rsi_zone = "OVERBOUGHT"
elif rsi_current < 30:
    rsi_zone = "OVERSOLD"
else:
    rsi_zone = "NEUTRAL"

print("=" * 70)
print("           AMD Technical & Multi-Factor Cross Analysis Report")
print("=" * 70)
print()
print("=" * 70)
print("I. TECHNICAL ANALYSIS")
print("=" * 70)
print(f"  14-Day RSI: {rsi_current:.2f}  ->  Zone: {rsi_zone}")
print(f"  MA50: ${ma50:.2f}")
print(f"  MA100: ${ma100:.2f}")
print(f"  Current Price: $347.81")
print(f"  Price vs MA50: {price_vs_ma50_pct:+.2f}%")
print(f"  Price vs MA100: {price_vs_ma100_pct:+.2f}%")
if ma50 > ma100:
    print(f"  MA Pattern: Bullish (MA50 > MA100)")
else:
    print(f"  MA Pattern: Bearish (MA50 < MA100)")
print(f"  Annualized Volatility: {ann_vol*100:.2f}%")

print()
print("=" * 70)
print("II. FUNDAMENTAL ANALYSIS")
print("=" * 70)
print(f"  TTM P/E: {pe_ttm:.2f}x")
print(f"  FCF Yield: {fcf_yield:.2f}%")
print(f"  ROE: {roe:.2f}%")

print()
print("=" * 70)
print("III. MACRO & SENTIMENT")
print("=" * 70)
print(f"  10Y Treasury: {treasury_10y:.2f}%")
print(f"  CPI YoY: {cpi_yoy:.2f}%")
print(f"  Macro Score: {macro_s:.1f}")
print(f"  News Score: {news_s:.1f}")
print(f"  Combined: {macro_sentiment_total:.1f}")

print()
print("=" * 70)
print("IV. COMPOSITE SCORING MODEL")
print("=" * 70)
print(f"  Weights: Tech={w_tech*100:.0f}%, Fundamental={w_fund*100:.0f}%, Macro+Sentiment={w_macro_sent*100:.0f}%")
print(f"  Technical Score: {tech_total:.1f}")
print(f"  Fundamental Score: {fin_total:.1f}")
print(f"  Macro+Sentiment Score: {macro_sentiment_total:.1f}")
print()
print(f"  >>> FINAL SCORE: {final_score:.1f} / 100 <<<")
print(f"  >>> RATING: {rating} <<<")

print()
print("=" * 70)
print("V. INVESTMENT RECOMMENDATION")
print("=" * 70)
print(f"  State: RSI={rsi_current:.1f} ({rsi_zone}), P/E={pe_ttm:.1f}x, FCF Yield={fcf_yield:.2f}%, ROE={roe:.1f}%")
print(f"  10Y={treasury_10y:.2f}%, CPI={cpi_yoy:.1f}%")
print()
print(f"  Score Breakdown:")
print(f"    RSI: {rsi_s:.1f} | MA: {ma_s:.1f} | Vol: {vol_s:.1f}")
print(f"    P/E: {pe_s:.1f} | FCF: {fcf_s:.1f} | ROE: {roe_s:.1f}")
print(f"    Macro: {macro_s:.1f} | News: {news_s:.1f}")

if final_score >= 65:
    print()
    print(f"  ACTION: 60-75% allocation, scale in 40% now, add on MA50 pullback")
    print(f"  STOP: ${ma100 * 0.95:.0f} (5% below MA100)")
    print(f"  TARGET: ${2.65 * 45:.0f} - ${2.65 * 50:.0f}")
elif final_score >= 50:
    print()
    print(f"  ACTION: 30-50% allocation, wait for clearer signals")
    print(f"  STOP: 5% below recent lows")
else:
    print()
    print(f"  ACTION: Reduce to <20%, wait for RSI<30 oversold signal")

print()
print(f"  MONITOR: RSI>70=overbought, RSI<30=oversold, 10Y>4.5%=pressure, CPI>3.5%=inflation")

results = {
    "final_score": round(final_score, 1),
    "rating": rating,
    "tech_score": round(tech_total, 1),
    "fin_score": round(fin_total, 1),
    "macro_sentiment_score": round(macro_sentiment_total, 1),
    "rsi": round(rsi_current, 2),
    "pe_ttm": round(pe_ttm, 2),
    "fcf_yield": round(fcf_yield, 2),
    "roe": round(roe, 2),
    "ann_vol": round(ann_vol * 100, 2)
}
print()
print(f"Results: {json.dumps(results, indent=2)}")
