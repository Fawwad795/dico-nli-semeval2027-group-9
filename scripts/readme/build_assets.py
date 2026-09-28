#!/usr/bin/env python3
"""Generate the README panels as SVG, light and dark, into assets/readme/.

Panels: hero and hero-narrow (one slow document-through-gate animation), pipeline (one
packet traversing the intended architecture), gates (static timeline). All motion is CSS
inside the SVG so GitHub renders it through <img>; prefers-reduced-motion freezes every
panel on a composed static frame. Fonts are the system stack because image SVGs cannot
load web fonts on GitHub.

Run: python scripts/readme/build_assets.py   (writes assets/readme/*.svg)
"""

import os
import sys

FONT = "-apple-system, 'Segoe UI', Inter, Roboto, Helvetica, Arial, sans-serif"

PALETTES = {
    "light": dict(bg="#ffffff", surface="#f6f8fa", border="#d0d7de", text="#1f2328",
                  muted="#656d76", line="#8c959f", accent="#0969da", accent_soft="#ddf4ff",
                  allow="#1a7f37", warn="#9a6700", reject="#cf222e"),
    "dark": dict(bg="#0b1220", surface="#111a2e", border="#2a3650", text="#e6edf3",
                 muted="#8b98a9", line="#3d4a63", accent="#58a6ff", accent_soft="#16263f",
                 allow="#3fb950", warn="#d29922", reject="#f85149"),
}

REDUCED = "@media (prefers-reduced-motion: reduce) { .anim { animation: none !important; } }"


def card(w, h, p):
    return (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" '
            f'fill="{p["surface"]}" stroke="{p["border"]}"/>')


def text(x, y, s, p, size=14, weight=400, fill=None, anchor="start", extra=""):
    fill = fill or p["text"]
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>')


def doc_glyph(p, x, y):
    """Document that travels through the gate; base position is the static frame."""
    return (
        f'<g class="doc anim" style="transform: translate({x}px,{y}px)">'
        f'<rect width="34" height="44" rx="4" fill="{p["bg"]}" stroke="{p["line"]}"/>'
        f'<path d="M8 12h18M8 20h18M8 28h12" stroke="{p["line"]}" stroke-width="2" stroke-linecap="round"/>'
        f'</g>'
    )


def chip(p, cls, label, color, base_opacity, x, y):
    # Position lives in an SVG attribute on a wrapper group; the CSS animation on the
    # inner group only touches opacity and a small translateY, so it can never wipe the
    # base position the way a keyframe would wipe an inline CSS transform.
    return (
        f'<g class="{cls} anim" style="opacity:{base_opacity}">'
        f'<g transform="translate({x},{y})">'
        f'<g class="chip anim">'
        f'<rect width="82" height="24" rx="12" fill="{p["bg"]}" stroke="{color}"/>'
        f'<circle cx="14" cy="12" r="4" fill="{color}"/>'
        f'{text(26, 16, label, p, size=12, weight=600, fill=color)}'
        f'</g></g></g>'
    )


def hero_css(p, start, gate, exit_, y, scan_len):
    return f"""
    .doc {{ animation: travel 10s cubic-bezier(.45,.05,.55,.95) infinite; }}
    .scan {{ animation: scan 10s linear infinite; }}
    .chip {{ animation: reveal 10s ease-in-out infinite; }}
    .slot-a {{ animation: slot-a 30s steps(1, end) infinite; }}
    .slot-b {{ animation: slot-b 30s steps(1, end) infinite; }}
    .slot-c {{ animation: slot-c 30s steps(1, end) infinite; }}
    @keyframes travel {{
      0%   {{ transform: translate({start}px,{y}px); opacity: 0; }}
      6%   {{ opacity: 1; }}
      38%  {{ transform: translate({gate}px,{y}px); }}
      62%  {{ transform: translate({gate}px,{y}px); }}
      88%  {{ transform: translate({exit_}px,{y}px); opacity: 1; }}
      94%  {{ opacity: 0; }}
      100% {{ transform: translate({start}px,{y}px); opacity: 0; }}
    }}
    @keyframes scan {{
      0%, 38%  {{ transform: translateY(0); opacity: 0; }}
      42%      {{ opacity: .9; }}
      58%      {{ transform: translateY({scan_len}px); opacity: .9; }}
      62%,100% {{ transform: translateY({scan_len}px); opacity: 0; }}
    }}
    @keyframes reveal {{
      0%, 64% {{ opacity: 0; transform: translateY(6px); }}
      70%     {{ opacity: 1; transform: translateY(0); }}
      90%     {{ opacity: 1; }}
      96%,100% {{ opacity: 0; }}
    }}
    @keyframes slot-a {{ 0% {{ opacity: 1; }} 33.34% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
    @keyframes slot-b {{ 0% {{ opacity: 0; }} 33.34% {{ opacity: 1; }} 66.67% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
    @keyframes slot-c {{ 0% {{ opacity: 0; }} 66.67% {{ opacity: 1; }} 100% {{ opacity: 1; }} }}
    {REDUCED}
    """


def hero_stage(p, gate_x, gate_y, gate_h, start, exit_, doc_y, chip_y, label_y):
    """Gate, scan line, labels, document, and the three verdict chips."""
    gate_cx = gate_x + 28
    return "\n".join([
        f'<rect x="{gate_x}" y="{gate_y}" width="56" height="{gate_h}" rx="8" fill="{p["bg"]}" stroke="{p["border"]}"/>',
        f'<rect class="scan anim" x="{gate_x + 6}" y="{gate_y + 6}" width="44" height="2" fill="{p["accent"]}" style="opacity:.35"/>',
        text(gate_cx, label_y, "security layer", p, size=12, fill=p["muted"], anchor="middle"),
        text(start + 17, label_y, "retrieved · remembered", p, size=12, fill=p["muted"], anchor="middle"),
        text(exit_ + 17, label_y, "verdict", p, size=12, fill=p["muted"], anchor="middle"),
        doc_glyph(p, exit_, doc_y),
        chip(p, "slot-a", "allow", p["allow"], 1, exit_ - 22, chip_y),
        chip(p, "slot-b", "flag", p["warn"], 0, exit_ - 22, chip_y),
        chip(p, "slot-c", "quarantine", p["warn"], 0, exit_ - 22, chip_y),
    ])


ARIA_HERO = "Agentic RAG Poisoning Defense: a model-agnostic security layer for agentic RAG pipelines"


# ----------------------------------------------------------------------------- hero
def hero(p):
    w, h = 1200, 260
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{ARIA_HERO}">
<style>{hero_css(p, start=800, gate=951, exit_=1096, y=108, scan_len=104)}</style>
{card(w, h, p)}
{text(48, 96, "Agentic RAG Poisoning Defense", p, size=34, weight=600)}
{text(48, 134, "A model-agnostic security layer for agentic RAG pipelines. It screens retrieved", p, size=17, fill=p["muted"])}
{text(48, 158, "documents and agent memory for poisoning, then explains and mitigates what it finds.", p, size=17, fill=p["muted"])}
{text(48, 214, "Final Year Design Project · NUST SEECS · Faculty of Computing", p, size=13, fill=p["muted"])}
<line x1="740" y1="40" x2="740" y2="220" stroke="{p["border"]}"/>
{hero_stage(p, gate_x=940, gate_y=70, gate_h=120, start=800, exit_=1096, doc_y=108, chip_y=158, label_y=212)}
</svg>
"""


def hero_narrow(p):
    """Phone-width variant: text stacked above the animation stage."""
    w, h = 600, 380
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{ARIA_HERO}">
<style>{hero_css(p, start=120, gate=283, exit_=430, y=258, scan_len=72)}</style>
{card(w, h, p)}
{text(32, 62, "Agentic RAG", p, size=30, weight=600)}
{text(32, 98, "Poisoning Defense", p, size=30, weight=600)}
{text(32, 134, "A model-agnostic security layer for agentic RAG pipelines.", p, size=15, fill=p["muted"])}
{text(32, 156, "It screens retrieved documents and agent memory for", p, size=15, fill=p["muted"])}
{text(32, 178, "poisoning, then explains and mitigates what it finds.", p, size=15, fill=p["muted"])}
{text(32, 210, "Final Year Design Project · NUST SEECS · Faculty of Computing", p, size=12, fill=p["muted"])}
<line x1="32" y1="226" x2="568" y2="226" stroke="{p["border"]}"/>
{hero_stage(p, gate_x=272, gate_y=236, gate_h=88, start=120, exit_=430, doc_y=258, chip_y=308, label_y=356)}
</svg>
"""


# ------------------------------------------------------------------------- pipeline
def pipeline(p):
    w, h = 1200, 420
    rows = ["content-risk detector", "inconsistency detector", "source / provenance analyzer",
            "memory-write validator", "retrieval-time validator"]
    css = f"""
    .packet {{ opacity: 0; animation: flow 12s cubic-bezier(.45,.05,.55,.95) infinite; }}
    .row {{ animation: rowpulse 12s ease-in-out infinite; }}
    @keyframes flow {{
      0%   {{ transform: translate(210px,148px); opacity: 0; fill: {p["accent"]}; }}
      4%   {{ opacity: 1; }}
      14%  {{ transform: translate(270px,200px); }}
      22%  {{ transform: translate(460px,200px); }}
      30%  {{ transform: translate(536px,200px); }}
      56%  {{ transform: translate(804px,200px); fill: {p["accent"]}; }}
      62%  {{ transform: translate(870px,200px); }}
      66%  {{ fill: {p["allow"]}; }}
      78%  {{ transform: translate(1070px,200px); }}
      86%  {{ transform: translate(1160px,200px); opacity: 1; }}
      90%  {{ opacity: 0; }}
      100% {{ transform: translate(210px,148px); opacity: 0; fill: {p["accent"]}; }}
    }}
    @keyframes rowpulse {{
      0%, 30%  {{ stroke: {p["border"]}; fill: {p["bg"]}; }}
      33%      {{ stroke: {p["accent"]}; fill: {p["accent_soft"]}; }}
      38%, 100% {{ stroke: {p["border"]}; fill: {p["bg"]}; }}
    }}
    {REDUCED}
    """
    marker = (f'<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
              f'<path d="M0 0L10 5L0 10z" fill="{p["line"]}"/></marker>')

    def box(x, y, bw, bh, lines, size=15, weight=500):
        out = [f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{p["bg"]}" stroke="{p["border"]}"/>']
        cy = y + bh / 2 - (len(lines) - 1) * (size * 0.65)
        for i, ln in enumerate(lines):
            out.append(text(x + bw / 2, cy + i * size * 1.3 + size * 0.35, ln, p, size=size, weight=weight, anchor="middle"))
        return "".join(out)

    row_svg = []
    for i, label in enumerate(rows):
        y = 100 + i * 48
        row_svg.append(
            f'<rect class="row anim" x="536" y="{y}" width="268" height="40" rx="6" fill="{p["bg"]}" stroke="{p["border"]}" style="animation-delay:{i * 0.72:.2f}s"/>'
            f'{text(670, y + 25, label, p, size=13, anchor="middle")}'
        )
    decisions = [("allow", p["allow"]), ("flag", p["warn"]), ("quarantine", p["warn"]),
                 ("rewrite", p["accent"]), ("reject", p["reject"])]
    dec_svg = [f'<rect x="870" y="115" width="150" height="170" rx="8" fill="{p["bg"]}" stroke="{p["border"]}"/>',
               text(945, 140, "Decision", p, size=14, weight=600, anchor="middle")]
    for i, (label, color) in enumerate(decisions):
        y = 164 + i * 24
        dec_svg.append(f'<circle cx="896" cy="{y - 4}" r="4" fill="{color}"/>')
        dec_svg.append(text(908, y, label, p, size=13))

    arrows = [
        f'<path d="M210 148 H240 Q250 148 250 158 V190 Q250 200 260 200 H266" fill="none" stroke="{p["line"]}" stroke-width="1.5" marker-end="url(#arrow)"/>',
        f'<path d="M210 248 H240 Q250 248 250 238 V210 Q250 200 260 200 H266" fill="none" stroke="{p["line"]}" stroke-width="1.5"/>',
        f'<line x1="460" y1="200" x2="516" y2="200" stroke="{p["line"]}" stroke-width="1.5" marker-end="url(#arrow)"/>',
        f'<line x1="820" y1="200" x2="866" y2="200" stroke="{p["line"]}" stroke-width="1.5" marker-end="url(#arrow)"/>',
        f'<line x1="1020" y1="200" x2="1066" y2="200" stroke="{p["line"]}" stroke-width="1.5" marker-end="url(#arrow)"/>',
    ]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Intended architecture: corpus and memory pass through provenance and normalization, five detectors, and a decision before reaching the agentic RAG pipeline">
<style>{css}</style>
<defs>{marker}</defs>
{card(w, h, p)}
{text(32, 40, "INTENDED ARCHITECTURE", p, size=12, weight=600, fill=p["muted"], extra='letter-spacing="1.5"')}
{text(1168, 40, "nothing implemented yet", p, size=12, fill=p["muted"], anchor="end")}
{box(40, 120, 170, 56, ["Retrieval corpus"])}
{box(40, 220, 170, 56, ["Agent memory"])}
{box(270, 162, 190, 76, ["Provenance and", "normalization"])}
{text(365, 262, "origin class · metadata · canonical text", p, size=11, fill=p["muted"], anchor="middle")}
<rect x="520" y="50" width="300" height="300" rx="10" fill="{p["surface"]}" stroke="{p["border"]}"/>
{text(670, 80, "Security monitoring layer", p, size=14, weight=600, anchor="middle")}
{"".join(row_svg)}
{"".join(dec_svg)}
{box(1070, 162, 100, 76, ["Agentic RAG", "pipeline"])}
{"".join(arrows)}
<circle class="packet anim" r="7" fill="{p["accent"]}" style="transform: translate(210px,148px)"/>
{text(32, 396, "Content carries its origin class from entry to output, and every decision ships with an explanation.", p, size=12, fill=p["muted"])}
</svg>
"""


# ----------------------------------------------------------------------------- gates
def gates(p, current="G1"):
    w, h = 1200, 140
    nodes = [
        ("G1", "Proposal Defense", "20% · week 3 to 4, semester 7", 170),
        ("G2", "MVS + Documentation", "30% · date not yet confirmed", 470),
        ("G3", "Industrial Evaluation", "10% · week 12 to 13, semester 8", 770),
        ("G4", "Complete Project Defense", "40% · week 16, semester 8", 1070),
    ]
    out = [card(w, h, p), f'<line x1="170" y1="66" x2="1070" y2="66" stroke="{p["line"]}" stroke-width="1.5"/>']
    for code, name, when, x in nodes:
        is_current = code == current
        if is_current:
            out.append(f'<circle cx="{x}" cy="66" r="14" fill="{p["accent_soft"]}" stroke="{p["accent"]}"/>')
            out.append(f'<circle cx="{x}" cy="66" r="6" fill="{p["accent"]}"/>')
        else:
            out.append(f'<circle cx="{x}" cy="66" r="8" fill="{p["bg"]}" stroke="{p["line"]}" stroke-width="1.5"/>')
        out.append(text(x, 38, f"{code} · {name}", p, size=14, weight=600, anchor="middle",
                        fill=p["accent"] if is_current else p["text"]))
        out.append(text(x, 96, when, p, size=12, fill=p["muted"], anchor="middle"))
        if is_current:
            out.append(text(x, 118, "current gate", p, size=11, weight=600, fill=p["accent"], anchor="middle"))
    body = "\n".join(out)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="FYDP gates: G1 Proposal Defense 20 percent, G2 MVS and Documentation 30 percent, G3 Industrial Evaluation 10 percent, G4 Complete Project Defense 40 percent; current gate G1">
{body}
</svg>
"""


PANELS = (("hero", hero), ("hero-narrow", hero_narrow), ("pipeline", pipeline), ("gates", gates))


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "assets/readme"
    os.makedirs(out_dir, exist_ok=True)
    for mode, p in PALETTES.items():
        for name, fn in PANELS:
            path = os.path.join(out_dir, f"{name}-{mode}.svg")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(fn(p))
            print("wrote", path)


if __name__ == "__main__":
    main()
