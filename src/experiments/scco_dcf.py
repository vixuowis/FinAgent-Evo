
import numpy as np

def f(n):
    return "{:,.1f}".format(n)

base_revenue = 13420.0
base_cost = 5359.2
sga = 137.8
da = 868.4
exploration = 52.8
ocf = 4752.1
capex = 1325.3
fcf = ocf - capex
tax_rate = 0.363
shares = 838.2
net_debt = 1841.4
wacc = 0.085
tg = 0.02
current_price = 180.43

def calc_dcf(fcf_y1, growth_rates, w, t, years=3):
    pv_fcf = 0
    fcfs = []
    current = fcf_y1
    for i in range(years):
        g = growth_rates[i] if i < len(growth_rates) else growth_rates[-1]
        fv = current * (1 + g)
        fcfs.append(fv)
        pv = fv / ((1 + w) ** (i + 1))
        pv_fcf += pv
        current = fv
    tf = fcfs[-1] * (1 + t)
    tv = tf / (w - t)
    pv_tv = tv / ((1 + w) ** years)
    ev = pv_fcf + pv_tv
    eq = ev - net_debt
    vps = eq / shares
    return fcfs, pv_fcf, tv, pv_tv, ev, eq, vps

print("SECTION 4: DCF STRESS TEST")
print("=" * 60)

base_gr = [0.03, 0.03, 0.02]
stress_rev = base_revenue * 0.95 * 1.03
cost_change = base_cost * 0.60 * (-0.05) + base_cost * 0.15 * 0.08
stress_cost = base_cost + cost_change
stress_ebit = stress_rev - stress_cost - sga - exploration
stress_nopat = stress_ebit * (1 - tax_rate)
stress_ocf = stress_nopat + da
stress_fcf = stress_ocf - capex * 1.05
stress_gr = [0.01, 0.02, 0.02]

bull_rev = base_revenue * 0.98 * 1.10
bull_cost = base_cost * 0.99
bull_ebit = bull_rev - bull_cost - sga - exploration
bull_nopat = bull_ebit * (1 - tax_rate)
bull_ocf = bull_nopat + da
bull_fcf = bull_ocf - capex
bull_gr = [0.05, 0.04, 0.03]

scenarios = [
    ("BASE", fcf, base_gr, "Normal ops"),
    ("STRESS", stress_fcf, stress_gr, "Strike: vol-5pct log+8pct"),
    ("BULL", bull_fcf, bull_gr, "Price+10pct vol-2pct"),
]

for name, fcf_y1, gr, desc in scenarios:
    fcfs, pv_fcf, tv, pv_tv, ev, eq, vps = calc_dcf(fcf_y1, gr, wacc, tg)
    print()
    print(name + ": " + desc)
    print("  FCF Y1: $" + f(fcf_y1) + "M")
    print("  FCF Y1-Y3: $" + f(fcfs[0]) + " / $" + f(fcfs[1]) + " / $" + f(fcfs[2]) + "M")
    print("  EV: $" + f(ev) + "M | Equity: $" + f(eq) + "M | VPS: $" + str(round(vps, 2)))
    print("  vs $" + str(current_price) + ": " + str(round((vps / current_price - 1) * 100, 1)) + "pct")

print()
print("SENSITIVITY: WACC vs FCF Change")
wacc_range = [0.07, 0.08, 0.085, 0.09, 0.10]
fcf_chg = [-0.15, -0.10, -0.05, 0.00, 0.05, 0.10]
h = "WACC  |"
for c in fcf_chg:
    h += " %+.0f%% |" % (c * 100)
print(h)
print("-" * len(h))
for w in wacc_range:
    r = str(round(w * 100, 1)) + "pct |"
    for c in fcf_chg:
        _, _, _, _, _, _, vps = calc_dcf(fcf * (1 + c), [0.02, 0.02, 0.02], w, tg)
        r += " $%4.0f |" % vps
    print(r)

print()
print("MONTE CARLO (10,000 iter)")
np.random.seed(123)
n = 10000
cc = np.random.normal(0.02, 0.12, n)
vc = np.random.normal(-0.02, 0.04, n)
kc = np.random.normal(0.03, 0.05, n)
ws = np.random.normal(0.085, 0.01, n)
sv = []
for i in range(n):
    sr = base_revenue * (1 + cc[i]) * (1 + vc[i])
    sc = base_cost * (1 + kc[i])
    se = sr - sc - sga - exploration
    sn = max(se * (1 - tax_rate), 0)
    so = sn + da
    sx = capex * (1 + kc[i] * 0.5)
    sf = so - sx
    w = ws[i]
    if sf > 0 and w > tg:
        _, _, _, _, _, _, vps = calc_dcf(sf, [0.02, 0.02, 0.02], w, tg)
        sv.append(vps)
sv = np.array(sv)
print("Mean: $" + str(round(np.mean(sv), 2)))
print("Median: $" + str(round(np.median(sv), 2)))
print("Std: $" + str(round(np.std(sv), 2)))
print("5th: $" + str(round(np.percentile(sv, 5), 2)))
print("25th: $" + str(round(np.percentile(sv, 25), 2)))
print("75th: $" + str(round(np.percentile(sv, 75), 2)))
print("95th: $" + str(round(np.percentile(sv, 95), 2)))
print("Min: $" + str(round(np.min(sv), 2)))
print("Max: $" + str(round(np.max(sv), 2)))
print("P(IV>$" + str(current_price) + "): " + str(round(np.mean(sv > current_price) * 100, 1)) + "pct")
print()
print("DCF RANGE: Bear $" + str(round(np.percentile(sv, 5), 2)) + " | Base $" + str(round(np.median(sv), 2)) + " | Bull $" + str(round(np.percentile(sv, 95), 2)))
