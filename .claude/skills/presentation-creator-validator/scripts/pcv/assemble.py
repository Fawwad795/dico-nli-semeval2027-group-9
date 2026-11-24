"""Full-bleed image PPTX and lossless PDF from the rendered slide images."""
from __future__ import annotations

from pathlib import Path

from .deckcfg import Deck
from .render import load_dom, ordered_images

SLIDE_W_EMU = 12192000  # 13.333 in
SLIDE_H_EMU = 6858000   # 7.5 in
PDF_W_PT, PDF_H_PT = 960, 540  # 13.333 x 7.5 in


def slide_text(out: Path, index: int) -> str:
    try:
        return load_dom(out, index).get("slideText", "").strip()
    except Exception:
        return ""


def assemble_pptx(deck: Deck, out: Path) -> Path:
    from pptx import Presentation
    from pptx.util import Emu

    W, H = deck.size
    if abs(W / H - 16 / 9) > 1e-3:
        raise ValueError(f"canvas {W}x{H} is not 16:9")
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(SLIDE_W_EMU), Emu(SLIDE_H_EMU)
    blank = prs.slide_layouts[6]
    for i, img in enumerate(ordered_images(out), start=1):
        s = prs.slides.add_slide(blank)
        for ph in list(s.placeholders):
            ph._element.getparent().remove(ph._element)
        pic = s.shapes.add_picture(str(img), 0, 0, width=prs.slide_width, height=prs.slide_height)
        pic.name = f"Slide {i}"
        text = slide_text(out, i)
        pic._element.nvPicPr.cNvPr.set("descr", text[:1500] or f"Slide {i}")
        notes = deck.notes_for(i)
        body = "\n\n".join(x for x in (notes, f"Slide text:\n{text}" if text else "") if x)
        if body:
            s.notes_slide.notes_text_frame.text = body
    cp = prs.core_properties
    cp.title = deck.title
    cp.author = deck.cfg.get("author", "")
    cp.comments = "Slides are full-slide images rendered from HTML sources; edit the sources and rebuild."
    path = out / f"{deck.name}.pptx"
    prs.save(path)
    return path


def export_pdf(deck: Deck, out: Path) -> Path:
    import pymupdf as fitz

    doc = fitz.open()
    for img in ordered_images(out):
        page = doc.new_page(width=PDF_W_PT, height=PDF_H_PT)
        page.insert_image(page.rect, filename=str(img), keep_proportion=False)
    doc.set_metadata({"title": deck.title, "author": deck.cfg.get("author", ""),
                      "creator": "presentation-creator-validator"})
    path = out / f"{deck.name}.pdf"
    doc.save(path, deflate=True, garbage=3)
    doc.close()
    return path
