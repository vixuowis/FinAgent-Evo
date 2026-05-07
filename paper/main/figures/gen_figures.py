import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np
from pathlib import Path

OUT = Path(__file__).parent
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.linewidth": 0.8,
    "pdf.fonttype": 42,
})

# ── Figure 1: System Architecture ──────────────────────────────────────────
def fig_architecture():
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")

    BLUE   = "#4472C4"; ORANGE = "#ED7D31"; GREEN  = "#70AD47"
    PURPLE = "#7030A0"; GRAY   = "#8496A9"

    def box(ax, x, y, w, h, label, color, fontsize=8.5):
        r = mpatches.FancyBboxPatch((x-w/2, y-h/2), w, h,
            boxstyle="round,pad=0.08", linewidth=0.9,
            edgecolor=color, facecolor=color+"22")
        ax.add_patch(r)
        ax.text(x, y, label, ha="center", va="center",
                fontsize=fontsize, color="#1a1a1a", fontweight="bold",
                multialignment="center")

    def arrow(ax, x0, y0, x1, y1, color="#555", style="-|>", lw=1.2, dashed=False):
        ls = (0,(4,3)) if dashed else "solid"
        ax.annotate("", xy=(x1,y1), xytext=(x0,y0),
            arrowprops=dict(arrowstyle=style, color=color,
                            lw=lw, linestyle=ls,
                            connectionstyle="arc3,rad=0.0"))

    # nodes
    box(ax, 1.0, 4.0, 1.6, 0.65, "Task $x$\n(NL query)",       GRAY)
    box(ax, 9.0, 4.0, 1.6, 0.65, "Answer $y$\n(verified)",      GRAY)
    box(ax, 5.0, 4.0, 2.2, 0.65, "DAG Orchestrator\n(structured plan)", GREEN)
    box(ax, 2.8, 2.2, 2.0, 0.65, "Skill Library $\\mathcal{S}$\n(prompt genotypes)", BLUE)
    box(ax, 7.2, 2.2, 2.0, 0.65, "Executor\n(topological order)", GREEN)
    box(ax, 7.2, 0.9, 2.0, 0.65, "Verification\n(schema + REPL)", GREEN)
    box(ax, 2.8, 0.9, 2.2, 0.65, "Hierarchical Memory\nworking/episodic/procedural", ORANGE)
    box(ax, 0.7, 2.2, 1.4, 0.65, "Evolution\nEngine", PURPLE)

    # arrows
    arrow(ax, 1.8, 4.0, 3.9, 4.0, GRAY)          # task -> orch
    arrow(ax, 6.1, 4.0, 8.2, 4.0, GRAY)           # orch -> answer (via exec path)
    arrow(ax, 4.2, 3.68, 3.3, 2.53, GREEN)        # orch -> skills
    arrow(ax, 5.8, 3.68, 6.7, 2.53, GREEN)        # orch -> exec
    arrow(ax, 3.8, 2.2, 6.2, 2.2, BLUE)           # skills -> exec
    arrow(ax, 7.2, 1.88, 7.2, 1.23, GREEN)        # exec -> verify
    arrow(ax, 8.2, 0.9, 9.0, 3.68, GREEN)         # verify -> answer
    arrow(ax, 3.9, 0.9, 4.5, 3.68, ORANGE,        # memory -> orch (rules)
          dashed=False)
    arrow(ax, 7.2, 0.58, 5.0, 1.23, ORANGE,       # verify -> memory (trajectory)
          dashed=True)
    arrow(ax, 1.8, 0.9, 1.4, 1.88, PURPLE,        # memory -> evo
          dashed=True)
    arrow(ax, 1.0, 2.53, 1.8, 2.2, PURPLE,        # evo -> skills
          dashed=True)

    # edge labels
    ax.text(4.15, 2.6, "rules", fontsize=7, color=ORANGE, style="italic")
    ax.text(6.0,  0.6, "trajectory", fontsize=7, color=ORANGE, style="italic")
    ax.text(1.05, 1.3, "feedback", fontsize=7, color=PURPLE, style="italic")
    ax.text(1.05, 2.45,"mutate",   fontsize=7, color=PURPLE, style="italic")

    fig.tight_layout(pad=0.3)
    fig.savefig(OUT / "fig_architecture.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_architecture.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig_architecture done")


# ── Figure 2: Main Results Bar Chart ───────────────────────────────────────
def fig_results():
    methods = ["ReAct", "FinMem", "FinAgent", "EvoFinAgent", 
               "w/o Evo", "w/o Mem", "w/o Orch"]
    hard   = [10.5, 76.2, 71.3, 74.4, 72.1, 73.5, 68.4]
    score  = [ 4.1, 24.2, 28.4, 39.5, 36.5, 34.9, 27.3]
    hard_e = [ 2.5,  2.1,  2.8,  2.6,  3.3,  3.2,  4.8]
    score_e= [ 0.8,  2.4,  2.8,  2.6,  2.7,  2.9,  3.1]

    x = np.arange(len(methods)); w = 0.35
    fig, ax = plt.subplots(figsize=(7.5, 3.4))

    BLUE = "#4472C4"; ORANGE = "#ED7D31"
    b1 = ax.bar(x - w/2, hard,  w, yerr=hard_e,  label="Hard-Success (%)",
                color=BLUE,   alpha=0.85, capsize=3, error_kw=dict(lw=1))
    b2 = ax.bar(x + w/2, score, w, yerr=score_e, label="Judge Score (0-100)",
                color=ORANGE, alpha=0.85, capsize=3, error_kw=dict(lw=1))

    # highlight Full (Best)
    for bar in [b1[3], b2[3]]:
        bar.set_edgecolor("#1a1a1a"); bar.set_linewidth(1.4)

    ax.set_xticks(x); ax.set_xticklabels(methods, rotation=25, ha="right", fontsize=8.5)
    ax.set_ylabel("Success Rate (%) / Score", fontsize=9)
    ax.set_ylim(0, 115)
    ax.yaxis.set_tick_params(labelsize=8)
    ax.axvline(3.5, color="gray", lw=0.8, ls="--", alpha=0.6)
    ax.text(3.6, 108, "ablations →", fontsize=7.5, color="gray")
    ax.legend(fontsize=8.5, framealpha=0.9, loc="upper left")
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(axis="y", lw=0.5, alpha=0.4)

    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "fig_results.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_results.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig_results done")


# ── Figure 3: Sensitivity Line Chart ───────────────────────────────────────
def fig_sensitivity():
    limits = [10, 15, 25, 50]
    hard   = [10.0, 18.2, 25.0, 32.5]
    judge  = [ 8.5, 14.1, 18.2, 22.1]
    hard_e = [ 2.1,  3.5,  4.5,  5.2]
    judge_e= [ 1.2,  2.8,  3.8,  4.1]

    fig, ax = plt.subplots(figsize=(4.5, 3.0))
    BLUE = "#4472C4"; ORANGE = "#ED7D31"; GREEN = "#70AD47"

    ax.errorbar(limits, hard,  yerr=hard_e,  fmt="-o", color=BLUE,
                capsize=4, lw=1.6, ms=5, label="ReAct Hard-Success")
    ax.errorbar(limits, judge, yerr=judge_e, fmt="-s", color=ORANGE,
                capsize=4, lw=1.6, ms=5, label="ReAct Judge-Success")
    ax.axhline(100.0, color=GREEN, lw=1.5, ls="--",
               label=r"\textsc{EvoFinAgent} (100\%)")

    ax.set_xlabel("Recursion Limit", fontsize=9)
    ax.set_ylabel("Rate (%)", fontsize=9)
    ax.set_xticks(limits)
    ax.set_ylim(0, 105)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7.8, framealpha=0.9)
    ax.spines[["top","right"]].set_visible(False)
    ax.grid(lw=0.5, alpha=0.4)

    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "fig_sensitivity.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_sensitivity.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig_sensitivity done")


# ── Figure 4: DAG Comparison ───────────────────────────────────────────────
def fig_dag_comparison():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.8, 3.8))
    
    BLUE = "#4472C4"; ORANGE = "#ED7D31"; GREEN = "#70AD47"; RED = "#C00000"; GRAY = "#8496A9"
    BKG_GRAY = "#F2F2F2"

    for ax in [ax1, ax2]:
        ax.set_xlim(0, 10); ax.set_ylim(0, 5); ax.axis("off")

    def node(ax, x, y, label, color, w=1.9, h=0.7, fontsize=8, is_fail=False):
        # Shadow effect
        shadow = mpatches.FancyBboxPatch((x-w/2+0.05, y-h/2-0.05), w, h,
            boxstyle="round,pad=0.05", linewidth=0, facecolor="black", alpha=0.1)
        ax.add_patch(shadow)
        
        ec = color if not is_fail else RED
        fc = color+"22" if not is_fail else RED+"11"
        r = mpatches.FancyBboxPatch((x-w/2, y-h/2), w, h,
            boxstyle="round,pad=0.05", linewidth=1.2,
            edgecolor=ec, facecolor=fc)
        ax.add_patch(r)
        
        # Text with path effect for better readability
        txt = ax.text(x, y, label, ha="center", va="center", 
                fontsize=fontsize, color="#222", fontweight="bold" if not is_fail else "normal")
        if is_fail:
            txt.set_color(RED)

    def arrow(ax, x0, y0, x1, y1, color="#666", lw=1.2, dashed=False):
        ls = (0,(3,2)) if dashed else "solid"
        ax.annotate("", xy=(x1,y1), xytext=(x0,y0),
            arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, 
                            linestyle=ls, shrinkA=3, shrinkB=3,
                            connectionstyle="arc3,rad=0.1" if dashed else "arc3,rad=0.0"))

    # Background containers
    ax1.add_patch(mpatches.Rectangle((0.2, 0.2), 9.6, 4.6, color=BKG_GRAY, alpha=0.3, zorder=-1))
    ax2.add_patch(mpatches.Rectangle((0.2, 0.2), 9.6, 4.6, color=BKG_GRAY, alpha=0.3, zorder=-1))

    # --- Left: ReAct (Logical Entropy) ---
    ax1.text(5, 4.7, "Baseline: ReAct Style", ha="center", fontsize=10, fontweight="bold", color="#444")
    ax1.text(5, 0.4, "High Logical Entropy", ha="center", fontsize=9, color=RED, fontweight="bold")
    
    node(ax1, 2, 4, "Fetch Data", GRAY)
    node(ax1, 2, 2.5, "Check Unit", RED, is_fail=True)
    node(ax1, 5, 2.5, "Check Unit\n(Retry)", RED, is_fail=True)
    node(ax1, 8, 2.5, "Search News\n(Loop)", RED, is_fail=True)
    node(ax1, 5, 0.9, "Recursion Limit Exceeded!", RED, w=4.5, h=0.5, fontsize=9)
    
    arrow(ax1, 2, 3.6, 2, 2.9)
    arrow(ax1, 3.0, 2.5, 3.9, 2.5, color=RED)
    arrow(ax1, 6.0, 2.5, 6.9, 2.5, color=RED)
    arrow(ax1, 8, 2.1, 5, 1.2, color=RED, dashed=True)
    
    # Chaos indicator
    for _ in range(3):
        x, y = np.random.uniform(3, 7), np.random.uniform(3, 4)
        ax1.text(x, y, "?", fontsize=12, color=RED, alpha=0.3, rotation=np.random.randint(0, 360))

    # --- Right: EvoFinAgent (Plan Rigor) ---
    ax2.text(5, 4.7, r"\textsc{EvoFinAgent}: DAG Orchestrator", ha="center", fontsize=10, fontweight="bold", color="#444")
    ax2.text(5, 0.4, "Low Entropy / High Plan Rigor", ha="center", fontsize=9, color=GREEN, fontweight="bold")

    node(ax2, 2, 4.2, "get_financials", BLUE)
    node(ax2, 2, 3.0, "get_fx_rate", BLUE)
    node(ax2, 2, 1.8, "get_quote", BLUE)
    node(ax2, 5.5, 3.6, "python_interpreter\n(Verified Calc)", GREEN, w=2.8)
    node(ax2, 8.5, 3.0, "synthesis\n(Final Decision)", ORANGE, w=2.4)

    arrow(ax2, 3.0, 4.2, 4.2, 3.8, color=BLUE)
    arrow(ax2, 3.0, 3.0, 4.2, 3.4, color=BLUE)
    arrow(ax2, 7.0, 3.6, 7.4, 3.2, color=GREEN)
    arrow(ax2, 3.0, 1.8, 7.4, 2.8, color=BLUE, dashed=True) # Data dependency
    
    ax2.text(3.5, 4.3, "Dependency\nFlow", fontsize=7.5, color=BLUE, ha="center", style="italic")
    ax2.text(6.8, 4.2, "Numeric\nGrounding", fontsize=7.5, color=GREEN, ha="center", style="italic")

    fig.tight_layout(pad=1.2)
    fig.savefig(OUT / "fig_dag_comparison.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_dag_comparison.png", dpi=250, bbox_inches="tight")
    plt.close(fig)
    print("fig_dag_comparison (improved) done")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_architecture()
    fig_results()
    fig_sensitivity()
    fig_dag_comparison()
