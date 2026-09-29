"""One paper-ready style for every figure: seaborn theme, fixed label palette, vector PDF out.

Light surface only, because the report is a PDF. The label palette uses the dataviz reference
categorical slots and was chosen with the palette validator on 2026-09-29, in canonical label
order (EQUIVALENCE, FORWARD, BACKWARD, NEGATIVE_OTHER): all-pairs on the light surface passes
with worst colour-vision-deficiency distance 9.2 and worst normal-vision distance 16.3. The
aqua slot sits at 2.74:1 contrast, so every figure carries direct labels or ships with its
table under ``experiments/``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns

from .data import LABELS

LABEL_COLORS: dict[str, str] = {
    "EQUIVALENCE": "#1baf7a",
    "FORWARD_ENTAILMENT": "#2a78d6",
    "BACKWARD_ENTAILMENT": "#eb6834",
    "NEGATIVE_OTHER": "#4a3aa7",
}
LABEL_NAMES: dict[str, str] = {
    "EQUIVALENCE": "Equivalence",
    "FORWARD_ENTAILMENT": "Forward entailment",
    "BACKWARD_ENTAILMENT": "Backward entailment",
    "NEGATIVE_OTHER": "Negative / other",
}
assert tuple(LABEL_COLORS) == LABELS and tuple(LABEL_NAMES) == LABELS

INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
DE_EMPHASIS = "#c3c2b7"
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# ACL two-column layout: 3.05 in per column, 6.3 in text width.
SINGLE_COLUMN_IN = 3.05
DOUBLE_COLUMN_IN = 6.3


def paper_theme() -> None:
    """Apply the project theme to matplotlib: small sans type, hairline grid, embedded fonts."""
    sns.set_theme(
        style="ticks",
        context="paper",
        rc={
            "font.family": "sans-serif",
            "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
            "font.size": 8,
            "axes.titlesize": 8,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "legend.title_fontsize": 7,
            "legend.frameon": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": BASELINE,
            "axes.linewidth": 0.6,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": GRID,
            "grid.linewidth": 0.5,
            "grid.linestyle": "-",
            "axes.axisbelow": True,
            "xtick.color": BASELINE,
            "ytick.color": BASELINE,
            "xtick.labelcolor": INK_SECONDARY,
            "ytick.labelcolor": INK_SECONDARY,
            "xtick.major.size": 2.5,
            "ytick.major.size": 0,
            "xtick.major.width": 0.6,
            "text.color": INK,
            "axes.labelcolor": INK_SECONDARY,
            "lines.linewidth": 1.2,
            "patch.linewidth": 0,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.02,
        },
    )


def figure(columns: int = 1, nrows: int = 1, ncols: int = 1, height: float | None = None, **kwargs):
    """A figure sized for one or two paper columns; returns ``(fig, ax)`` or ``(fig, axes)``."""
    width = SINGLE_COLUMN_IN if columns == 1 else DOUBLE_COLUMN_IN
    height = height or (width / ncols) * 0.72 * nrows
    return plt.subplots(nrows, ncols, figsize=(width, height), constrained_layout=True, **kwargs)


def label_palette(labels=LABELS) -> list[str]:
    return [LABEL_COLORS[label] for label in labels]


def bar_labels(ax, container, fmt: str = "{:.0f}", **kwargs) -> None:
    """Direct labels at bar tips in secondary ink; text never wears the series colour."""
    ax.bar_label(container, fmt=fmt, padding=2, fontsize=7, color=INK_SECONDARY, **kwargs)


def save_figure(fig, stem: Path | str) -> tuple[Path, Path]:
    """Write ``<stem>.pdf`` (vector, fonts embedded) and ``<stem>.png`` (review preview)."""
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    pdf_path, png_path = stem.with_suffix(".pdf"), stem.with_suffix(".png")
    fig.savefig(pdf_path, format="pdf")
    fig.savefig(png_path, format="png", dpi=200)
    plt.close(fig)
    return pdf_path, png_path
