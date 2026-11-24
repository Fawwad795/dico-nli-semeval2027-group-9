"""Checks on the rendered images themselves: exact size, blank output, and WCAG contrast measured
against the pixels actually behind each line of text (handles gradients, panels and photos)."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image

from .util import finding

_RGB = re.compile(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)")


_SRGB = re.compile(r"color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*/\s*([\d.]+%?))?\s*\)")


def parse_color(css: str) -> tuple[tuple[float, float, float], float] | None:
    """rgb()/rgba() and color(srgb ...). Other spaces (oklch, lab, display-p3) return None."""
    m = _RGB.match(css or "")
    if not m:
        s = _SRGB.match(css or "")
        if not s:
            return None
        a = s.group(4)
        alpha = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
        return (float(s.group(1)) * 255, float(s.group(2)) * 255, float(s.group(3)) * 255), alpha
    a = m.group(4)
    alpha = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
    return (float(m.group(1)), float(m.group(2)), float(m.group(3))), alpha


def luminance(rgb) -> float:
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2])


def contrast(a, b) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def background_of(px: np.ndarray, fg=None) -> np.ndarray | None:
    """Most frequent colour in a patch (5-bit quantised), averaged within its bin. Pixels close to the
    text colour are left out first, so large heavy text over a photo or gradient is not taken for its
    own background. When almost every pixel is text-coloured, the background is that colour too (text
    nearly invisible), so the unfiltered mode is used and the contrast failure is reported."""
    flat = px.reshape(-1, 3).astype(np.int32)
    if fg is not None:
        keep = np.abs(flat - np.asarray(fg, dtype=np.int32)).sum(axis=1) > 60
        if keep.mean() >= 0.1:
            flat = flat[keep]
    keys = (flat[:, 0] >> 3) << 10 | (flat[:, 1] >> 3) << 5 | (flat[:, 2] >> 3)
    k = np.bincount(keys).argmax()
    return flat[keys == k].mean(axis=0)


def check_image(img_path: Path, slide: int, expect: tuple[int, int]) -> list[dict]:
    F = []
    if not img_path.is_file():
        return [finding("image-missing", "critical", "technical", f"Rendered image missing: {img_path.name}", slide)]
    with Image.open(img_path) as im:
        if im.size != expect:
            F.append(finding("image-size", "critical", "technical", f"{img_path.name} is {im.size}, expected {expect}.", slide))
        if im.mode == "RGBA" and im.getchannel("A").getextrema()[0] < 255:
            F.append(finding("image-transparency", "minor", "technical",
                             "Slide image has transparent pixels; PowerPoint will show the slide background through them.", slide))
        small = np.asarray(im.convert("L").resize((192, 108)), dtype=float)
    if small.std() < 1.0:
        F.append(finding("blank-slide", "critical", "technical", "Slide image is a single flat colour.", slide))
    return F


def check_contrast(img_path: Path, dom: dict, slide: int) -> list[dict]:
    F = []
    if not img_path.is_file() or "texts" not in dom:
        return F
    dpr = dom["viewport"][2]
    with Image.open(img_path) as im:
        arr = np.asarray(im.convert("RGB"))
    H, W = arr.shape[:2]
    worst: dict[int, tuple[float, dict, list]] = {}
    unmeasured: set[str] = set()
    for t in dom["texts"]:
        if t["flags"]["contrast"]:
            continue
        pc = parse_color(t["color"])
        if not pc:
            unmeasured.add(t["color"])
            continue
        rgb, alpha = pc
        alpha *= t["opacity"]
        size, weight = t["font"]["size"], t["font"]["weight"]
        large = size >= 24 or (size >= 18.66 and weight >= 700)
        need = 3.0 if large else 4.5
        for r in t["rects"]:
            x0, y0 = max(0, int(r["x"] * dpr)), max(0, int(r["y"] * dpr))
            x1, y1 = min(W, int((r["x"] + r["w"]) * dpr)), min(H, int((r["y"] + r["h"]) * dpr))
            if x1 - x0 < 2 or y1 - y0 < 2:
                continue
            bg = background_of(arr[y0:y1, x0:x1], rgb if alpha > 0.5 else None)
            if bg is None:
                unmeasured.add(t["color"])
                continue
            fg = alpha * np.asarray(rgb) + (1 - alpha) * bg
            ratio = contrast(fg, bg)
            if ratio < need and (t["block"] not in worst or ratio < worst[t["block"]][0]):
                worst[t["block"]] = (ratio, t, [need, bg.round().tolist(), fg.round().tolist()])
    for ratio, t, (need, bg, fg) in worst.values():
        sev = "critical" if ratio < 2.0 else "major"
        F.append(finding("low-contrast", sev, "typography",
                         f"Contrast {ratio:.2f}:1 is below {need}:1 for {t['font']['size']:g}px text: “{t['text'][:50]}”.",
                         slide, {"path": t["path"], "ratio": round(ratio, 2), "required": need,
                                 "foreground": fg, "background": bg}))
    unmeasured.discard("none")
    if unmeasured:
        F.append(finding("contrast-unmeasured", "info", "typography",
                         f"Contrast not measured for text coloured {', '.join(sorted(unmeasured))[:120]} (colour space not parsed); check it in the visual review.",
                         slide))
    return F
