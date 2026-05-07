import json, urllib.request, math

url = "https://oss.qveris.cn/tool_result_cache%2F20260425%2Ffinancialmodelingprep.historical_price_eod.non_split_adjusted.retrieve.v1.4c43e8ed%2F3925c0e11d054ebeb68ce651665358f2.json?OSSAccessKeyId=LTAI5tM3qNRZSgSrg1iSTALm&Expires=1777154681&Signature=PN11VqhHYNov%2FkLYUViwHQ5yNNU%3D"
resp = urllib.request.urlopen(url)
data = json.loads(resp.read().decode())
filtered = [d for d in data if d['date'] >= '2026-01-24']
prices = [d['adjClose'] for d in filtered]
volumes = [d['volume'] for d in filtered]
highs = [d['adjHigh'] for d in filtered]
lows = [d['adjLow'] for d in filtered]

print("Trading days:", len(filtered))
print("Range:", filtered[-1]['date'], "to", filtered[0]['date'])
print("Latest Close: $%.2f" % prices[0])
print("Oldest Close: $%.2f" % prices[-1])
print("90D High: $%.2f" % max(highs))
print("90D Low: $%.2f" % min(lows))
print("Avg Volume: %d" % (sum(volumes) / len(volumes)))
ret = ((prices[0] - prices[-1]) / prices[-1]) * 100
print("90D Return: %.2f%%" % ret)

returns = [(prices[i] - prices[i+1]) / prices[i+1] for i in range(len(prices) - 1)]
mr = sum(returns) / len(returns)
vr = sum((r - mr) ** 2 for r in returns) / (len(returns) - 1)
dv = math.sqrt(vr)
av = dv * math.sqrt(252)
print("Daily Volatility: %.2f%%" % (dv * 100))
print("Annualized Volatility: %.2f%%" % (av * 100))

print("\n=== Last 10 Trading Days ===")
for d in filtered[:10]:
    chg = ((d['adjClose'] - d['adjOpen']) / d['adjOpen']) * 100
    print("  %s O:%.2f H:%.2f L:%.2f C:%.2f Vol:%d Chg:%+.2f%%" % (d['date'], d['adjOpen'], d['adjHigh'], d['adjLow'], d['adjClose'], d['volume'], chg))
