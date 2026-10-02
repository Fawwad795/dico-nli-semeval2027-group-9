#!/usr/bin/env python3
"""Generate the README panels as SVG, light and dark, into assets/readme/.

Panels: hero and hero-narrow (a phrase pair swaps order while its label flips from
FORWARD_ENTAILMENT to BACKWARD_ENTAILMENT and a consistency check appears), relations (the
four labels with one example each, static), timeline (the three assignments, static).

All motion is CSS inside the SVG so GitHub renders it through <img>. Base positions live in
SVG transform attributes on wrapper groups and the keyframes animate an inner group, so a
keyframe can never wipe a base position. prefers-reduced-motion freezes the hero on the
forward frame. Fonts are the system stack because image SVGs cannot load web fonts on GitHub.

Run: python scripts/readme/build_assets.py [out_dir]   (default assets/readme/)
"""

import os
import sys

FONT = "-apple-system, 'Segoe UI', Inter, Roboto, Helvetica, Arial, sans-serif"

PALETTES = {
    "light": dict(bg="#ffffff", surface="#f6f8fa", border="#d0d7de", text="#1f2328",
                  muted="#656d76", line="#8c959f", accent="#0969da", accent_soft="#ddf4ff",
                  fwd="#0969da", bwd="#8250df", equiv="#1a7f37", neg="#cf222e"),
    "dark": dict(bg="#0b1220", surface="#111a2e", border="#2a3650", text="#e6edf3",
                 muted="#8b98a9", line="#3d4a63", accent="#58a6ff", accent_soft="#16263f",
                 fwd="#58a6ff", bwd="#a371f7", equiv="#3fb950", neg="#f85149"),
}

REDUCED = "@media (prefers-reduced-motion: reduce) { .anim { animation: none !important; } }"

ARIA_HERO = ("DiCo-NLI, SemEval-2027 Task 2: directional-consistent fine-grained natural language "
             "inference. A phrase pair labelled FORWARD_ENTAILMENT swaps order and is labelled "
             "BACKWARD_ENTAILMENT, consistent when reversed.")

PAIR_A = "a red sports car"
PAIR_B = "a car"


def card(w, h, p):
    return (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" '
            f'fill="{p["surface"]}" stroke="{p["border"]}"/>')


def text(x, y, s, p, size=14, weight=400, fill=None, anchor="start", extra=""):
    fill = fill or p["text"]
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>')


def arrow_marker(mid, color):
    return (f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{color}"/></marker>')


# ------------------------------------------------------------------------------ hero
def hero_css(dx):
    return f"""
    .pa   {{ animation: swap-a 12s ease-in-out infinite; }}
    .pb   {{ animation: swap-b 12s ease-in-out infinite; }}
    .fwd  {{ animation: show-fwd 12s steps(1, end) infinite; }}
    .bwd  {{ animation: show-bwd 12s steps(1, end) infinite; }}
    .ok   {{ animation: show-ok 12s ease-in-out infinite; }}
    @keyframes swap-a {{ 0%, 36% {{ transform: translate(0,0); }} 41% {{ transform: translate({dx / 2}px,46px); }} 46%, 88% {{ transform: translate({dx}px,0); }} 93% {{ transform: translate({dx / 2}px,46px); }} 98%, 100% {{ transform: translate(0,0); }} }}
    @keyframes swap-b {{ 0%, 36% {{ transform: translate(0,0); }} 46%, 88% {{ transform: translate({-dx}px,0); }} 98%, 100% {{ transform: translate(0,0); }} }}
    @keyframes show-fwd {{ 0% {{ opacity: 1; }} 36% {{ opacity: 0; }} 98% {{ opacity: 1; }} 100% {{ opacity: 1; }} }}
    @keyframes show-bwd {{ 0% {{ opacity: 0; }} 46% {{ opacity: 1; }} 88% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
    @keyframes show-ok  {{ 0%, 54% {{ opacity: 0; transform: translateY(6px); }} 60% {{ opacity: 1; transform: translateY(0); }} 84% {{ opacity: 1; transform: translateY(0); }} 88%, 100% {{ opacity: 0; transform: translateY(0); }} }}
    {REDUCED}
    """


def phrase_chip(p, cls, label, x, y, w):
    return (
        f'<g transform="translate({x},{y})"><g class="{cls} anim" style="transform:translate(0,0)">'
        f'<rect width="{w}" height="40" rx="8" fill="{p["bg"]}" stroke="{p["border"]}"/>'
        f'{text(w / 2, 25, label, p, size=14, weight=500, anchor="middle")}'
        f'</g></g>'
    )


def label_chip(p, cls, label, color, cx, y, w, base_opacity):
    return (
        f'<g transform="translate({cx - w / 2},{y})"><g class="{cls} anim" style="opacity:{base_opacity}">'
        f'<rect width="{w}" height="26" rx="13" fill="{p["bg"]}" stroke="{color}"/>'
        f'{text(w / 2, 17.5, label, p, size=12, weight=600, fill=color, anchor="middle")}'
        f'</g></g>'
    )


def ok_chip(p, cx, y, w):
    color = p["equiv"]
    return (
        f'<g transform="translate({cx - w / 2},{y})"><g class="ok anim" style="opacity:0">'
        f'<rect width="{w}" height="26" rx="13" fill="{p["bg"]}" stroke="{color}"/>'
        f'<circle cx="16" cy="13" r="7" fill="{color}"/>'
        f'<path d="M12.5 13.2l2.3 2.3 4.4-4.6" fill="none" stroke="{p["bg"]}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
        f'{text(30, 17.5, "consistent when reversed", p, size=12, weight=600, fill=color)}'
        f'</g></g>'
    )


def hero_stage(p, ax, bx, chip_w, chip_y, arrow_y, label_y, ok_y, pos_y):
    """Two phrase chips, a forward and a backward arrow, the two labels, the check."""
    a_cx, b_cx = ax + chip_w / 2, bx + chip_w / 2
    gap_l, gap_r = ax + chip_w + 10, bx - 10
    mid = (gap_l + gap_r) / 2
    return "\n".join([
        f'<defs>{arrow_marker("m-fwd", p["fwd"])}{arrow_marker("m-bwd", p["bwd"])}</defs>',
        text(a_cx, pos_y, "premise", p, size=12, fill=p["muted"], anchor="middle"),
        text(b_cx, pos_y, "hypothesis", p, size=12, fill=p["muted"], anchor="middle"),
        phrase_chip(p, "pa", PAIR_A, ax, chip_y, chip_w),
        phrase_chip(p, "pb", PAIR_B, bx, chip_y, chip_w),
        f'<line class="fwd anim" x1="{gap_l}" y1="{arrow_y}" x2="{gap_r}" y2="{arrow_y}" stroke="{p["fwd"]}" stroke-width="2.5" marker-end="url(#m-fwd)" style="opacity:1"/>',
        f'<line class="bwd anim" x1="{gap_r}" y1="{arrow_y}" x2="{gap_l}" y2="{arrow_y}" stroke="{p["bwd"]}" stroke-width="2.5" marker-end="url(#m-bwd)" style="opacity:0"/>',
        label_chip(p, "fwd", "FORWARD_ENTAILMENT", p["fwd"], mid, label_y, 176, 1),
        label_chip(p, "bwd", "BACKWARD_ENTAILMENT", p["bwd"], mid, label_y, 184, 0),
        ok_chip(p, mid, ok_y, 200),
    ])


def hero(p):
    w, h = 1200, 260
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{ARIA_HERO}">
<style>{hero_css(dx=240)}</style>
{card(w, h, p)}
{text(48, 92, "DiCo-NLI · SemEval-2027 Task 2", p, size=34, weight=600)}
{text(48, 130, "Directional-consistent fine-grained natural language inference.", p, size=17, fill=p["muted"])}
{text(48, 154, "Label how two phrases relate, and give a compatible answer when the pair is flipped.", p, size=16, fill=p["muted"])}
{text(48, 212, "Large Language Models course · semester 7 · group 9", p, size=13, fill=p["muted"])}
<line x1="740" y1="40" x2="740" y2="220" stroke="{p["border"]}"/>
{hero_stage(p, ax=770, bx=1010, chip_w=160, chip_y=80, arrow_y=100, label_y=140, ok_y=180, pos_y=66)}
</svg>
"""


def hero_narrow(p):
    """Phone-width variant: text stacked above the animation stage."""
    w, h = 600, 400
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{ARIA_HERO}">
<style>{hero_css(dx=350)}</style>
{card(w, h, p)}
{text(32, 60, "DiCo-NLI", p, size=30, weight=600)}
{text(32, 96, "SemEval-2027 Task 2", p, size=30, weight=600)}
{text(32, 132, "Directional-consistent fine-grained natural", p, size=15, fill=p["muted"])}
{text(32, 154, "language inference. Label how two phrases relate,", p, size=15, fill=p["muted"])}
{text(32, 176, "and give a compatible answer when the pair is flipped.", p, size=15, fill=p["muted"])}
{text(32, 208, "Large Language Models course · semester 7 · group 9", p, size=12, fill=p["muted"])}
<line x1="32" y1="226" x2="568" y2="226" stroke="{p["border"]}"/>
{hero_stage(p, ax=40, bx=390, chip_w=170, chip_y=262, arrow_y=282, label_y=318, ok_y=354, pos_y=250)}
</svg>
"""


# ------------------------------------------------------------------------- relations
RELATIONS = [
    ("EQUIVALENCE", "equiv", "↔", "a big house  ↔  a large house", "each phrase entails the other"),
    ("FORWARD_ENTAILMENT", "fwd", "→", "a red sports car  →  a car", "the first phrase entails the second"),
    ("BACKWARD_ENTAILMENT", "bwd", "←", "a car  ←  a red sports car", "the second phrase entails the first"),
    ("NEGATIVE_OTHER", "neg", "✕", "a red car  ✕  a blue car", "neither direction holds"),
]


def relations(p):
    w, h = 1200, 150
    out = [card(w, h, p)]
    cw, gap, y0, ch = 270, 20, 14, 122
    for i, (name, key, glyph, example, desc) in enumerate(RELATIONS):
        x = 32 + i * (cw + gap)
        color = p[key]
        out.append(f'<rect x="{x}" y="{y0}" width="{cw}" height="{ch}" rx="10" fill="{p["bg"]}" stroke="{p["border"]}"/>')
        out.append(f'<circle cx="{x + 30}" cy="{y0 + 30}" r="14" fill="{p["accent_soft"] if key == "fwd" else p["surface"]}" stroke="{color}"/>')
        out.append(text(x + 30, y0 + 35, glyph, p, size=15, weight=600, fill=color, anchor="middle"))
        out.append(text(x + 54, y0 + 35, name, p, size=13, weight=600, fill=color))
        out.append(text(x + 20, y0 + 74, example, p, size=14, weight=500))
        out.append(text(x + 20, y0 + 100, desc, p, size=12, fill=p["muted"]))
    body = "\n".join(out)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="The four DiCo-NLI labels: EQUIVALENCE, each phrase entails the other; FORWARD_ENTAILMENT, the first entails the second; BACKWARD_ENTAILMENT, the second entails the first; NEGATIVE_OTHER, neither direction holds">
{body}
</svg>
"""


# -------------------------------------------------------------------------- timeline
def timeline(p, current="Assignment 1"):
    w, h = 1200, 150
    nodes = [
        ("Assignment 1", "Problem, literature and baseline", "Sunday 4 October 2026", 230),
        ("Assignment 2", "Approach and experimental design", "Friday 13 November 2026", 600),
        ("Assignment 3", "Experiments, analysis and paper", "Friday 4 December 2026", 970),
    ]
    out = [card(w, h, p), f'<line x1="230" y1="80" x2="970" y2="80" stroke="{p["line"]}" stroke-width="1.5"/>']
    for code, name, when, x in nodes:
        is_current = code == current
        if is_current:
            out.append(f'<circle cx="{x}" cy="80" r="14" fill="{p["accent_soft"]}" stroke="{p["accent"]}"/>')
            out.append(f'<circle cx="{x}" cy="80" r="6" fill="{p["accent"]}"/>')
        else:
            out.append(f'<circle cx="{x}" cy="80" r="8" fill="{p["bg"]}" stroke="{p["line"]}" stroke-width="1.5"/>')
        out.append(text(x, 32, code, p, size=14, weight=600, anchor="middle",
                        fill=p["accent"] if is_current else p["text"]))
        out.append(text(x, 52, name, p, size=13, fill=p["text"], anchor="middle"))
        out.append(text(x, 110, when, p, size=12, fill=p["muted"], anchor="middle"))
        if is_current:
            out.append(text(x, 132, "in progress", p, size=11, weight=600, fill=p["accent"], anchor="middle"))
    body = "\n".join(out)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Assignments: Assignment 1, problem, literature and baseline, due Sunday 4 October 2026, in progress; Assignment 2, approach and experimental design, due Friday 13 November 2026; Assignment 3, experiments, analysis and paper, due Friday 4 December 2026">
{body}
</svg>
"""


PANELS = (("hero", hero), ("hero-narrow", hero_narrow), ("relations", relations), ("timeline", timeline))


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
