import math, random

qqq_vol = 0.2204
inrg_vol_eur = 0.2148
fx_vol = 0.09
inrg_vol_usd = math.sqrt(inrg_vol_eur**2 + fx_vol**2)
corr = 0.38
us_rate = 0.0364
ecb_rate = 0.0200
rate_spread = us_rate - ecb_rate
eur_usd = 1.17159

def nppf(p):
    if p <= 0: return -8.0
    if p >= 1: return 8.0
    if p == 0.5: return 0.0
    if p > 0.5: return -nppf(1 - p)
    t = math.sqrt(-2 * math.log(p))
    return -(t - (2.515517 + 0.802853*t + 0.010328*t**2) / (1 + 1.432788*t + 0.189269*t**2 + 0.001308*t**3))

def pv(w1, v1, w2, v2, c):
    return math.sqrt(w1**2 * v1**2 + w2**2 * v2**2 + 2 * w1 * w2 * c * v1 * v2)

z95 = nppf(0.05)

# 1. Portfolio Volatility
vo = pv(0.6, qqq_vol, 0.4, inrg_vol_usd, corr)
vn = pv(0.4, qqq_vol, 0.6, inrg_vol_usd, corr)
print("INRG.L USD vol (incl FX):", round(inrg_vol_usd*100, 2), "%")
print("Old portfolio (60/40) vol:", round(vo*100, 2), "%")
print("New portfolio (40/60) vol:", round(vn*100, 2), "%")
print("Vol change:", round((vn-vo)*100, 2), "pp")

# 2. VaR
dvo = vo / math.sqrt(252)
dvn = vn / math.sqrt(252)
print("\nDaily VaR 95% - Old:", round(abs(z95)*dvo*100, 2), "%")
print("Daily VaR 95% - New:", round(abs(z95)*dvn*100, 2), "%")
print("Annual VaR 95% - Old:", round(abs(z95)*vo*100, 2), "%")
print("Annual VaR 95% - New:", round(abs(z95)*vn*100, 2), "%")

# 3. FX Risk
voh = pv(0.6, qqq_vol, 0.4, inrg_vol_eur, corr)
vnh = pv(0.4, qqq_vol, 0.6, inrg_vol_eur, corr)
fdo = vo - voh
fdn = vn - vnh
print("\nFX drag - Old:", round(fdo*100, 2), "pp")
print("FX drag - New:", round(fdn*100, 2), "pp")
print("FX drag increase:", round((fdn-fdo)*100, 2), "pp")
fxv = abs(z95) * 0.085
print("95% GBP/USD annual move: +/-", round(fxv*100, 2), "%")
print("New port (60% INRG) FX impact: +/-", round(fxv*0.6*100, 2), "%")

# 4. Sharpe
r = 0.15
so_sh = (r - us_rate) / vo
sn_sh = (r - us_rate) / vn
print("\nSharpe - Old:", round(so_sh, 3))
print("Sharpe - New:", round(sn_sh, 3))

# 5. Monte Carlo
random.seed(42)
N = 10000
L11 = qqq_vol
L21 = corr * inrg_vol_usd
L22 = math.sqrt(inrg_vol_usd**2 - L21**2)

def rn():
    u1 = random.random()
    u2 = random.random()
    return math.sqrt(-2*math.log(u1)) * math.cos(2*math.pi*u2)

po = []
pn = []
for _ in range(N):
    z1 = rn()
    z2 = rn()
    r1 = r + L11 * z1
    r2 = r + L21 * z1 + L22 * z2
    po.append(0.6*r1 + 0.4*r2)
    pn.append(0.4*r1 + 0.6*r2)

def st(lst):
    n = len(lst)
    m = sum(lst) / n
    sl = sorted(lst)
    v = sum((x-m)**2 for x in lst) / n
    return m, sl[n//2], math.sqrt(v), sl[int(n*0.05)], sl[0], sum(1 for x in lst if x > 0) / n

mo, medo, sod, v5o, mno, ppo = st(po)
mn, medn, snd, v5n, mnn, ppn = st(pn)

print("\nMonte Carlo (10000 sims, 1-year)")
print("Old (60/40): mean=", round(mo*100,2), "% med=", round(medo*100,2), "% std=", round(sod*100,2), "% VaR5%=", round(v5o*100,2), "% min=", round(mno*100,2), "% pos=", round(ppo*100,1), "%")
print("New (40/60): mean=", round(mn*100,2), "% med=", round(medn*100,2), "% std=", round(snd*100,2), "% VaR5%=", round(v5n*100,2), "% min=", round(mnn*100,2), "% pos=", round(ppn*100,1), "%")

d = [b - a for a, b in zip(po, pn)]
md = sum(d) / len(d)
pd = sum(1 for x in d if x > 0) / len(d)
print("\nNew > Old prob:", round(pd*100, 1), "%")
print("Mean return diff:", round(md*100, 2), "%")

rf = us_rate
dso = math.sqrt(sum(min(x-rf, 0)**2 for x in po) / N)
dsn = math.sqrt(sum(min(x-rf, 0)**2 for x in pn) / N)
print("Sortino - Old:", round((mo-rf)/dso, 3))
print("Sortino - New:", round((mn-rf)/dsn, 3))
