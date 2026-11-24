"""Luminance, contrast, CSS colour parsing, background estimation and image comparison."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from pcv.checks_image import background_of, contrast, luminance, parse_color
from pcv.checks_output import compare_images


def test_luminance_extremes_and_known_value():
    assert luminance((255, 255, 255)) == pytest.approx(1.0)
    assert luminance((0, 0, 0)) == pytest.approx(0.0)
    # WCAG relative luminance of #777777
    assert luminance((119, 119, 119)) == pytest.approx(0.1845, abs=1e-4)


def test_contrast_known_ratios_and_symmetry():
    assert contrast((255, 255, 255), (0, 0, 0)) == pytest.approx(21.0)
    assert contrast((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0)
    assert contrast((10, 20, 30), (10, 20, 30)) == pytest.approx(1.0)
    # #777 on white is the classic just-below-AA pair: 4.48:1
    assert contrast((119, 119, 119), (255, 255, 255)) == pytest.approx(4.48, abs=0.01)
    assert contrast((118, 118, 118), (255, 255, 255)) >= 4.5


@pytest.mark.parametrize("css, want", [
    ("rgb(10, 20, 30)", ((10.0, 20.0, 30.0), 1.0)),
    ("rgba(0, 0, 0, 0.5)", ((0.0, 0.0, 0.0), 0.5)),
    ("rgb(0 0 0 / 50%)", ((0.0, 0.0, 0.0), 0.5)),
    ("rgba(255, 255, 255, 0)", ((255.0, 255.0, 255.0), 0.0)),
])
def test_parse_color_computed_style_forms(css, want):
    assert parse_color(css) == want


@pytest.mark.parametrize("css", ["#ffffff", "transparent", "", None, "url(#grad)", "currentcolor"])
def test_parse_color_rejects_non_rgb(css):
    assert parse_color(css) is None


def test_background_is_dominant_colour_not_glyph_ink():
    patch = np.full((40, 200, 3), 250, dtype=np.uint8)
    patch[15:25, 10:190] = (20, 20, 20)  # 25 % of the patch is "text"
    assert background_of(patch).round().tolist() == [250.0, 250.0, 250.0]


def test_compare_images_identical_and_changed():
    a = Image.new("RGB", (1920, 1080), (255, 255, 255))
    assert compare_images(a, a.copy())["match"]
    b = a.copy()
    b.paste((0, 0, 0), (200, 200, 900, 700))
    r = compare_images(a, b)
    assert not r["match"] and r["changed_frac"] > 0.1
