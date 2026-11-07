"""Figures for src/data/blog/ai-supervised-learning.md.

Run from the repo root:
    scripts/figures/.venv/bin/python scripts/figures/ai_supervised_learning.py
"""

from pathlib import Path

import numpy as np
from matplotlib.patches import Rectangle

from style import BLUE, INK, MUTED, ORANGE, plt, save

OUT = Path("public/images/ai-supervised-learning")
OUT.mkdir(parents=True, exist_ok=True)


def fitting():
    rng = np.random.default_rng(285)
    truth = lambda x: np.sin(2 * np.pi * x)  # noqa: E731
    x_train = np.sort(rng.uniform(0, 1, 10))
    y_train = truth(x_train) + rng.normal(0, 0.25, x_train.size)
    x_test = np.sort(rng.uniform(0.03, 0.97, 10))
    y_test = truth(x_test) + rng.normal(0, 0.25, x_test.size)
    grid = np.linspace(0, 1, 400)

    panels = [(1, "Underfit"), (3, "Good fit"), (9, "Overfit")]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.6), sharey=True)
    for ax, (degree, title) in zip(axes, panels):
        coeffs = np.polyfit(x_train, y_train, degree)
        mse = lambda x, y: float(np.mean((np.polyval(coeffs, x) - y) ** 2))  # noqa: E731
        ax.plot(grid, np.polyval(coeffs, grid), color=BLUE, linewidth=2.5)
        ax.scatter(x_train, y_train, color=INK, s=28, zorder=3, label="training data")
        ax.scatter(x_test, y_test, facecolors="none", edgecolors=ORANGE, linewidths=2, s=40, zorder=3, label="new data")
        ax.set_ylim(-2, 2)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(title)
        ax.text(
            0.5, -0.12,
            f"training error {mse(x_train, y_train):.2f}\nerror on new data {mse(x_test, y_test):.2f}",
            transform=ax.transAxes, ha="center", va="top", color=MUTED, fontsize=10,
        )
    axes[0].legend(loc="lower left", fontsize=9, frameon=False)
    save(fig, OUT / "fitting.svg")


def cross_validation(k=5):
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.grid(False)
    for round_ in range(k):
        y = k - 1 - round_
        for fold in range(k):
            test = fold == round_
            ax.add_patch(
                Rectangle(
                    (fold + 0.05, y + 0.12), 0.9, 0.76,
                    facecolor=ORANGE if test else "#bfdbfe",
                    edgecolor=ORANGE if test else BLUE,
                )
            )
            ax.text(fold + 0.5, y + 0.5, "test" if test else "train", ha="center", va="center",
                    color="white" if test else INK, fontsize=10, fontweight="bold" if test else "normal")
        ax.text(-0.15, y + 0.5, f"Round {round_ + 1}", ha="right", va="center", color=INK, fontsize=10)
        ax.text(k + 0.15, y + 0.5, f"score {[0.91, 0.88, 0.93, 0.90, 0.89][round_]:.2f}", ha="left", va="center", color=MUTED, fontsize=10)
    ax.text(k + 0.15, -0.45, "average 0.90", ha="left", va="center", color=INK, fontsize=10, fontweight="bold")
    ax.set_xlim(-1.3, k + 1.4)
    ax.set_ylim(-0.8, k)
    ax.axis("off")
    save(fig, OUT / "cross-validation.svg")


if __name__ == "__main__":
    fitting()
    cross_validation()
    print("wrote", sorted(p.name for p in OUT.iterdir()))
