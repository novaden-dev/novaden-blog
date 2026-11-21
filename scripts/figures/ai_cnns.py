"""Figures for src/data/blog/ai-cnns.md.

Run from the repo root, with the path to the extracted Malimg dataset
(one folder per family):
    scripts/figures/.venv/bin/python scripts/figures/ai_cnns.py /path/to/malimg_paper_dataset_imgs
"""

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from style import MUTED, plt

OUT = Path("public/images/ai-cnns")
OUT.mkdir(parents=True, exist_ok=True)

MALIMG = Path(sys.argv[1])
FAMILIES = ["Dialplatform.B", "Allaple.A", "Yuner.A"]
PER_FAMILY = 3


def malimg_samples():
    fig, axes = plt.subplots(len(FAMILIES), PER_FAMILY, figsize=(9, 9.5))
    for row, family in zip(axes, FAMILIES):
        paths = sorted((MALIMG / family).glob("*.png"))[:PER_FAMILY]
        for ax, path in zip(row, paths):
            pixels = np.asarray(Image.open(path).convert("L"))
            height, width = pixels.shape
            ax.imshow(pixels, cmap="gray", vmin=0, vmax=255, interpolation="antialiased")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_color(MUTED)
            ax.set_xlabel(f"{width} × {height} px", color=MUTED, fontsize=10)
        row[0].set_ylabel(family, fontsize=12, fontweight="bold", labelpad=10)
    # The samples are bitmaps, so PNG: an SVG would embed them and weigh over 1 MB.
    # Reducing to 32 colors keeps the textures and cuts the file size.
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110)
    plt.close(fig)
    image = Image.open(buffer).convert("RGB").quantize(colors=32, dither=Image.Dither.NONE)
    image.save(OUT / "malimg-samples.png", optimize=True)


malimg_samples()
