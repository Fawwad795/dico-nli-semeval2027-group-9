"""presentation-creator-validator command line.

Run from the repository root with the slides dependency group:
    uv run --group slides python .claude/skills/presentation-creator-validator/scripts/deck.py <command> ...
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pcv import ds, pipeline  # noqa: E402
from pcv.assemble import assemble_pptx, export_pdf  # noqa: E402
from pcv.deckcfg import Deck  # noqa: E402
from pcv.render import render  # noqa: E402
from pcv.review import make_kit  # noqa: E402
from pcv.util import SKILL_DIR  # noqa: E402


def _slides(s: str | None) -> list[int] | None:
    if not s:
        return None
    out: list[int] = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += range(int(a), int(b) + 1)
        else:
            out.append(int(part))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="deck.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="start a deck folder from the template")
    p.add_argument("dir")
    p.add_argument("--title", default="Untitled presentation")
    p.add_argument("--design-system", help="folder holding tokens.json (+ components/bundle.css/js) to import")

    p = sub.add_parser("ds-import", help="copy a design system into a deck and generate tokens.css")
    p.add_argument("src")
    p.add_argument("deck")

    p = sub.add_parser("inspect-pptx", help="VALIDATE a PPTX this skill did not build")
    p.add_argument("pptx")
    p.add_argument("--out", required=True)
    p.add_argument("--sources", nargs="*", default=[])
    p.add_argument("--glossary", nargs="*", default=[])
    p.add_argument("--min-font", type=float, default=20, help="minimum size in px on a 1920px-wide canvas")

    p = sub.add_parser("ds-audit", help="contrast and minimum-size audit of a design system")
    p.add_argument("src")
    p.add_argument("--out", required=True)
    p.add_argument("--min-font", type=float, default=22)

    for name, hlp in (("render", "render slides to images"), ("assemble", "build the PPTX"), ("pdf", "build the PDF"),
                      ("validate", "run every automated check"), ("fix", "apply safe fixes, re-render, re-validate"),
                      ("review-kit", "previews and contact sheet for the visual review"), ("report", "score and write the report"),
                      ("build", "render, fix, assemble, pdf, review kit, validate, report")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("deck")
        p.add_argument("--out", help="build folder (default: <deck>/build)")
        if name in ("render", "fix", "build"):
            p.add_argument("--headless", action="store_true", help="only where no display exists")
        if name == "render":
            p.add_argument("--slides", help="e.g. 1,3-5")
            p.add_argument("--scale", type=float, help="2 -> 3840x2160, 3 -> 5760x3240")
            p.add_argument("--format", choices=["png", "jpeg"])
        if name in ("validate", "build"):
            p.add_argument("--no-renderback", action="store_true")
        if name == "build":
            p.add_argument("--no-fix", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "new":
        dst = Path(a.dir)
        if dst.exists() and any(dst.iterdir()):
            ap.error(f"{dst} exists and is not empty")
        shutil.copytree(SKILL_DIR / "templates" / "deck", dst, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("build", "__pycache__"))
        cfg = (dst / "deck.json").read_text(encoding="utf-8").replace("Untitled presentation", a.title)
        (dst / "deck.json").write_text(cfg, encoding="utf-8")
        if a.design_system:
            print("design system ->", ds.import_ds(Path(a.design_system), dst))
        print("created", dst.resolve())
        return 0
    if a.cmd == "ds-import":
        print(ds.import_ds(Path(a.src), Path(a.deck)))
        return 0
    if a.cmd == "ds-audit":
        print(ds.write_audit(Path(a.src), Path(a.out), a.min_font))
        return 0
    if a.cmd == "inspect-pptx":
        from pcv.foreign import inspect_pptx
        r = inspect_pptx(Path(a.pptx), Path(a.out).resolve(), [Path(s).resolve() for s in a.sources], a.glossary, a.min_font)
        print(r["status"], r["overall"], "->", Path(a.out) / "validation" / "report.md")
        return 0

    deck = Deck.load(a.deck)
    out = deck.build_dir(a.out)
    if a.cmd == "render":
        man = render(deck, out, only=_slides(a.slides), scale=a.scale, fmt=a.format, headless=a.headless)
        for k in sorted(man["slides"], key=int):
            s = man["slides"][k]
            print(f"{k:>3} {s['image']} {s['size'][0]}x{s['size'][1]} {s['ms']} ms")
        for e in man["errors"]:
            print("ERROR", e)
        return 1 if man["errors"] else 0
    if a.cmd == "assemble":
        print(assemble_pptx(deck, out))
    elif a.cmd == "pdf":
        print(export_pdf(deck, out))
    elif a.cmd == "review-kit":
        print(make_kit(out))
    elif a.cmd == "validate":
        res = pipeline.validate(deck, out, renderback_on=not a.no_renderback)
        _summary(res["findings"])
    elif a.cmd == "fix":
        log = pipeline.fix_loop(deck, out, headless=a.headless)
        print(f"fixed {len(log['fixed'])}, refused {len(log['refused'])}; re-run assemble, pdf and validate")
    elif a.cmd == "report":
        r = pipeline.report(deck, out)
        print(r["status"], r["overall"], "->", out / "validation" / "report.md")
    elif a.cmd == "build":
        r = pipeline.build(deck, out, headless=a.headless, fix=not a.no_fix, renderback_on=not a.no_renderback)
        print(r["status"], r["overall"], "->", out / "validation" / "report.md")
    return 0


def _summary(findings: list[dict]) -> None:
    order = {"critical": 0, "major": 1, "minor": 2, "info": 3}
    for f in sorted(findings, key=lambda f: (order[f["severity"]], f["slide"] or 0)):
        where = f"slide {f['slide']}" if f["slide"] else "deck"
        print(f"{f['severity']:<8} {where:<9} {f['code']:<28} {f['message']}")
    print(f"{len(findings)} findings")


if __name__ == "__main__":
    sys.exit(main())
