"""Figures for src/data/blog/ai-math.md.

Run from the repo root:
    scripts/figures/.venv/bin/python scripts/figures/ai_math.py
"""

import math
from pathlib import Path

from style import BLUE, INK, MUTED, ORANGE, plt, save

OUT = Path("public/images/ai-math")
OUT.mkdir(parents=True, exist_ok=True)


def frange(a, b, n=400):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def sigmoid():
    xs = frange(-8, 8)
    ys = [1 / (1 + math.exp(-x)) for x in xs]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(xs, ys, color=BLUE, linewidth=3)
    for x, label, dx in [(0, "sigmoid(0) = 0.5", 0.4), (4, "sigmoid(4) ≈ 0.98", -3.6)]:
        y = 1 / (1 + math.exp(-x))
        ax.plot([x], [y], "o", color=INK, markersize=7)
        ax.annotate(label, (x, y), xytext=(x + dx, y - 0.16), color=INK, fontsize=11)
    ax.axhline(0, color=MUTED, linewidth=1, linestyle="--")
    ax.axhline(1, color=MUTED, linewidth=1, linestyle="--")
    ax.set_ylim(-0.08, 1.08)
    ax.set_xlabel("input (any number)")
    ax.set_ylabel("output (0 to 1)")
    ax.set_title("Sigmoid: any number in, a probability out")
    save(fig, OUT / "sigmoid.svg")


def log_loss():
    ps = frange(0.02, 1, 300)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(ps, [-math.log(p) for p in ps], color=ORANGE, linewidth=3)
    for p, label, dx, dy in [
        (0.9, "p = 0.9, loss 0.11", -0.32, 0.6),
        (0.1, "p = 0.1, loss 2.30", 0.05, 0.4),
    ]:
        ax.plot([p], [-math.log(p)], "o", color=INK, markersize=7)
        ax.annotate(label, (p, -math.log(p)), xytext=(p + dx, -math.log(p) + dy), color=INK, fontsize=11)
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 4)
    ax.set_xlabel("probability the model gave the correct label (p)")
    ax.set_ylabel("loss = -ln(p)")
    ax.set_title("Log loss: confident wrong answers cost the most")
    save(fig, OUT / "log-loss.svg")


def correlation():
    import random

    rng = random.Random(16)
    xs = [rng.uniform(0, 10) for _ in range(40)]
    panels = [
        ("positive", [x + rng.gauss(0, 1) for x in xs]),
        ("none", [rng.uniform(0, 10) for _ in xs]),
        ("negative", [10 - x + rng.gauss(0, 1) for x in xs]),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.2), sharey=True)
    for ax, (title, ys) in zip(axes, panels):
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / len(xs)
        sx = math.sqrt(sum((x - mx) ** 2 for x in xs) / len(xs))
        sy = math.sqrt(sum((y - my) ** 2 for y in ys) / len(ys))
        ax.scatter(xs, ys, color=BLUE, s=22)
        ax.set_title(f"ρ = {cov / (sx * sy):.2f}", fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])
    axes[1].set_xlabel("X")
    axes[0].set_ylabel("Y")
    save(fig, OUT / "correlation.svg")


if __name__ == "__main__":
    sigmoid()
    log_loss()
    correlation()
    print("wrote", sorted(p.name for p in OUT.iterdir()))
