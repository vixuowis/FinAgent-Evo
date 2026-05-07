import matplotlib.pyplot as plt
import numpy as np

# 1. Cost vs Performance Scatter (Pareto Curve)
models = ['FinMem', 'FinAgent', 'EvoFinAgent', 'ReAct']
costs = [0.08, 0.12, 0.22, 0.25]
scores = [24.2, 28.4, 39.5, 4.1]

fig, ax = plt.subplots(figsize=(6, 4))

# Set up colors and markers
colors = ['#4C72B0', '#4C72B0', '#C44E52', '#8C8C8C']
markers = ['o', 'o', '*', 'X']
sizes = [100, 100, 250, 100]

# Plot each point
for i in range(len(models)):
    ax.scatter(costs[i], scores[i], color=colors[i], marker=markers[i], s=sizes[i], zorder=3, edgecolors='black', linewidths=0.5)

# Annotate points
for i, txt in enumerate(models):
    if txt == 'EvoFinAgent':
        ax.annotate(txt, (costs[i], scores[i]), xytext=(-25, 12), textcoords='offset points', fontweight='bold', color='#C44E52')
    elif txt == 'ReAct':
        ax.annotate(txt, (costs[i], scores[i]), xytext=(5, 5), textcoords='offset points')
    else:
        ax.annotate(txt, (costs[i], scores[i]), xytext=(8, -8), textcoords='offset points')

# Draw Pareto frontier line connecting optimal points (FinMem -> FinAgent -> EvoFinAgent)
pareto_costs = [0.08, 0.12, 0.22]
pareto_scores = [24.2, 28.4, 39.5]
ax.plot(pareto_costs, pareto_scores, linestyle='--', color='#55A868', linewidth=2, label='Pareto Frontier', zorder=2)

ax.set_xlabel('Avg. Cost per Task ($)')
ax.set_ylabel('Judge Score')
ax.set_title('Cost vs. Performance (Pareto Frontier)')
ax.grid(True, linestyle=':', alpha=0.6, zorder=1)
ax.legend(loc='upper right')
ax.set_xlim(0.05, 0.30)
ax.set_ylim(0, 45)

fig.tight_layout()
plt.savefig('/Users/vix/Code/FinAgent/neurips_paper/figures/fig_cost_efficiency.pdf')
plt.close()

# 2. Judge Score by Difficulty (Table 2)
labels = ['Easy\n(1-2 tools)', 'Medium\n(3-4 tools)', 'Hard\n(>= 5 tools)']
full_hs = [46.2, 38.4, 33.9]
finagent_hs = [33.8, 27.6, 23.8]
finmem_hs = [27.1, 24.8, 20.7]

x = np.arange(len(labels))
width = 0.25

fig, ax = plt.subplots(figsize=(6, 4))
rects1 = ax.bar(x - width, full_hs, width, label='EvoFinAgent', color='#4C72B0')
rects2 = ax.bar(x, finagent_hs, width, label='FinAgent', color='#55A868')
rects3 = ax.bar(x + width, finmem_hs, width, label='FinMem', color='#C44E52')

ax.set_ylabel('Judge Score')
ax.set_title('Judge Score by Task Complexity')
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylim(0, 55)
ax.legend(loc='upper right')

fig.tight_layout()
plt.savefig('/Users/vix/Code/FinAgent/neurips_paper/figures/fig_hard_success.pdf')
plt.close()
