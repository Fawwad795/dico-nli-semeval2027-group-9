"""Checks on the delivered files: PPTX integrity and image placement, slide order by image hash,
PDF pages, and a render-back through PowerPoint compared with the original images."""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from .assemble import PDF_H_PT, PDF_W_PT, SLIDE_H_EMU, SLIDE_W_EMU
from .util import SKILL_DIR, finding, sha256_file

COMPARE_SIZE = (960, 540)


def _gray(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L").resize(COMPARE_SIZE, Image.Resampling.LANCZOS), dtype=np.int16)


def compare_images(a: Image.Image, b: Image.Image) -> dict:
    """Mean absolute difference and the share of pixels that differ by more than 16 levels after a
    3x3 erosion, so resampling halos on glyph edges do not count, but moved or missing content does."""
    ga, gb = _gray(a), _gray(b)
    diff = np.abs(ga - gb)
    mask = Image.fromarray(((diff > 16) * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))
    frac = float((np.asarray(mask) > 0).mean())
    return {"mean_abs": round(float(diff.mean()), 3), "changed_frac": round(frac, 5),
            "match": bool(diff.mean() < 3.0 and frac < 0.005)}


def check_pptx(pptx: Path, images: list[Path]) -> list[dict]:
    F: list[dict] = []
    if not pptx.is_file():
        return [finding("pptx-missing", "critical", "technical", f"{pptx.name} was not produced.")]
    try:
        with zipfile.ZipFile(pptx) as z:
            bad = z.testzip()
        if bad:
            return [finding("pptx-corrupt", "critical", "technical", f"Corrupt member in {pptx.name}: {bad}.")]
        from pptx import Presentation
        prs = Presentation(str(pptx))
    except Exception as e:
        return [finding("pptx-corrupt", "critical", "technical", f"{pptx.name} does not open: {e}.")]
    if (prs.slide_width, prs.slide_height) != (SLIDE_W_EMU, SLIDE_H_EMU):
        F.append(finding("pptx-size", "critical", "technical",
                         f"Slide size {prs.slide_width}x{prs.slide_height} EMU is not 16:9 widescreen.", None))
    slides = list(prs.slides)
    if len(slides) != len(images):
        F.append(finding("pptx-count", "critical", "technical",
                         f"{len(slides)} PowerPoint slides for {len(images)} rendered images.", None))
    want: dict[str, list[int]] = {}
    for k, p in enumerate(images, start=1):
        want.setdefault(sha256_file(p), []).append(k)  # identical slides (a repeated divider) share a hash
    for i, s in enumerate(slides, start=1):
        pics = [sh for sh in s.shapes if sh.shape_type == 13]
        others = [sh for sh in s.shapes if sh.shape_type != 13]
        if len(pics) != 1:
            F.append(finding("pptx-picture-count", "critical", "technical", f"Slide has {len(pics)} pictures, expected 1.", i))
            continue
        if others:
            F.append(finding("pptx-extra-shapes", "major", "technical", f"Slide has {len(others)} shapes besides the slide image.", i))
        p = pics[0]
        if (p.left, p.top, p.width, p.height) != (0, 0, prs.slide_width, prs.slide_height):
            F.append(finding("pptx-image-placement", "critical", "technical",
                             f"Image at ({p.left}, {p.top}) size {p.width}x{p.height} EMU does not cover the slide exactly.", i))
        if any(getattr(p, f"crop_{k}") for k in ("left", "right", "top", "bottom")):
            F.append(finding("pptx-image-cropped", "critical", "technical", "Slide image is cropped inside PowerPoint.", i))
        h = hashlib.sha256(p.image.blob).hexdigest()
        if h not in want:
            F.append(finding("slide-image-mismatch", "critical", "technical", "Slide image matches no rendered slide.", i))
        elif i not in want[h]:
            F.append(finding("slide-order-mismatch", "critical", "technical",
                             f"PowerPoint slide {i} shows rendered slide {want[h][0]}.", i, {"shows": want[h][0]}))
        if not (p._element.nvPicPr.cNvPr.get("descr") or "").strip():
            F.append(finding("pptx-no-alt-text", "minor", "technical", "Slide image has no alt text.", i))
    return F


def check_pdf(pdf: Path, images: list[Path]) -> list[dict]:
    F: list[dict] = []
    if not pdf.is_file():
        return [finding("pdf-missing", "critical", "technical", f"{pdf.name} was not produced.")]
    import pymupdf as fitz
    try:
        doc = fitz.open(pdf)
    except Exception as e:
        return [finding("pdf-corrupt", "critical", "technical", f"{pdf.name} does not open: {e}.")]
    with doc:
        if doc.page_count != len(images):
            F.append(finding("pdf-count", "critical", "technical", f"{doc.page_count} PDF pages for {len(images)} slides.", None))
        for i, (page, img) in enumerate(zip(doc, images), start=1):
            if abs(page.rect.width - PDF_W_PT) > 0.5 or abs(page.rect.height - PDF_H_PT) > 0.5:
                F.append(finding("pdf-page-size", "major", "technical", f"Page is {page.rect.width}x{page.rect.height} pt.", i))
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            got = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            with Image.open(img) as ref:
                cmp = compare_images(ref, got)
            if not cmp["match"]:
                F.append(finding("pdf-mismatch", "critical", "technical",
                                 f"PDF page differs from the rendered slide (mean diff {cmp['mean_abs']}).", i, cmp))
    return F


def renderback(pptx: Path, images: list[Path], out: Path) -> tuple[list[dict], dict]:
    """Open the PPTX in PowerPoint (Windows) and compare its own export with the rendered images."""
    info: dict = {"engine": None}
    if platform.system() != "Windows" or not shutil.which("powershell"):
        return [finding("renderback-unavailable", "info", "technical",
                        "PowerPoint render-back needs Windows with PowerPoint; not verified on this machine.")], info
    rb = out / "renderback"
    if rb.exists():
        shutil.rmtree(rb)
    with Image.open(images[0]) as im:
        w, h = im.size
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SKILL_DIR / "scripts" / "renderback.ps1"),
           "-Pptx", str(pptx.resolve()), "-OutDir", str(rb.resolve()), "-Width", str(w), "-Height", str(h)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except Exception as e:
        return [finding("renderback-unavailable", "info", "technical", f"PowerPoint render-back failed to start: {e}")], info
    if res.returncode != 0:
        text = (res.stderr or res.stdout).strip()
        lines = [l for l in text.splitlines() if l.strip()]
        detail = " | ".join(lines[:3])[:300]
        if "80040154" in text or "COM class factory" in text or "PowerPoint.Application" in text and "not" in text.lower():
            return [finding("renderback-unavailable", "info", "technical",
                            "PowerPoint is not installed or not registered; render-back not verified. " + detail)], info
        return [finding("renderback-failed", "major", "technical", "PowerPoint failed to open or export the deck: " + detail)], info
    try:
        info = json.loads(res.stdout.strip().splitlines()[-1])
    except Exception:
        info = {}
    info["engine"] = "PowerPoint"
    F: list[dict] = []
    results = []
    for i, img in enumerate(images, start=1):
        got = rb / f"slide-{i:02d}.png"
        if not got.is_file():
            F.append(finding("renderback-missing", "critical", "technical", "PowerPoint exported no image for this slide.", i))
            continue
        with Image.open(img) as a, Image.open(got) as b:
            cmp = compare_images(a, b)
        results.append({"slide": i, **cmp})
        if not cmp["match"]:
            F.append(finding("renderback-mismatch", "critical", "technical",
                             f"PowerPoint shows this slide differently from the design render (mean diff {cmp['mean_abs']}, "
                             f"changed {cmp['changed_frac'] * 100:.2f} %).", i, cmp))
    info["comparisons"] = results
    pdf = rb / "powerpoint-export.pdf"
    info["powerpoint_pdf"] = pdf.is_file()
    return F, info
