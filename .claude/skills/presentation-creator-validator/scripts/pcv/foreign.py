"""VALIDATE mode for a PPTX this skill did not build: export every slide through PowerPoint, read its
text and shape geometry with python-pptx, run the checks that work without a live page, and build
the review kit. Clipping, glyph overlap and font fallback need the live page; the report says so."""
from __future__ import annotations

import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .checks_content import check_content
from .checks_image import check_image
from .review import load_review, make_kit, review_findings
from .score import report_md, score
from .util import SKILL_DIR, finding, read_json, sha256_file, write_json

EMU_PER_IN = 914400


def _iter_shapes(shapes):
    for sh in shapes:
        if sh.shape_type == 6:  # group
            yield from _iter_shapes(sh.shapes)
        else:
            yield sh


def _shape_texts(sh) -> list[tuple[str, float | None]]:
    """(paragraph text, smallest explicit run size in pt or None) for a shape's text and table cells."""
    frames = []
    if getattr(sh, "has_text_frame", False) and sh.has_text_frame:
        frames.append(sh.text_frame)
    if getattr(sh, "has_table", False) and sh.has_table:
        frames += [c.text_frame for r in sh.table.rows for c in r.cells]
    out = []
    for tf in frames:
        for p in tf.paragraphs:
            t = "".join(r.text for r in p.runs).strip()
            if not t:
                continue
            sizes = [r.font.size.pt for r in p.runs if r.font.size is not None]
            out.append((t, min(sizes) if sizes else None))
    return out


def inspect_pptx(pptx: Path, out: Path, sources: list[Path], glossary: list[str], min_font_px: float = 20,
                 width: int = 3840) -> dict:
    from pptx import Presentation

    pptx = pptx.resolve()
    out.mkdir(parents=True, exist_ok=True)
    F: list[dict] = []
    try:
        prs = Presentation(str(pptx))
    except Exception as e:
        raise SystemExit(f"{pptx.name} does not open: {e}")
    sw, sh_ = prs.slide_width, prs.slide_height
    ratio = sw / sh_
    if abs(ratio - 16 / 9) > 1e-3:
        F.append(finding("pptx-size", "minor", "technical", f"Slide size {sw / EMU_PER_IN:.2f}x{sh_ / EMU_PER_IN:.2f} in is not 16:9.", None))
    height = round(width / ratio)
    px_per_pt = (1920 / (sw / EMU_PER_IN)) / 72  # size on a 1920-wide canvas, comparable with HTML decks

    doms: dict[int, dict] = {}
    for i, s in enumerate(prs.slides, start=1):
        texts, seen_small = [], set()
        boxes = []
        for shp in _iter_shapes(s.shapes):
            for t, pt in _shape_texts(shp):
                texts.append({"text": t, "path": shp.name, "flags": {"nocheck": False, "source": False, "spelling": False}})
                if pt is not None and pt * px_per_pt < min_font_px - 0.01 and (shp.name, pt) not in seen_small:
                    seen_small.add((shp.name, pt))
                    F.append(finding("text-too-small", "major", "typography",
                                     f"{pt:g} pt text (= {pt * px_per_pt:.0f}px on a 1920px canvas) is below {min_font_px:g}px: “{t[:50]}”.",
                                     i, {"shape": shp.name, "pt": pt}))
            if shp.left is None or shp.width is None:
                continue
            l, tp, w, h = shp.left, shp.top, shp.width, shp.height
            if (l < -EMU_PER_IN * 0.01 or tp < -EMU_PER_IN * 0.01 or l + w > sw * 1.002 or tp + h > sh_ * 1.002) and _shape_texts(shp):
                F.append(finding("text-out-of-bounds", "major", "layout", f"Text shape “{shp.name}” extends past the slide edge.", i))
            if _shape_texts(shp):
                boxes.append((shp.name, l, tp, w, h))
            if getattr(shp, "is_placeholder", False) and getattr(shp, "has_text_frame", False) and shp.has_text_frame and not shp.text_frame.text.strip():
                F.append(finding("empty-placeholder", "minor", "technical", f"Empty placeholder “{shp.name}”.", i))
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                _, l1, t1, w1, h1 = boxes[a]
                _, l2, t2, w2, h2 = boxes[b]
                ow = min(l1 + w1, l2 + w2) - max(l1, l2)
                oh = min(t1 + h1, t2 + h2) - max(t1, t2)
                if ow > 0 and oh > 0 and ow * oh > 0.1 * min(w1 * h1, w2 * h2):
                    F.append(finding("shape-overlap", "minor", "layout",
                                     f"Text frames “{boxes[a][0]}” and “{boxes[b][0]}” overlap (frames, not necessarily glyphs).", i))
        notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
        doms[i] = {"texts": texts, "refs": [], "slideText": "\n".join(t["text"] for t in texts), "notes": notes}
        write_json(out / "dom" / f"{i:02d}.json", doms[i])

    n = len(doms)
    images_dir = out / "images"
    exported = False
    state_p = out / "export-state.json"
    digest = sha256_file(pptx)
    reuse = (state_p.is_file() and read_json(state_p).get("sha256") == digest
             and all((images_dir / f"slide-{i:02d}.png").is_file() for i in range(1, n + 1)))
    if reuse:
        exported = True  # same file as the last export: keep its images, so a review written since stays current
    elif platform.system() == "Windows" and shutil.which("powershell"):
        tmp = out / "export"
        if tmp.exists():
            shutil.rmtree(tmp)
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SKILL_DIR / "scripts" / "renderback.ps1"),
               "-Pptx", str(pptx), "-OutDir", str(tmp.resolve()), "-Width", str(width), "-Height", str(height)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        exported = res.returncode == 0
        if exported:
            if images_dir.exists():
                shutil.rmtree(images_dir)
            images_dir.mkdir(parents=True)
            for i in range(1, n + 1):
                src = tmp / f"slide-{i:02d}.png"
                if src.is_file():
                    shutil.copy2(src, images_dir / f"slide-{i:02d}.png")
            write_json(state_p, {"sha256": digest, "pptx": str(pptx)})
        else:
            F.append(finding("export-failed", "critical", "technical", "PowerPoint could not export the slides: "
                             + ((res.stderr or res.stdout).strip().splitlines() or [""])[-1][:200], None))
    else:
        F.append(finding("export-unavailable", "critical", "technical",
                         "Exporting a foreign PPTX to images needs PowerPoint on Windows; no images, so no visual review is possible here.", None))

    write_json(out / "render-manifest.json", {
        "slides": {str(i): {"id": f"slide-{i:02d}", "image": f"images/slide-{i:02d}.png", "dom": f"dom/{i:02d}.json"} for i in range(1, n + 1)},
        "count": n, "canvas": [1920, round(1920 / ratio)], "scale": width / 1920, "format": "png",
        "browser": "PowerPoint export", "headless": False, "errors": [],
        "rendered": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    if exported:
        for i in range(1, n + 1):
            F += check_image(images_dir / f"slide-{i:02d}.png", i, (width, height))
        if not reuse or not (out / "review" / "contact-sheet.png").is_file():
            make_kit(out)
    # No reference list exists for a foreign deck, so numbered citation markers cannot be resolved here.
    cfg = {"rules": {"number_policy": "major", "min_integer_checked": 10, "require_source_for_numbers": False, "spelling": True},
           "glossary": glossary, "references": {}, "check_citation_markers": False}
    F += check_content(doms, cfg, sources)
    F.append(finding("layout-unchecked", "info", "layout",
                     "Live-page checks (clipped text, glyph overlap, font fallback, measured contrast) cannot run on a foreign PPTX; "
                     "the visual review must cover them.", None))
    for f in F:
        f.setdefault("status", "open")
    stages = {"rendered": exported, "pptx": True, "renderback_verified": None}
    write_json(out / "validation" / "findings.json", {"findings": F, "stages": stages, "slides": n, "renderback": {},
                                                     "render": {"canvas": [1920, round(1920 / ratio)], "scale": width / 1920,
                                                                "format": "png", "browser": "PowerPoint export",
                                                                "headless": False, "rendered": ""}})
    review, problems = load_review(out, n)
    F = F + review_findings(review, problems)
    result = score(F, review, problems, stages)
    meta = {"file": str(pptx), "slides": n, "exported by": "PowerPoint" if exported else "not exported",
            "checks not possible on a foreign PPTX": "clipping, glyph overlap, font fallback, measured contrast",
            "font sizes": "checked only where a text run sets its size explicitly; sizes inherited from paragraphs, "
                          "layouts or masters, and text in charts or SmartArt, are not checked"}
    (out / "validation" / "report.md").write_text(report_md(pptx.stem, result, F, [], [], None if problems else review, problems, meta), encoding="utf-8")
    write_json(out / "validation" / "report.json", {**result, "meta": meta, "review_problems": problems})
    return result
