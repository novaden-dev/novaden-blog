"""Figures for src/data/blog/ai-decision-trees.md.

Run from the repo root:
    scripts/figures/.venv/bin/python scripts/figures/ai_decision_trees.py
"""

from pathlib import Path

import numpy as np
from matplotlib import font_manager

from style import plt, save

OUT = Path("public/images/ai-decision-trees")
OUT.mkdir(parents=True, exist_ok=True)

# This note also has hand-drawn Excalidraw diagrams (runs, feature-splits,
# decision-tree), so these plots use the same palette and Nunito,
# Excalidraw's text font, on a white card. Red/green mean malicious/benign.
FONTS = Path(__file__).parent / "fonts"
for f in FONTS.glob("nunito-*.ttf"):
    font_manager.fontManager.addfont(str(f))
INK = "#1e1e1e"
MUTED = "#495057"
BLUE = "#1971c2"
ORANGE = "#e8590c"
WHITE = "#ffffff"
plt.rcParams.update({
    # The fontsource files carry the family name "Nunito ExtraLight", left over
    # from the variable font they were cut from; their weights are 400 and 700.
    "font.family": "Nunito ExtraLight",
    "figure.facecolor": WHITE,
    "axes.facecolor": WHITE,
    "savefig.facecolor": WHITE,
    "text.color": INK,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "axes.edgecolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "grid.color": "#e9ecef",
})


def impurity():
    p = np.linspace(0.0001, 0.9999, 400)
    gini = 1 - p**2 - (1 - p) ** 2
    ent = -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.plot(p, ent, color=ORANGE, linewidth=3, label="entropy (max 1.0)")
    ax.plot(p, gini, color=BLUE, linewidth=3, label="Gini impurity (max 0.5)")
    ax.plot([0.4, 0.4], [0, 0.971], color=MUTED, linestyle="--", linewidth=1)
    ax.annotate("root node: 4 of 10 malicious\nGini 0.48, entropy 0.97", (0.4, 0.62),
                xytext=(0.47, 0.25), color=INK, fontsize=10,
                arrowprops=dict(arrowstyle="->", color=MUTED))
    ax.set_xlabel("share of the node that is malicious")
    ax.set_ylabel("impurity")
    ax.set_ylim(0, 1.08)
    ax.set_title("Pure nodes score 0, a 50/50 mix scores highest")
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    save(fig, OUT / "impurity.svg")


if __name__ == "__main__":
    impurity()
    print("wrote", sorted(p.name for p in OUT.iterdir()))
