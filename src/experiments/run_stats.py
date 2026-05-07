import urllib.request, json, csv, os, math

url_q = "https://oss.qveris.cn/tool_result_cache%2F20260430%2Ffinancialmodelingprep.historical_price_eod.non_split_adjusted.retrieve.v1.4c43e8ed%2Fa6c54f1d05bb4544980f73d8e9c7a74a.json?OSSAccessKeyId=LTAI5tM3qNRZSgSrg1iSTALm&Expires=1777552593&Signature=AHgxYFOB4%2F8QE00fcqzoFM5V3%2F4%3D"
url_f = "https://oss.qveris.cn/tool_result_cache%2F20260430%2Ffinancialmodelingprep.historical_price_eod.non_split_adjusted.retrieve.v1.4c43e8ed%2F014ce2fae94248c38898fac8a7e330d7.json?OSSAccessKeyId=LTAI5tM3qNRZSgSrg1iSTALm&Expires=1777552593&Signature=C%2BeEobP45BQsNvKZ7AlIfiPLNYY%3D"
url_u = "https://oss.qveris.cn/tool_result_cache%2F20260430%2Ffinancialmodelingprep.historical_price_eod.non_split_adjusted.retrieve.v1.4c43e8ed%2F338503f0d8e6420abd9dbc7fada03110.json?OSSAccessKeyId=LTAI5tM3qNRZSgSrg1iSTALm&Expires=1777552592&Signature=LEaSWZgWSlAalvwHNxXyHQNw%2BUc%3D"

def do_fetch(u):
    r = urllib.request.Request(u)
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read().decode("utf-8"))

qqq_d = do_fetch(url_q)
xlf_d = do_fetch(url_f)
xlu_d = do_fetch(url_u)
print("Fetched QQQ={}, XLF={}, XLU={}".format(len(qqq_d), len(xlf_d), len(xlu_d)))

ddir = os.path.join(os.getcwd(), "data")
os.makedirs(ddir, exist_ok=True)

for sym, dat in [("QQQ", qqq_d), ("XLF", xlf_d), ("XLU", xlu_d)]:
    recs = sorted(dat, key=lambda x: x["date"])
    p = os.path.join(ddir, sym + "_1y_ohlcv.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "high", "low", "close", "volume"])
        for r in recs:
            w.writerow([r["date"], r["adjOpen"], r["adjHigh"], r["adjLow"], r["adjClose"], r["volume"]])
    print("Saved {} ({} rows)".format(p, len(recs)))

for sym, dat in [("QQQ", qqq_d), ("XLF", xlf_d), ("XLU", xlu_d)]:
    recs = sorted(dat, key=lambda x: x["date"])
    d = [r["date"] for r in recs]
    c = [r["adjClose"] for r in recs]
    lo = [r["adjLow"] for r in recs]
    hi = [r["adjHigh"] for r in recs]
    vo = [r["volume"] for r in recs]
    lr = [math.log(c[i]/c[i-1]) for i in range(1, len(c))]
    mn = sum(lr)/len(lr)
    sd = math.sqrt(sum((x-mn)**2 for x in lr)/(len(lr)-1))
    av = sd*math.sqrt(252)
    print()
    print("=" * 60)
    print("  {} Summary Statistics".format(sym))
    print("=" * 60)
    print("  Trading Days:        {}".format(len(recs)))
    print("  Date Range:          {} -> {}".format(d[0], d[-1]))
    print("  Price Range (Low):   ${:.2f}".format(min(lo)))
    print("  Price Range (High):  ${:.2f}".format(max(hi)))
    print("  Avg Daily Volume:    {:,.0f}".format(sum(vo)/len(vo)))
    print("  Mean Daily Return:   {:.6f}%".format(mn*100))
    print("  Std Daily Return:    {:.6f}%".format(sd*100))
    print("  Annualized Vol:      {:.2f}%".format(av*100))
