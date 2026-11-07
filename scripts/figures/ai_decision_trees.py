"""Figures for src/data/blog/ai-decision-trees.md.

Run from the repo root:
    scripts/figures/.venv/bin/python scripts/figures/ai_decision_trees.py
"""

from pathlib import Path

import numpy as np
from matplotlib.patches import FancyBboxPatch

from style import BLUE, INK, MUTED, ORANGE, plt, save

OUT = Path("public/images/ai-decision-trees")
OUT.mkdir(parents=True, exist_ok=True)


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


def box(ax, x, y, text, kind):
    colors = {
        "split": ("#e2e8f0", MUTED),
        "mal": ("#fed7aa", ORANGE),
        "ben": ("#dbeafe", BLUE),
    }[kind]
    w, h = 2.7, 0.95
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                facecolor=colors[0], edgecolor=colors[1], linewidth=1.8))
    ax.text(x, y, text, ha="center", va="center", fontsize=10, color=INK)


def edge(ax, x1, y1, x2, y2, label):
    ax.annotate("", xy=(x2, y2 + 0.5), xytext=(x1, y1 - 0.5),
                arrowprops=dict(arrowstyle="->", color=MUTED, linewidth=1.5))
    ax.text((x1 + x2) / 2 + (0.15 if x2 > x1 else -0.15), (y1 + y2) / 2, label,
            ha="left" if x2 > x1 else "right", va="center", fontsize=10, color=MUTED, fontweight="bold")


def tree():
    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.grid(False)
    ax.axis("off")
    nodes = {
        "root": (4.5, 6, "Launched by Office?\n10 runs, 4 malicious", "split"),
        "off": (1.6, 4.2, "Malicious\n2 of 2", "mal"),
        "dl": (7.0, 4.2, "Downloads from internet?\n8 runs, 2 malicious", "split"),
        "dl_no": (9.3, 2.4, "Benign\n4 of 4", "ben"),
        "enc": (4.7, 2.4, "Encoded command?\n4 runs, 2 malicious", "split"),
        "enc_yes": (2.6, 0.6, "Malicious\n1 of 1", "mal"),
        "enc_no": (6.8, 0.6, "Benign\n2 of 3 (impure)", "ben"),
    }
    for a, b, label in [("root", "off", "yes"), ("root", "dl", "no"), ("dl", "enc", "yes"),
                        ("dl", "dl_no", "no"), ("enc", "enc_yes", "yes"), ("enc", "enc_no", "no")]:
        edge(ax, nodes[a][0], nodes[a][1], nodes[b][0], nodes[b][1], label)
    for x, y, text, kind in nodes.values():
        box(ax, x, y, text, kind)
    ax.set_xlim(-0.2, 10.9)
    ax.set_ylim(-0.1, 6.7)
    save(fig, OUT / "tree.svg")


if __name__ == "__main__":
    impurity()
    tree()
    print("wrote", sorted(p.name for p in OUT.iterdir()))
