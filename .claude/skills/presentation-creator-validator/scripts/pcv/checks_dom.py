"""Layout, typography and asset checks on the geometry the renderer measured in the live page."""
from __future__ import annotations

from collections import Counter

from .util import finding

GENERIC_FAMILIES = {"serif", "sans-serif", "monospace", "system-ui", "cursive", "fantasy", "ui-sans-serif",
                    "ui-serif", "ui-monospace", "ui-rounded", "math", "emoji", "fangsong"}
TOL = 1.0


def first_family(css_family: str) -> str:
    return css_family.split(",")[0].strip().strip("'\"")


def glyph_box(r: dict) -> dict:
    """A text rect covers ascent+descent; the inked band is roughly its middle 70 %."""
    return {"x": r["x"], "y": r["y"] + 0.15 * r["h"], "w": r["w"], "h": 0.7 * r["h"]}


def inter(a: dict, b: dict) -> tuple[float, float]:
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return max(0.0, w), max(0.0, h)


def inside(r: dict, box: dict, tol: float = TOL) -> bool:
    return (r["x"] >= box["x"] - tol and r["y"] >= box["y"] - tol
            and r["x"] + r["w"] <= box["x"] + box["w"] + tol and r["y"] + r["h"] <= box["y"] + box["h"] + tol)


def is_ancestor(a: str, b: str) -> bool:
    """True when path a is an ancestor of (or equal to) path b; '' is the slide root."""
    return a == "" or b == a or b.startswith(a + " > ")


def check_slide(dom: dict, slide: int, rules: dict, size: tuple[int, int]) -> list[dict]:
    W, H = size
    F: list[dict] = []
    if "error" in dom:
        return [finding("slide-root-missing", "critical", "technical", dom["error"], slide)]
    root = dom["root"]
    if abs(root["x"]) > TOL or abs(root["y"]) > TOL or abs(root["w"] - W) > TOL or abs(root["h"] - H) > TOL:
        F.append(finding("slide-root-size", "critical", "technical",
                         f"Slide root is {root['w']}x{root['h']} at ({root['x']}, {root['y']}), expected {W}x{H} at the origin.",
                         slide, {"root": root}))
    slide_box = {"x": 0, "y": 0, "w": W, "h": H}
    m = rules["safe_margin_px"]
    safe = {"x": m, "y": m, "w": W - 2 * m, "h": H - 2 * m}
    min_px = rules["min_font_px"]
    blocks = dom["blocks"]

    seen: set[tuple[str, str]] = set()

    def once(code: str, key: str) -> bool:
        if (code, key) in seen:
            return False
        seen.add((code, key))
        return True

    for t in dom["texts"]:
        fl = t["flags"]
        bpath = blocks[t["block"]]["path"]
        for r in t["rects"]:
            g = glyph_box(r)
            if not fl["bleed"] and not inside(g, slide_box) and once("text-out-of-bounds", bpath):
                F.append(finding("text-out-of-bounds", "critical", "layout",
                                 f"Text runs off the slide: “{t['text'][:60]}”.", slide,
                                 {"path": bpath, "rect": r}))
            for c in t["clips"]:
                box = c["rect"]
                cut = (c["x"] and (g["x"] < box["x"] - TOL or g["x"] + g["w"] > box["x"] + box["w"] + TOL)) or \
                      (c["y"] and (g["y"] < box["y"] - TOL or g["y"] + g["h"] > box["y"] + box["h"] + TOL))
                if cut and once("text-clipped", bpath):
                    F.append(finding("text-clipped", "critical", "layout",
                                     f"Text is cut off by its container: “{t['text'][:60]}”.", slide,
                                     {"path": bpath, "clip_path": c["path"], "clip_rect": box, "rect": r,
                                      "font_px": t["font"]["size"]},
                                     fix={"kind": "shrink-text", "path": bpath,
                                          "font_px": t["font"].get("cssSize", t["font"]["size"]),
                                          "scale": t["font"]["size"] / (t["font"].get("cssSize") or t["font"]["size"]),
                                          "ratio": _fit_ratio(t, c)}))
            if not fl["bleed"] and inside(g, slide_box) and not inside(g, safe, 2.0) and once("outside-safe-area", bpath):
                F.append(finding("outside-safe-area", "minor", "layout",
                                 f"Text sits inside the {m}px safe margin: “{t['text'][:60]}”.", slide,
                                 {"path": bpath, "rect": r}))
        if not fl["small"] and t["font"]["size"] < min_px - 0.01 and once("text-too-small", f"{bpath}|{t['font']['size']}"):
            F.append(finding("text-too-small", "major", "typography",
                             f"{t['font']['size']:g}px text is below the {min_px}px minimum: “{t['text'][:60]}”.",
                             slide, {"path": bpath, "font_px": t["font"]["size"]}))
        scale = rules.get("type_scale")
        if scale and not any(abs(t["font"]["size"] - s) < 0.51 for s in scale) and once("off-scale-font-size", str(t["font"]["size"])):
            F.append(finding("off-scale-font-size", "minor", "typography",
                             f"{t['font']['size']:g}px is not on the type scale {scale}.", slide,
                             {"path": bpath, "font_px": t["font"]["size"]}))

    # Text overlapping text from an unrelated block.
    lines = [(t, glyph_box(r)) for t in dom["texts"] for r in t["rects"]]
    for i in range(len(lines)):
        ti, ri = lines[i]
        for j in range(i + 1, len(lines)):
            tj, rj = lines[j]
            if ti["block"] == tj["block"] or ti["flags"]["overlap"] or tj["flags"]["overlap"]:
                continue
            bi, bj = blocks[ti["block"]], blocks[tj["block"]]
            if bi["overlapAllowed"] or bj["overlapAllowed"] or is_ancestor(bi["path"], bj["path"]) or is_ancestor(bj["path"], bi["path"]):
                continue
            w, h = inter(ri, rj)
            if w > 2 and h > 2 and w * h > 0.1 * min(ri["w"] * ri["h"], rj["w"] * rj["h"]):
                key = "|".join(sorted((bi["path"], bj["path"])))
                if once("text-overlap", key):
                    F.append(finding("text-overlap", "major", "layout",
                                     f"Text overlaps other text: “{ti['text'][:40]}” and “{tj['text'][:40]}”.",
                                     slide, {"a": bi["path"], "b": bj["path"], "rect_a": ri, "rect_b": rj}))

    # Text over a graphic that is not its own container.
    for g in dom["graphics"]:
        if g["decor"] or g["overlap"]:
            continue
        for t, r in lines:
            if t["flags"]["overlap"] or is_ancestor(g["path"], t["path"]):
                continue
            w, h = inter(r, g["rect"])
            if w > 2 and h > 2 and w * h > 0.1 * r["w"] * r["h"] and once("text-over-graphic", g["path"] + t["path"]):
                F.append(finding("text-over-graphic", "major", "layout",
                                 f"Text overlaps a {g['kind']}: “{t['text'][:40]}”.", slide,
                                 {"graphic": g["path"], "text": t["path"]}))

    # Text whose inked lines spill out of its own (fixed-size, unclipped) box onto its neighbours.
    # Compared on glyph boxes, not scrollWidth/Height: Chrome counts glyph overhang into scroll
    # sizes, which flags every tight-leading heading.
    by_block: dict[int, list[dict]] = {}
    for t in dom["texts"]:
        by_block.setdefault(t["block"], []).extend(glyph_box(r) for r in t["rects"])
    for bi, rs in by_block.items():
        b = blocks[bi]
        if b["isRoot"] or b["svg"] or b["overflow"] != ["visible", "visible"] or b["rect"]["w"] <= 0:
            continue
        x0, y0 = min(r["x"] for r in rs), min(r["y"] for r in rs)
        x1, y1 = max(r["x"] + r["w"] for r in rs), max(r["y"] + r["h"] for r in rs)
        box = b["rect"]
        tol = max(2.0, 0.25 * b["fontSize"])
        over_x = max(box["x"] - x0, x1 - (box["x"] + box["w"]))
        over_y = max(box["y"] - y0, y1 - (box["y"] + box["h"]))
        if over_x > tol or over_y > tol:
            ratio = 1.0
            if over_x > tol:
                ratio = min(ratio, box["w"] / (x1 - x0))
            if over_y > tol and box["h"] > 0:
                ratio = min(ratio, box["h"] / (y1 - y0))
            F.append(finding("text-overflows-box", "major", "layout",
                             f"Text in <{b['tag']}> spills {max(over_x, over_y):.0f}px outside its {box['w']:.0f}x{box['h']:.0f}px box.",
                             slide, {"path": b["path"], "box": box, "text_extent": [x0, y0, x1, y1]},
                             fix={"kind": "shrink-text", "path": b["path"], "font_px": b["fontSize"], "ratio": round(ratio, 4)}))

    for g in dom["graphics"]:
        if not g["bleed"] and not inside(g["rect"], slide_box, 2.0):
            F.append(finding("graphic-out-of-bounds", "major", "layout",
                             f"A {g['kind']} extends past the slide edge.", slide, {"path": g["path"], "rect": g["rect"]}))
        if g["kind"] != "img":
            continue
        if not g["complete"] or g["natural"][0] == 0:
            F.append(finding("missing-asset", "critical", "technical", f"Image did not load: {g['src'] or '(no src)'}.",
                             slide, {"path": g["path"], "src": g["src"]}))
            continue
        nw, nh = g["natural"]
        rw, rh = g["rect"]["w"], g["rect"]["h"]
        if not g["vector"] and g["objectFit"] in ("fill", "") and rh > 0 and abs((rw / rh) / (nw / nh) - 1) > 0.02:
            F.append(finding("image-distorted", "major", "visual_design",
                             f"Image is stretched: natural {nw}x{nh}, shown {rw:.0f}x{rh:.0f} with object-fit {g['objectFit']}.",
                             slide, {"path": g["path"], "src": g["src"]},
                             fix={"kind": "object-fit", "path": g["path"], "value": "contain"}))
        dpr = dom["viewport"][2]
        if not g["vector"] and nw < 0.8 * rw * dpr:
            sev = "major" if nw < 0.5 * rw * dpr else "minor"
            F.append(finding("image-low-resolution", sev, "visual_design",
                             f"Image is upscaled: {nw}px wide source shown at {rw * dpr:.0f} device px.", slide,
                             {"path": g["path"], "src": g["src"]}))

    titles = dom["titles"]
    if rules["require_title"] and not titles:
        F.append(finding("no-title", "minor", "hierarchy", "Slide has no element matching the title selector.", slide))
    for t in titles:
        if t["lines"] > rules["max_title_lines"]:
            F.append(finding("title-wraps", "major", "typography",
                             f"Title wraps to {t['lines']} lines (limit {rules['max_title_lines']}): “{t['text'][:80]}”.",
                             slide, {"path": t["path"], "lines": t["lines"]}))

    words = sum(len(t["text"].split()) for t in dom["texts"] if not t["flags"]["source"] and not t["flags"]["nocheck"])
    if words > rules["max_words"]:
        F.append(finding("dense-slide", "minor", "hierarchy", f"{words} words on the slide (limit {rules['max_words']}).",
                         slide, {"words": words}))

    for c in dom["charts"]:
        spec = c["spec"] or {}
        if spec.get("type") == "bar" and (spec.get("yMin") or 0) > 0:
            F.append(finding("truncated-bar-axis", "major", "data_visualization",
                             f"Bar chart axis starts at {spec.get('yMin')}, not 0; bar lengths exaggerate differences.",
                             slide, {"path": c["path"]}))
        for v in spec.get("valueLabels", []):
            if v not in c["labels"]:
                F.append(finding("chart-label-mismatch", "major", "data_visualization",
                                 f"Chart data value {v} has no matching label in the drawing.", slide, {"path": c["path"]}))

    F.extend(_font_findings(dom, slide))
    for line in dom.get("console", []):
        F.append(finding("console-error", "minor", "technical", f"Browser console: {line[:200]}", slide))
    for n in dom.get("network", []):
        if n["result"] in ("blocked", "missing", "fetch-failed") or n["result"].startswith("http-"):
            F.append(finding("asset-request-failed", "major", "technical",
                             f"Request {n['result']}: {n['url'][:160]}", slide, {"url": n["url"]}))
    return F


def _fit_ratio(t: dict, c: dict) -> float:
    xs = [r["x"] for r in t["rects"]] + [r["x"] + r["w"] for r in t["rects"]]
    ys = [r["y"] for r in t["rects"]] + [r["y"] + r["h"] for r in t["rects"]]
    need_w, need_h = max(xs) - min(xs), max(ys) - min(ys)
    box = c["rect"]
    ratio = 1.0
    if c["x"] and need_w > box["w"]:
        ratio = min(ratio, box["w"] / need_w)
    if c["y"] and need_h > box["h"]:
        ratio = min(ratio, box["h"] / need_h)
    return round(ratio, 4)


def _font_findings(dom: dict, slide: int) -> list[dict]:
    F = []
    faces = dom.get("faces", [])
    for f in faces:
        if f["status"] == "error":
            F.append(finding("font-load-failed", "major", "typography", f"Web font failed to load: {f['family']} {f['weight']}.",
                             slide, {"face": f}))
    loaded = {f["family"].lower() for f in faces if f["status"] == "loaded"}
    declared = {f["family"].lower() for f in faces}
    pf = dom.get("platformFonts", {})
    for s in dom.get("fontSamples", []):
        want = first_family(s["family"])
        if want.lower() in GENERIC_FAMILIES:
            continue
        used = pf.get(str(s["fid"]), [])
        if not used:
            continue
        if want.lower() in declared:
            ok = want.lower() in loaded and any(u.get("isCustomFont") for u in used)
        else:
            ok = any(u["familyName"].lower().startswith(want.lower()) for u in used)
        if not ok:
            got = ", ".join(sorted({u["familyName"] for u in used}))
            F.append(finding("font-fallback", "major", "typography",
                             f"Requested “{want}” but Chrome drew “{s['text']}” with {got}.", slide,
                             {"requested": s["family"], "used": used}))
    return F


def check_deck(doms: dict[int, dict], rules: dict) -> list[dict]:
    """Cross-slide consistency: title sizes, title positions, number of type families, duplicate titles."""
    F: list[dict] = []
    titles = {i: d["titles"][0] for i, d in doms.items() if d.get("titles")}
    if len(titles) >= 3:
        sizes = Counter(round(t["fontSize"]) for t in titles.values())
        mode, _ = sizes.most_common(1)[0]
        for i, t in titles.items():
            s = round(t["fontSize"])
            if s != mode and sizes[s] == 1 and abs(s - mode) / mode < 0.25:
                F.append(finding("title-size-inconsistent", "minor", "consistency",
                                 f"Title is {s}px where the other content slides use {mode}px.", i,
                                 {"font_px": s, "deck_mode_px": mode}))
        xs = Counter(round(t["rect"]["x"]) for t in titles.values() if round(t["fontSize"]) == mode)
        if xs:
            xmode, _ = xs.most_common(1)[0]
            for i, t in titles.items():
                if round(t["fontSize"]) == mode and abs(t["rect"]["x"] - xmode) > 4:
                    F.append(finding("title-position-inconsistent", "minor", "consistency",
                                     f"Title starts at x={t['rect']['x']:.0f}px; the other titles start at {xmode}px.", i))
        seen: dict[str, int] = {}
        for i, t in sorted(titles.items()):
            key = t["text"].lower()
            if key and key in seen:
                F.append(finding("duplicate-title", "minor", "storytelling",
                                 f"Same title as slide {seen[key]}: “{t['text'][:60]}”.", i))
            seen.setdefault(key, i)
    fams = Counter(first_family(t["font"]["family"]) for d in doms.values() for t in d.get("texts", []))
    if len(fams) > 3:
        F.append(finding("too-many-families", "minor", "consistency",
                         f"{len(fams)} type families in the deck: {', '.join(sorted(fams))}.", None, {"families": dict(fams)}))
    return F
