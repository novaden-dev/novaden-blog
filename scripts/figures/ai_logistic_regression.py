"""Figures for src/data/blog/ai-logistic-regression.md.

Run from the repo root:
    scripts/figures/.venv/bin/python scripts/figures/ai_logistic_regression.py
"""

from pathlib import Path

import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from style import BLUE, INK, MUTED, ORANGE, plt, save

OUT = Path("public/images/ai-logistic-regression")
OUT.mkdir(parents=True, exist_ok=True)

# The model in the post: z = 0.3 * failed + 0.8 * usernames - 6
W1, W2, B = 0.3, 0.8, -6.0


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def boundary():
    rng = np.random.default_rng(11)
    # Most sources fail a login or two with one username; a few hammer it.
    failed = np.clip(rng.gamma(1.6, 4.5, 160), 0, 24.5)
    users = np.clip(rng.gamma(1.3, 1.9, 160), 0, 9.8)
    attack = rng.uniform(0, 1, 160) < sigmoid(W1 * failed + W2 * users + B)

    gx, gy = np.meshgrid(np.linspace(0, 25, 300), np.linspace(0, 10, 300))
    prob = sigmoid(W1 * gx + W2 * gy + B)
    cmap = LinearSegmentedColormap.from_list("risk", ["#dbeafe", "#f8fafc", "#fed7aa"])

    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    ax.grid(False)
    ax.contourf(gx, gy, prob, levels=20, cmap=cmap)
    lines = ax.contour(gx, gy, prob, levels=[0.2, 0.5, 0.9], colors=[MUTED, INK, MUTED],
                       linestyles=["--", "-", "--"], linewidths=[1.2, 2.5, 1.2])
    ax.clabel(lines, fmt={0.2: "p = 0.2", 0.5: "p = 0.5", 0.9: "p = 0.9"}, fontsize=10)
    ax.scatter(failed[~attack], users[~attack], color=BLUE, s=24, label="benign source", zorder=3)
    ax.scatter(failed[attack], users[attack], color=ORANGE, marker="^", s=34, label="attack source", zorder=3)
    ax.set_xlabel("failed logins in the last 10 minutes")
    ax.set_ylabel("distinct usernames tried")
    ax.set_title("Decision boundary and probability bands")
    ax.legend(loc="upper right", frameon=True, facecolor="white", fontsize=9)
    save(fig, OUT / "boundary.svg")


if __name__ == "__main__":
    boundary()
    for f, u in [(5, 1), (12, 6), (20, 1), (2, 7)]:
        z = W1 * f + W2 * u + B
        print(f"failed={f} users={u} z={z:.2f} p={sigmoid(z):.3f}")
    print("odds x per failed", np.exp(W1), "per username", np.exp(W2))
    print("wrote", sorted(p.name for p in OUT.iterdir()))
