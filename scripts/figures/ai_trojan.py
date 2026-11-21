"""Figures for src/data/blog/ai-trojan.md.

Run from the repo root:
    scripts/figures/.venv/bin/python scripts/figures/ai_trojan.py

SEVEN is the first image of the MNIST test set (a 7), one hex string per
row, 28 rows of 28 grayscale values from 00 (black) to ff (white).
"""

from pathlib import Path

from style import INK, ORANGE, plt, save

OUT = Path("public/images/ai-trojan")
OUT.mkdir(parents=True, exist_ok=True)

SEVEN = [
    "00000000000000000000000000000000000000000000000000000000",
    "00000000000000000000000000000000000000000000000000000000",
    "00000000000000000000000000000000000000000000000000000000",
    "00000000000000000000000000000000000000000000000000000000",
    "00000000000000000000000000000000000000000000000000000000",
    "00000000000000000000000000000000000000000000000000000000",
    "00000000000000000000000000000000000000000000000000000000",
    "00000000000054b99f973c2400000000000000000000000000000000",
    "000000000000defefefefef1c6c6c6c6c6c6c6c6aa34000000000000",
    "00000000000043724872a3e3fee1fefefefae5fefe8c000000000000",
    "000000000000000000000011420e4343433b15ecfe6a000000000000",
    "00000000000000000000000000000000000053fdd112000000000000",
    "000000000000000000000000000000000016e9ff5300000000000000",
    "000000000000000000000000000000000081feee2c00000000000000",
    "000000000000000000000000000000003bf9fe3e0000000000000000",
    "0000000000000000000000000000000085febb050000000000000000",
    "00000000000000000000000000000009cdf83a000000000000000000",
    "0000000000000000000000000000007efeb600000000000000000000",
    "00000000000000000000000000004bfbf03900000000000000000000",
    "0000000000000000000000000013ddfea60000000000000000000000",
    "00000000000000000000000003cbfedb230000000000000000000000",
    "00000000000000000000000026fefe4d000000000000000000000000",
    "00000000000000000000001fe0fe7301000000000000000000000000",
    "000000000000000000000085fefe3400000000000000000000000000",
    "000000000000000000003df2fefe3400000000000000000000000000",
    "0000000000000000000079fefedb2800000000000000000000000000",
    "0000000000000000000079fecf120000000000000000000000000000",
    "00000000000000000000000000000000000000000000000000000000",
]

PATTERN = [[1.0, 0.0, 1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 1.0]]


def image():
    return [[int(row[i : i + 2], 16) / 255 for i in range(0, 56, 2)] for row in SEVEN]


def with_pixel():
    img = image()
    img[26][26] = 1.0
    return img


def with_pattern():
    img = image()
    for r in range(3):
        for c in range(3):
            img[24 + r][24 + c] = PATTERN[r][c]
    return img


def mnist_triggers():
    panels = [
        ("Clean", image(), None),
        ("Single pixel", with_pixel(), (26, 26, 1)),
        ("Pattern", with_pattern(), (24, 24, 3)),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(8.4, 3.2))
    for ax, (title, img, box) in zip(axes, panels):
        ax.imshow(img, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
        ax.set_title(title, color=INK)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        for side in ax.spines.values():
            side.set_visible(False)
        if box:
            row, col, size = box
            ax.add_patch(
                plt.Rectangle(
                    (col - 0.5 - 0.6, row - 0.5 - 0.6),
                    size + 1.2,
                    size + 1.2,
                    fill=False,
                    edgecolor=ORANGE,
                    linewidth=2,
                )
            )
    save(fig, OUT / "mnist-triggers.svg")


if __name__ == "__main__":
    mnist_triggers()
