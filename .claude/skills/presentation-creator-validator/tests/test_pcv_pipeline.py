"""End-to-end: the real CLI renders the deliberate-defect deck in headed Chrome and validates it.

The fixture is copied to pytest's tmp_path (the PNG asset is drawn there with Pillow), so nothing
is ever written under .claude/. PowerPoint render-back is skipped (--no-renderback): it needs a
local PowerPoint and is not what these tests assert.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from pcv.checks_output import check_pptx
from pcv.render import load_dom, ordered_images
from pcv.util import read_json

pytestmark = pytest.mark.browser

TESTS_DIR = Path(__file__).resolve().parent
FIXTURE = TESTS_DIR / "fixtures" / "defect-deck"
DECK_PY = TESTS_DIR.parent / "scripts" / "deck.py"
N_SLIDES = 13
MIN_FONT = 20

EXPECTED = [
    ("text-clipped", 2),
    ("text-out-of-bounds", 3),
    ("text-overlap", 4),
    ("missing-asset", 5),
    ("image-distorted", 6),
    ("title-size-inconsistent", 7),
    ("text-too-small", 8),
    ("low-contrast", 9),
    ("unsupported-number", 10),
    ("missing-reference", 11),
    ("spelling", 12),
    ("text-clipped", 13),
]


def _prepare(tmp: Path) -> Path:
    deck = tmp / "deck"
    shutil.copytree(FIXTURE, deck)
    (deck / "assets").mkdir(exist_ok=True)
    im = Image.new("RGB", (800, 600), (40, 90, 160))
    d = ImageDraw.Draw(im)
    d.rectangle([100, 100, 500, 400], fill=(230, 180, 60))
    d.ellipse([450, 250, 750, 550], fill=(200, 60, 60))
    im.save(deck / "assets" / "photo.png")
    return deck


def _cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    res = subprocess.run([sys.executable, str(DECK_PY), *args], cwd=cwd, env=env, capture_output=True,
                         text=True, encoding="utf-8", timeout=900)
    assert res.returncode == 0, f"deck.py {' '.join(args)} failed:\n{res.stdout}\n{res.stderr}"
    return res


@pytest.fixture(scope="module")
def nofix(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("nofix")
    deck = _prepare(tmp)
    out = tmp / "build"
    res = _cli("build", str(deck), "--out", str(out), "--no-renderback", "--no-fix", cwd=tmp)
    return {"deck": deck, "out": out, "stdout": res.stdout,
            "findings": read_json(out / "validation" / "findings.json")["findings"]}


@pytest.fixture(scope="module")
def fixed(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("fixed")
    deck = _prepare(tmp)
    out = tmp / "build"
    _cli("build", str(deck), "--out", str(out), "--no-renderback", cwd=tmp)
    return {"deck": deck, "out": out, "findings": read_json(out / "validation" / "findings.json")["findings"],
            "log": read_json(out / "validation" / "fix-log.json")}


def _at(findings, code, slide):
    return [f for f in findings if f["code"] == code and f["slide"] == slide]


# ---------- detection ----------

@pytest.mark.parametrize("code, slide", EXPECTED, ids=[f"{c}@{s}" for c, s in EXPECTED])
def test_expected_finding_on_expected_slide(nofix, code, slide):
    assert _at(nofix["findings"], code, slide), \
        f"{code} not reported on slide {slide}; got {[(f['code'], f['slide']) for f in nofix['findings']]}"


def test_defects_are_not_reported_on_other_slides(nofix):
    expected_slides: dict[str, set] = {}
    for code, slide in EXPECTED:
        expected_slides.setdefault(code, set()).add(slide)
    stray = [(f["code"], f["slide"]) for f in nofix["findings"]
             if f["code"] in expected_slides and f["slide"] not in expected_slides[f["code"]]]
    assert stray == []


def test_clean_slide_has_no_critical_or_major_findings(nofix):
    bad = [(f["code"], f["message"]) for f in nofix["findings"] if f["slide"] == 1 and f["severity"] in ("critical", "major")]
    assert bad == []


def test_severities_of_key_defects(nofix):
    F = nofix["findings"]
    assert _at(F, "text-clipped", 2)[0]["severity"] == "critical"
    assert _at(F, "text-out-of-bounds", 3)[0]["severity"] == "critical"
    assert _at(F, "missing-asset", 5)[0]["severity"] == "critical"
    assert _at(F, "low-contrast", 9)[0]["evidence"]["ratio"] < 2.0
    assert _at(F, "unsupported-number", 10)[0]["evidence"]["number"] == "97.3%"
    assert _at(F, "missing-reference", 11)[0]["evidence"]["key"] == "nobody2099"
    assert _at(F, "spelling", 12)[0]["evidence"]["word"] == "resluts"
    assert _at(F, "title-size-inconsistent", 7)[0]["evidence"] == {"font_px": 60, "deck_mode_px": 56}


def test_report_is_not_ready_with_criticals(nofix):
    assert nofix["stdout"].startswith("NOT READY")
    md = (nofix["out"] / "validation" / "report.md").read_text(encoding="utf-8")
    assert "**Status: NOT READY**" in md


# ---------- rendered images ----------

def test_rendered_images_are_exactly_3840x2160(nofix):
    imgs = ordered_images(nofix["out"])
    assert len(imgs) == N_SLIDES
    for p in imgs:
        with Image.open(p) as im:
            assert im.size == (3840, 2160), p.name
    man = read_json(nofix["out"] / "render-manifest.json")
    assert man["scale"] == 2 and man["canvas"] == [1920, 1080] and man["headless"] is False and man["errors"] == []
    assert all(s["size"] == [3840, 2160] for s in man["slides"].values())


# ---------- PPTX ----------

def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def test_pptx_has_one_full_slide_picture_per_slide_matching_the_png(nofix):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    out = nofix["out"]
    prs = Presentation(str(out / "defect-fixture-deck.pptx"))
    imgs = ordered_images(out)
    slides = list(prs.slides)
    assert len(slides) == N_SLIDES
    assert (prs.slide_width, prs.slide_height) == (12192000, 6858000)
    assert abs(prs.slide_width / prs.slide_height - 16 / 9) < 1e-3
    for s, png in zip(slides, imgs):
        shapes = list(s.shapes)
        assert len(shapes) == 1 and shapes[0].shape_type == MSO_SHAPE_TYPE.PICTURE
        pic = shapes[0]
        assert (pic.left, pic.top, pic.width, pic.height) == (0, 0, prs.slide_width, prs.slide_height)
        assert _sha(pic.image.blob) == _sha(png.read_bytes())


def test_built_outputs_pass_output_checks(nofix):
    out_codes = re.compile(r"^(pptx-|pdf-|slide-order|slide-image)")
    assert [f["code"] for f in nofix["findings"] if out_codes.match(f["code"])] == []


def test_swapped_slides_yield_slide_order_mismatch(nofix, tmp_path):
    from pptx import Presentation

    out = nofix["out"]
    imgs = ordered_images(out)
    prs = Presentation(str(out / "defect-fixture-deck.pptx"))
    lst = prs.slides._sldIdLst
    first = list(lst)[0]
    lst.remove(first)
    lst.insert(1, first)  # order is now 2, 1, 3, ...
    swapped = tmp_path / "swapped.pptx"
    prs.save(swapped)
    F = check_pptx(swapped, imgs)
    mism = sorted((f["slide"], f["evidence"]["shows"]) for f in F if f["code"] == "slide-order-mismatch")
    assert mism == [(1, 2), (2, 1)]
    assert all(f["severity"] == "critical" for f in F if f["code"] == "slide-order-mismatch")
    assert check_pptx(out / "defect-fixture-deck.pptx", imgs) == []


# ---------- PDF ----------

def test_pdf_page_count_and_size(nofix):
    import pymupdf

    with pymupdf.open(nofix["out"] / "defect-fixture-deck.pdf") as doc:
        assert doc.page_count == N_SLIDES
        for page in doc:
            assert page.rect.width == pytest.approx(960, abs=0.5)
            assert page.rect.height == pytest.approx(540, abs=0.5)


# ---------- fix loop ----------

def _font_of(out: Path, slide: int, prefix: str) -> float:
    t = next(t for t in load_dom(out, slide)["texts"] if t["text"].startswith(prefix))
    return t["font"]["size"]


def test_fix_loop_resolves_clipped_text_without_going_below_min(fixed):
    F, out, deck = fixed["findings"], fixed["out"], fixed["deck"]
    assert not _at(F, "text-clipped", 2)
    assert {"code": "text-clipped", "slide": 2} in [{k: e[k] for k in ("code", "slide")} for e in fixed["log"]["fixed"]]
    size = _font_of(out, 2, "This sentence is much too long")
    assert MIN_FONT <= size < 48
    css = (deck / "fixes" / "02-clipped.css").read_text(encoding="utf-8")
    px = [int(v) for v in re.findall(r"font-size:\s*(\d+)px", css)]
    assert px and all(v >= MIN_FONT for v in px)
    ledger = read_json(deck / "fixes" / "ledger.json")
    assert any(e["stem"] == "02-clipped" and e["code"] == "text-clipped" for e in ledger)


def test_fix_loop_refuses_fit_that_needs_text_below_min(fixed):
    F, out, deck = fixed["findings"], fixed["out"], fixed["deck"]
    refused = [r for r in fixed["log"]["refused"] if r["slide"] == 13]
    assert refused and refused[0]["code"] == "text-clipped" and f"{MIN_FONT}px minimum" in refused[0]["reason"]
    assert _at(F, "text-clipped", 13)  # still reported, not hidden
    assert not (deck / "fixes" / "13-clipped-hard.css").exists()
    assert _font_of(out, 13, "This sentence is much too long") == 48


def test_fix_loop_letterboxes_stretched_image(fixed):
    assert not _at(fixed["findings"], "image-distorted", 6)
    assert "object-fit: contain" in (fixed["deck"] / "fixes" / "06-stretched.css").read_text(encoding="utf-8")


def test_fix_loop_leaves_unfixable_defects_reported(fixed):
    F = fixed["findings"]
    for code, slide in (("text-overlap", 4), ("missing-asset", 5), ("text-too-small", 8), ("low-contrast", 9),
                        ("unsupported-number", 10), ("missing-reference", 11), ("spelling", 12)):
        assert _at(F, code, slide), f"{code} on slide {slide} vanished after the fix loop"
