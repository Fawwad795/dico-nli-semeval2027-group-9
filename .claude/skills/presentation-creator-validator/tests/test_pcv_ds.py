"""Design-system support: tokens.css generation and the contrast audit's text/ground pairing."""
from __future__ import annotations

import json

import pytest

from pcv.ds import audit_ds, import_ds, tokens_css

TOKENS = {
    "name": "Test system",
    "color": {
        "themes": [{"id": "light"}, {"id": "dark"}],
        "tokens": [
            {"name": "paper", "value": {"light": "#ffffff", "dark": "#101010"}},
            {"name": "surface-1", "value": {"light": "#f4f4f4", "dark": "#1c1c1c"}},
            {"name": "ink", "value": {"light": "#111111", "dark": "#f0f0f0"}},
            {"name": "ink-3", "value": {"light": "#bbbbbb"}, "usage": "Captions on paper only."},
            {"name": "accent-text", "value": "#2a6df4", "usage": "Large text, 24px or more, on surface-1."},
            {"name": "rule", "value": "#cccccc", "usage": "Hairlines; never text."},
            {"name": "link", "value": "{accent-text}"},
        ],
    },
    "type": {
        "families": {"display": "'Fraunces', serif", "text": "'Inter', sans-serif"},
        "groups": [{"styles": [{"name": "h1", "fontSize": 56, "lineHeight": 1.1, "fontWeight": 700},
                               {"name": "body", "fontSize": "1.5rem"}]}],
    },
    "space": {"tokens": [{"name": "space-4", "value": 32}]},
}


def test_tokens_css_root_dark_theme_aliases_families_and_scales():
    css = tokens_css(TOKENS)
    root, dark = css.split('[data-theme="dark"]')
    assert "--paper: #ffffff;" in root and "--ink: #111111;" in root
    assert "--link: var(--accent-text);" in root          # {alias} -> var()
    assert "--font-display: 'Fraunces', serif;" in root
    assert "--type-h1-size: 56px;" in root and "--type-h1-line: 1.1;" in root and "--type-h1-weight: 700;" in root
    assert "--type-body-size: 1.5rem;" in root
    assert "--space-4: 32px;" in root                     # other token families, numbers -> px
    assert "--paper: #101010;" in dark and "--ink: #f0f0f0;" in dark
    assert "--ink-3: #bbbbbb;" in dark                    # missing theme value falls back to the first theme
    assert "--font-display" not in dark


def test_tokens_css_single_theme_default():
    css = tokens_css({"color": {"tokens": [{"name": "ink", "value": "#000000"}]}})
    assert ":root {" in css and "--ink: #000000;" in css and "data-theme" not in css


@pytest.fixture
def ds_dir(tmp_path):
    d = tmp_path / "ds"
    (d / "components").mkdir(parents=True)
    (d / "tokens.json").write_text(json.dumps(TOKENS), encoding="utf-8")
    (d / "components" / "bundle.css").write_text(
        "/* .ignored { font-size: 8px } */\n.caption { font-size: 12px; }\n.big { font: 700 40px/1.2 sans-serif; }\n",
        encoding="utf-8")
    return d


def test_audit_pairs_text_tokens_with_named_or_surface_grounds(ds_dir):
    a = audit_ds(ds_dir, min_font_px=22)
    pairs = {(p["text"], p["ground"], p["theme"]): p for p in a["pairs"]}
    # ink names no ground -> tested on every surface* token in every theme
    assert {k for k in pairs if k[0] == "ink"} == {("ink", "surface-1", "light"), ("ink", "surface-1", "dark")}
    # ink-3 names "paper" in its usage -> only paper; light grey on white fails 4.5:1
    p = pairs[("ink-3", "paper", "light")]
    assert not p["ok"] and p["required"] == 4.5 and p["ground_named_in_usage"]
    assert not any(k[0] == "ink-3" and k[1] != "paper" for k in pairs)
    # "24px or more" usage -> large-text threshold 3:1, against the named surface-1
    p = pairs[("accent-text", "surface-1", "light")]
    assert p["required"] == 3.0 and p["ok"]
    # "never text" tokens are skipped; non-text names are skipped
    assert not any(k[0] in ("rule", "paper", "link") for k in pairs)


def test_audit_findings(ds_dir):
    a = audit_ds(ds_dir, min_font_px=22)
    contrast = [f for f in a["findings"] if f["code"] == "ds-token-contrast"]
    # light fails; dark reuses the light value (#bbbbbb) on dark paper and passes
    assert [(f["evidence"]["text"], f["evidence"]["theme"]) for f in contrast] == [("ink-3", "light")]
    assert audit_ds(ds_dir)["pairs"] and any(p["theme"] == "dark" and p["text"] == "ink-3" and p["ok"]
                                             for p in a["pairs"])
    small = [f["evidence"] for f in a["findings"] if f["code"] == "ds-font-below-minimum"]
    assert small == [{"selector": ".caption", "px": 12.0}]                   # comments stripped, 40px passes


def test_import_ds_copies_files_and_writes_tokens_css(ds_dir, tmp_path):
    deck = tmp_path / "deck"
    dst = import_ds(ds_dir, deck)
    assert (dst / "tokens.json").is_file() and (dst / "components" / "bundle.css").is_file()
    assert (dst / "tokens.css").read_text(encoding="utf-8") == tokens_css(TOKENS)
