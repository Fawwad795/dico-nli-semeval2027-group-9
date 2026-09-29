"""dico_nli.plotting: one paper-ready style for every figure, vector PDF out."""

import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dico_nli.data import LABELS
from dico_nli.plotting import DOUBLE_COLUMN_IN, LABEL_COLORS, LABEL_NAMES, SINGLE_COLUMN_IN, figure, paper_theme, save_figure


def test_label_colours_cover_every_label_with_a_hex_value():
    assert tuple(LABEL_COLORS) == LABELS
    assert all(re.fullmatch(r"#[0-9a-f]{6}", value) for value in LABEL_COLORS.values())
    assert len(set(LABEL_COLORS.values())) == 4
    assert tuple(LABEL_NAMES) == LABELS


def test_paper_theme_embeds_fonts_and_uses_hairline_grid():
    paper_theme()

    assert plt.rcParams["pdf.fonttype"] == 42
    assert plt.rcParams["axes.spines.top"] is False
    assert plt.rcParams["axes.spines.right"] is False
    assert plt.rcParams["grid.linewidth"] <= 0.6
    assert plt.rcParams["font.size"] <= 9


def test_figure_sizes_match_paper_column_widths():
    fig, ax = figure(columns=1)
    assert fig.get_figwidth() == SINGLE_COLUMN_IN
    plt.close(fig)

    fig, axes = figure(columns=2, ncols=2)
    assert fig.get_figwidth() == DOUBLE_COLUMN_IN
    assert len(axes) == 2
    plt.close(fig)


def test_save_figure_writes_a_vector_pdf_and_a_png_preview(tmp_path):
    fig, ax = figure(columns=1)
    ax.bar([0, 1], [1, 2], color=[LABEL_COLORS["EQUIVALENCE"], LABEL_COLORS["NEGATIVE_OTHER"]])

    pdf_path, png_path = save_figure(fig, tmp_path / "figures" / "demo")

    assert pdf_path == tmp_path / "figures" / "demo.pdf"
    assert png_path == tmp_path / "figures" / "demo.png"
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert png_path.read_bytes().startswith(b"\x89PNG")
