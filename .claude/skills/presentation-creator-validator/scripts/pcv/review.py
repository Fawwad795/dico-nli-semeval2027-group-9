"""The visual-review kit (previews, contact sheet, template) and validation of the returned review."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .render import ordered_images
from .util import CATEGORIES, SEVERITIES, finding, read_json, write_json

MODEL_CATEGORIES = [c for c in CATEGORIES if c != "technical"]


def make_kit(out: Path, preview_width: int = 1920) -> dict:
    rv = out / "review"
    rv.mkdir(parents=True, exist_ok=True)
    imgs = ordered_images(out)
    previews = []
    for i, p in enumerate(imgs, start=1):
        with Image.open(p) as im:
            h = round(im.height * preview_width / im.width)
            q = rv / f"slide-{i:02d}.png"
            im.convert("RGB").resize((preview_width, h), Image.Resampling.LANCZOS).save(q)
            previews.append(q.name)
    sheet = contact_sheet(imgs, rv / "contact-sheet.png")
    # Deliberately empty: the reviewer fills these in only for what they actually opened.
    template = {
        "reviewer": "independent-subagent | same-session | human",
        "inspected": [],
        "contact_sheet_inspected": False,
        "categories": {c: {"score": None, "rationale": "", "slides": []} for c in MODEL_CATEGORIES},
        "findings": [{"severity": "major", "category": "hierarchy", "slide": 1, "message": "", "recommendation": ""}],
        "slide_notes": {str(i): "" for i in range(1, len(imgs) + 1)},
    }
    write_json(rv / "review-template.json", template)
    return {"previews": previews, "contact_sheet": sheet.name, "dir": str(rv)}


def contact_sheet(imgs: list[Path], path: Path, cols: int = 4, thumb_w: int = 640, gap: int = 24) -> Path:
    rows = (len(imgs) + cols - 1) // cols
    th = round(thumb_w * 9 / 16)
    label_h = 40
    W = cols * thumb_w + (cols + 1) * gap
    H = rows * (th + label_h) + (rows + 1) * gap
    sheet = Image.new("RGB", (W, H), (236, 236, 232))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for k, p in enumerate(imgs):
        r, c = divmod(k, cols)
        x = gap + c * (thumb_w + gap)
        y = gap + r * (th + label_h + gap)
        with Image.open(p) as im:
            sheet.paste(im.convert("RGB").resize((thumb_w, th), Image.Resampling.LANCZOS), (x, y))
        draw.rectangle([x - 1, y - 1, x + thumb_w, y + th], outline=(180, 180, 175))
        draw.text((x, y + th + 8), f"{k + 1:02d}  {p.stem}", fill=(40, 40, 40), font=font)
    sheet.save(path)
    return path


def load_review(out: Path, n_slides: int) -> tuple[dict | None, list[str]]:
    p = out / "review" / "review.json"
    if not p.is_file():
        return None, ["no review.json: the visual review has not been done"]
    try:
        rv = read_json(p)
    except Exception as e:
        return None, [f"review.json is not valid JSON: {e}"]
    problems = []
    try:
        newest = max(i.stat().st_mtime for i in ordered_images(out))
        if p.stat().st_mtime < newest:
            problems.append("review.json is older than the current slide images (slides were re-rendered after the review); review again")
        kit = [out / "review" / "contact-sheet.png", *sorted((out / "review").glob("slide-*.png"))]
        if any(not k.is_file() or k.stat().st_mtime < newest for k in kit[:1]) or any(k.stat().st_mtime < newest for k in kit[1:]):
            problems.append("the review kit (previews, contact sheet) is older than the slide images; run review-kit, then review again")
    except Exception as e:
        problems.append(f"could not check review freshness: {e}")
    if rv.get("reviewer") not in ("independent-subagent", "same-session", "human"):
        problems.append("reviewer must be independent-subagent, same-session or human")
    missing = sorted(set(range(1, n_slides + 1)) - set(rv.get("inspected", [])))
    if missing:
        problems.append(f"slides not inspected: {missing}")
    if not rv.get("contact_sheet_inspected"):
        problems.append("contact sheet not inspected (deck-level rhythm unchecked)")
    for c in MODEL_CATEGORIES:
        e = rv.get("categories", {}).get(c)
        if not e:
            problems.append(f"category {c} not scored")
            continue
        s = e.get("score")
        if s != "n/a" and not (isinstance(s, (int, float)) and 0 <= s <= 10):
            problems.append(f"category {c}: score must be 0-10 or 'n/a', got {s!r}")
        if s != "n/a" and not str(e.get("rationale") or "").strip():
            problems.append(f"category {c}: score has no rationale")
    for f in rv.get("findings", []):
        if f.get("severity") not in SEVERITIES or f.get("category") not in MODEL_CATEGORIES or not f.get("message"):
            problems.append(f"malformed review finding (technical integrity comes from automated checks only): {f}")
        s = f.get("slide")
        if s is not None and not (isinstance(s, int) and 1 <= s <= n_slides):
            problems.append(f"review finding names slide {s!r}, outside 1..{n_slides}")
    notes = rv.get("slide_notes") or {}
    if not isinstance(notes, dict) or not all(str(k).isdigit() for k in notes):
        problems.append("slide_notes keys must be slide numbers")
    return rv, problems


def review_findings(review: dict | None, problems: list[str]) -> list[dict]:
    """The reviewer's findings as validator findings (only from a complete, current review)."""
    if not review or problems:
        return []
    out = []
    for f in review.get("findings", []):
        if f.get("message"):
            g = finding(f.get("code") or "visual-review", f["severity"], f["category"], f["message"], f.get("slide"),
                        {"recommendation": f.get("recommendation", ""), "source": "visual review"})
            g["status"] = "open"
            out.append(g)
    return out
