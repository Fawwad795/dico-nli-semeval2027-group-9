"""Orchestration: validate, fix loop, build, report."""
from __future__ import annotations

from pathlib import Path

from .assemble import assemble_pptx, export_pdf
from .checks_content import check_content
from .checks_dom import check_deck, check_slide
from .checks_image import check_contrast, check_image
from .checks_output import check_pdf, check_pptx, renderback
from .deckcfg import Deck
from .fixes import plan_fixes, write_fixes
from .render import render
from .review import load_review, make_kit, review_findings
from .score import report_md, score
from .util import finding, read_json, sha256_file, write_json


def _key(f: dict) -> tuple:
    return f["code"], f["slide"], (f.get("evidence") or {}).get("path")


def _fresh_log() -> dict:
    return {"fixed": [], "refused": []}


def validate(deck: Deck, out: Path, outputs: bool = True, renderback_on: bool = True) -> dict:
    man = read_json(out / "render-manifest.json")
    n = len(deck.slide_files())
    W, H = deck.size
    expect = (round(W * man["scale"]), round(H * man["scale"]))
    F: list[dict] = [finding("render-error", "critical", "technical", e["error"], e["slide"]) for e in man.get("errors", [])]
    have = {int(k): v for k, v in man["slides"].items() if (out / v["image"]).is_file()}
    errored = {e["slide"] for e in man.get("errors", [])}
    for i in range(1, n + 1):
        if i not in have and i not in errored:
            F.append(finding("not-rendered", "critical", "technical", "Slide has no rendered image; run render.", i))
    # Images must reflect the current sources: a slide, its fix CSS or the deck's injected CSS edited
    # after the render means every check below would describe an old picture.
    files = deck.slide_files()
    for i, s in have.items():
        src = files[i - 1]
        if s.get("source") != src.relative_to(deck.dir).as_posix() or (src.is_file() and s.get("source_sha256") != sha256_file(src)):
            F.append(finding("stale-render", "critical", "technical",
                             "The slide source changed after this image was rendered; re-render before trusting any check.", i))
        img = out / s["image"]
        newer = [p for p in [deck.fixes_dir() / f"{src.stem}.css", *(deck.dir / c for c in deck.cfg["inject_css"])]
                 if p.is_file() and p.stat().st_mtime > img.stat().st_mtime]
        if newer:
            F.append(finding("stale-render", "critical", "technical",
                             f"{newer[0].name} changed after this image was rendered; re-render.", i))
    doms = {i: read_json(out / have[i]["dom"]) for i in have}
    imgs = {i: out / have[i]["image"] for i in have}
    for i in sorted(have):
        F += check_slide(doms[i], i, deck.rules, deck.size)
        F += check_image(imgs[i], i, expect)
        F += check_contrast(imgs[i], doms[i], i)
    F += check_deck(doms, deck.rules)
    F += check_content(doms, deck.cfg, deck.sources())
    complete = len(have) == n and not man.get("errors")
    stages = {"rendered": complete, "pptx": False, "pdf": False, "renderback_verified": None}
    rb_info: dict = {}
    if outputs and complete:
        ordered = [imgs[i] for i in range(1, n + 1)]
        pptx, pdf = out / f"{deck.name}.pptx", out / f"{deck.name}.pdf"
        F += check_pptx(pptx, ordered)
        F += check_pdf(pdf, ordered)
        stages["pptx"], stages["pdf"] = pptx.is_file(), pdf.is_file()
        if renderback_on and pptx.is_file():
            rbF, rb_info = renderback(pptx, ordered, out)
            F += rbF
            # None = not run (no PowerPoint here); False = ran and found mismatches; True = ran and matched.
            if rb_info.get("engine") == "PowerPoint":
                stages["renderback_verified"] = not any(
                    f["code"].startswith("renderback-") and f["severity"] != "info" for f in rbF)
    for f in F:
        f.setdefault("status", "open")
    res = {"findings": F, "stages": stages, "renderback": rb_info, "slides": n,
           "render": {k: man[k] for k in ("canvas", "scale", "format", "browser", "headless", "rendered")}}
    write_json(out / "validation" / "findings.json", res)
    return res


def fix_loop(deck: Deck, out: Path, rounds: int = 3, headless: bool = False) -> dict:
    log = _fresh_log()  # a log describes this loop only; old entries would claim fixes that no longer hold
    res = validate(deck, out, outputs=False)
    for _ in range(rounds):
        apply, refused = plan_fixes(deck, res["findings"])
        log["refused"] = [{k: f[k] for k in ("code", "slide", "message", "reason")} for f in refused]
        if not apply:
            break
        before = {_key(f): f for f in res["findings"] if f.get("fix")}
        slides = write_fixes(deck, apply)
        render(deck, out, only=slides, headless=headless)
        res = validate(deck, out, outputs=False)
        after = {_key(f) for f in res["findings"]}
        for k, f in before.items():
            if k not in after:
                log["fixed"].append({**{x: f[x] for x in ("code", "slide", "message", "category", "severity")}, "status": "fixed"})
    write_json(out / "validation" / "fix-log.json", log)
    return log


def build(deck: Deck, out: Path, headless: bool = False, fix: bool = True, renderback_on: bool = True) -> dict:
    man = render(deck, out, headless=headless)
    if fix and not man["errors"]:
        fix_loop(deck, out, headless=headless)
    else:
        write_json(out / "validation" / "fix-log.json", _fresh_log())
    man = read_json(out / "render-manifest.json")
    if not man["errors"]:
        assemble_pptx(deck, out)
        export_pdf(deck, out)
        make_kit(out)
    validate(deck, out, outputs=True, renderback_on=renderback_on)
    return report(deck, out)


def report(deck: Deck, out: Path) -> dict:
    res = read_json(out / "validation" / "findings.json")
    log_p = out / "validation" / "fix-log.json"
    log = read_json(log_p) if log_p.is_file() else _fresh_log()
    review, problems = load_review(out, res["slides"])
    findings = res["findings"] + review_findings(review, problems)
    # Findings must describe the current images; otherwise the report would score an older deck.
    man = read_json(out / "render-manifest.json")
    imgs = [out / s["image"] for s in man["slides"].values() if (out / s["image"]).is_file()]
    stages = dict(res["stages"])
    if imgs and (out / "validation" / "findings.json").stat().st_mtime < max(p.stat().st_mtime for p in imgs):
        findings.append({**finding("stale-validation", "critical", "technical",
                                   "findings.json is older than the slide images; run validate before report.", None),
                         "status": "open"})
    open_keys = {(f["code"], f["slide"]) for f in findings if f.get("status", "open") == "open"}
    fixed = [f for f in log["fixed"] if (f["code"], f["slide"]) not in open_keys]
    result = score(findings, review, problems, stages)
    rb = res.get("renderback") or {}
    meta = {
        "slides": res["slides"],
        "canvas": f"{res['render']['canvas'][0]}x{res['render']['canvas'][1]} CSS px at scale {res['render']['scale']} "
                  f"-> {round(res['render']['canvas'][0] * res['render']['scale'])}x{round(res['render']['canvas'][1] * res['render']['scale'])} {res['render']['format'].upper()}",
        "renderer": f"{res['render']['browser']} ({'headless' if res['render']['headless'] else 'headed, off-screen'})",
        "rendered": res["render"]["rendered"],
        "pptx and pdf checked": f"{stages['pptx']} / {stages['pdf']}",
        "PowerPoint render-back": ("verified, every slide matches" if stages["renderback_verified"]
                                   else "not verified" if stages["renderback_verified"] is None
                                   else "ran, mismatches found") + (f" (PowerPoint {rb.get('powerpoint')})" if rb.get("powerpoint") else ""),
    }
    md = report_md(deck.title, result, findings, fixed, log["refused"], None if problems else review, problems, meta)
    (out / "validation" / "report.md").write_text(md, encoding="utf-8")
    write_json(out / "validation" / "report.json", {**result, "meta": meta, "fixed": fixed, "refused": log["refused"],
                                                    "review_problems": problems})
    return result
