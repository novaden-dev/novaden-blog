"""Figures for src/data/blog/ai-linear-regression.md.

Run from the repo root:
    scripts/figures/.venv/bin/python scripts/figures/ai_linear_regression.py
"""

from pathlib import Path

import numpy as np

from style import BLUE, INK, MUTED, ORANGE, plt, save

OUT = Path("public/images/ai-linear-regression")
OUT.mkdir(parents=True, exist_ok=True)

# The worked example in the post: concurrent users -> response time (ms).
USERS = np.array([10, 20, 30, 40, 50])
MS = np.array([120, 150, 210, 230, 290])


def fit_line():
    w, b = np.polyfit(USERS, MS, 1)
    fig, ax = plt.subplots(figsize=(7, 4))
    grid = np.linspace(5, 55, 100)
    ax.plot(grid, w * grid + b, color=BLUE, linewidth=2.5, label=f"ŷ = {w:.1f}x + {b:.0f}")
    for x, y in zip(USERS, MS):
        pred = w * x + b
        ax.plot([x, x], [pred, y], color=ORANGE, linewidth=2)
        ax.annotate(f"{y - pred:+.0f}", (x, (y + pred) / 2), xytext=(6, 0),
                    textcoords="offset points", color=ORANGE, fontsize=10, va="center")
    ax.scatter(USERS, MS, color=INK, s=40, zorder=3, label="measured")
    ax.plot([], [], color=ORANGE, linewidth=2, label="residual")
    ax.set_xlim(5, 55)
    ax.set_ylim(100, 305)
    ax.set_xlabel("concurrent users")
    ax.set_ylabel("response time (ms)")
    ax.set_title("The fitted line and its residuals")
    ax.legend(loc="upper left", frameon=False)
    save(fig, OUT / "fit.svg")
    return w, b


def residual_patterns():
    rng = np.random.default_rng(3)
    pred = np.linspace(100, 400, 60)
    panels = [
        ("Fine: random band", rng.normal(0, 12, pred.size)),
        ("Curve: not linear", 0.0035 * (pred - 250) ** 2 - 25 + rng.normal(0, 8, pred.size)),
        ("Fan: spread grows", rng.normal(0, 1, pred.size) * (pred - 80) * 0.12),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.3), sharey=True)
    for ax, (title, resid) in zip(axes, panels):
        ax.axhline(0, color=MUTED, linewidth=1, linestyle="--")
        ax.scatter(pred, resid, color=BLUE, s=16)
        ax.set_title(title, fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])
    axes[1].set_xlabel("predicted value")
    axes[0].set_ylabel("residual")
    save(fig, OUT / "residual-patterns.svg")


if __name__ == "__main__":
    w, b = fit_line()
    residual_patterns()
    pred = w * USERS + b
    sse = float(((MS - pred) ** 2).sum())
    sst = float(((MS - MS.mean()) ** 2).sum())
    print(f"w={w:.4f} b={b:.4f} resid={MS - pred} sse={sse:.1f} rmse={np.sqrt(sse / 5):.2f} r2={1 - sse / sst:.4f}")
    print("wrote", sorted(p.name for p in OUT.iterdir()))
