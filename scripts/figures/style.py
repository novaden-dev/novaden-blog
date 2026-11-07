"""Shared look for post figures: a light card that reads on both site themes."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BG = "#f8fafc"
INK = "#0f172a"
MUTED = "#475569"
GRID = "#e2e8f0"
BLUE = "#2563eb"
ORANGE = "#ea580c"

plt.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": BG,
        "savefig.facecolor": BG,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "axes.titleweight": "bold",
        "axes.grid": True,
        "grid.color": GRID,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 11,
        "svg.fonttype": "path",
        "svg.hashsalt": "novaden",
    }
)


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)
