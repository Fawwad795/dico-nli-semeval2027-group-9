"""Glyph-box and overlap helpers, cross-slide consistency, and the fix planner's minimum-size guard."""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from pcv.checks_dom import check_deck, glyph_box, inside, inter, is_ancestor
from pcv.deckcfg import DEFAULTS, Deck, _merge
from pcv.fixes import plan_fixes


def R(x, y, w, h):
    return {"x": x, "y": y, "w": w, "h": h}


def test_glyph_box_is_middle_70_percent():
    g = glyph_box(R(10, 100, 300, 100))
    assert g == pytest.approx(R(10, 115, 300, 70))


def test_inter_overlap_and_disjoint():
    assert inter(R(0, 0, 100, 50), R(50, 25, 100, 50)) == (50, 25)
    assert inter(R(0, 0, 10, 10), R(20, 20, 10, 10)) == (0.0, 0.0)
    assert inter(R(0, 0, 10, 10), R(10, 0, 10, 10)) == (0.0, 10)  # touching edges share no area


def test_inside_with_tolerance():
    box = R(0, 0, 1920, 1080)
    assert inside(R(0, 0, 1920, 1080), box)
    assert inside(R(-0.9, 0, 1920, 1080), box)           # within the 1 px tolerance
    assert not inside(R(-2, 0, 100, 100), box)
    assert not inside(R(1900, 0, 40, 10), box)
    assert inside(R(1900, 0, 21.5, 10), box, tol=2.0)


@pytest.mark.parametrize("a, b, want", [
    ("", "div:nth-child(1)", True),                         # root is everyone's ancestor
    ("div:nth-child(1)", "div:nth-child(1)", True),
    ("div:nth-child(1)", "div:nth-child(1) > p:nth-child(2)", True),
    ("div:nth-child(1)", "div:nth-child(10)", False),       # prefix of the string, not of the path
    ("div:nth-child(1) > p:nth-child(2)", "div:nth-child(1)", False),
])
def test_is_ancestor(a, b, want):
    assert is_ancestor(a, b) is want


def _title(size, x=120.0, text="t"):
    return {"titles": [{"fontSize": size, "rect": R(x, 120, 900, 70), "text": text}], "texts": []}


def test_check_deck_flags_single_off_size_title_and_position():
    doms = {1: _title(56, text="a"), 2: _title(56, text="b"), 3: _title(60, text="c"), 4: _title(56, 200, text="d")}
    F = check_deck(doms, DEFAULTS["rules"])
    got = {(f["code"], f["slide"]) for f in F}
    assert ("title-size-inconsistent", 3) in got
    assert ("title-position-inconsistent", 4) in got
    assert not any(s in (1, 2) for _, s in got)


def test_check_deck_ignores_deliberate_section_title_and_needs_three_slides():
    # a 96px section title differs by more than 25 % -> a deliberate style, not drift
    doms = {1: _title(56, text="a"), 2: _title(56, text="b"), 3: _title(96, text="c")}
    assert not [f for f in check_deck(doms, DEFAULTS["rules"]) if f["code"] == "title-size-inconsistent"]
    assert check_deck({1: _title(56, text="a"), 2: _title(60, text="b")}, DEFAULTS["rules"]) == []


def test_check_deck_duplicate_titles_and_too_many_families():
    doms = {i: _title(56, text="Same claim") for i in (1, 2, 3)}
    for i, fam in zip((1, 2, 3), ("A", "B", "C")):
        doms[i]["texts"] = [{"font": {"family": f"{fam}, serif"}}, {"font": {"family": "D"}}]
    codes = [(f["code"], f["slide"]) for f in check_deck(doms, DEFAULTS["rules"])]
    assert ("duplicate-title", 2) in codes and ("duplicate-title", 3) in codes
    assert ("too-many-families", None) in codes


def _deck(tmp_path: Path, min_font=20) -> Deck:
    return Deck(tmp_path, _merge(DEFAULTS, {"slides": ["01-a.html", "02-b.html"], "rules": {"min_font_px": min_font}}))


def _clip(font, ratio, slide=2):
    return {"code": "text-clipped", "slide": slide, "message": "m",
            "fix": {"kind": "shrink-text", "path": "div:nth-child(2)", "font_px": font, "ratio": ratio}}


def test_plan_fixes_shrinks_with_margin_and_selector(tmp_path):
    apply, refuse = plan_fixes(_deck(tmp_path), [_clip(48, 0.6)])
    assert refuse == []
    assert apply == [{"stem": "02-b", "slide": 2, "selector": "[data-pcv-slide] > div:nth-child(2)",
                      "prop": "font-size", "value": f"{math.floor(48 * 0.6 * 0.97)}px", "code": "text-clipped", "message": "m"}]


def test_plan_fixes_never_goes_below_min_font(tmp_path):
    apply, refuse = plan_fixes(_deck(tmp_path, min_font=20), [_clip(48, 0.4)])  # 48*0.4*0.97 = 18.6
    assert apply == [] and len(refuse) == 1 and "below the 20px minimum" in refuse[0]["reason"]


def test_plan_fixes_object_fit_and_skips(tmp_path):
    f_fit = {"code": "image-distorted", "slide": 1, "message": "m",
             "fix": {"kind": "object-fit", "path": "img:nth-child(3)", "value": "contain"}}
    fixed = {**_clip(48, 0.5), "status": "fixed"}
    no_fix = {"code": "text-overlap", "slide": 1, "message": "m", "fix": None}
    full = _clip(48, 1.0)  # a shrink finding whose ratio could not be measured
    apply, refuse = plan_fixes(_deck(tmp_path), [f_fit, fixed, no_fix, full])
    assert [(a["prop"], a["value"], a["stem"]) for a in apply] == [("object-fit", "contain", "01-a")]
    # Not silently dropped: it is refused with a reason, so the report lists it for a person.
    assert len(refuse) == 1 and refuse[0]["slide"] == 2 and "no shrink ratio" in refuse[0]["reason"]
