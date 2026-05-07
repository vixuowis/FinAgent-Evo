
import json
import numpy as np
from collections import defaultdict

def analyze_scenario_stats():
    with open('src/benchmarks/results/final_consolidated_results.json', 'r') as f:
        data = json.load(f)
    
    themes = [
        "Equity Research & Valuation",
        "Macro Strategy & Forex",
        "Portfolio Risk & Sector Rotation",
        "Crypto & Alternative Assets",
        "Event-Driven & Policy Analysis",
        "Fixed Income & Credit Analysis",
        "Commodities & Supply Chain",
        "ESG & Sustainable Investing",
        "Quantitative Factors & Technicals",
        "Global Banking & Fintech"
    ]
    
    variants = ["EvoFinAgent", "wo_evolution", "wo_memory", "wo_orchestration"]
    
    results = defaultdict(lambda: defaultdict(list))
    
    for tid, scores in data.items():
        t_num = int(tid[1:])
        theme_idx = (t_num - 1) // 30
        if theme_idx < len(themes):
            theme_name = themes[theme_idx]
            for v in variants:
                if v in scores:
                    results[theme_name][v].append(scores[v])
                else:
                    results[theme_name][v].append(0.0)

    print("| Scenario | EvoFinAgent | wo_evolution | wo_memory | wo_orchestration |")
    print("| :--- | :---: | :---: | :---: | :---: |")
    
    for theme in themes:
        row = f"| {theme} | "
        for v in variants:
            avg = np.mean(results[theme][v])
            row += f"{avg:.1f} | "
        print(row)

if __name__ == "__main__":
    analyze_scenario_stats()
