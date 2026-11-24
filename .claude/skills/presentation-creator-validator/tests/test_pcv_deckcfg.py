"""deck.json loading: defaults merge, validation, slide ids, paths."""
from __future__ import annotations

import copy
import json

import pytest

from pcv.deckcfg import DEFAULTS, Deck, _merge


def write_deck(tmp_path, cfg: dict):
    (tmp_path / "deck.json").write_text(json.dumps(cfg), encoding="utf-8")
    return tmp_path


def test_merge_is_deep_and_does_not_mutate_defaults():
    before = copy.deepcopy(DEFAULTS)
    m = _merge(DEFAULTS, {"render": {"scale": 3}, "rules": {"min_font_px": 24, "type_scale": [20, 28]},
                          "network": {"allow": ["example.org"]}})
    assert m["render"]["scale"] == 3 and m["render"]["width"] == 1920 and m["render"]["selector"] == "[data-pcv-slide]"
    assert m["rules"]["min_font_px"] == 24 and m["rules"]["safe_margin_px"] == 64
    assert m["network"]["allow"] == ["example.org"]  # lists replace, they do not merge
    m["rules"]["type_scale"].append(99)
    assert DEFAULTS == before


def test_load_from_dir_or_file_and_defaults(tmp_path):
    write_deck(tmp_path, {"title": "Results: Phase 2!", "slides": ["03-results.html", "intro.html", "s/2_methods.html"]})
    d = Deck.load(tmp_path)
    assert Deck.load(tmp_path / "deck.json").cfg == d.cfg
    assert d.size == (1920, 1080) and d.render["scale"] == 2 and d.rules["min_font_px"] == 20
    assert d.name == "results-phase-2"
    assert [d.slide_id(i) for i in (1, 2, 3)] == ["03-results", "02-intro", "2_methods"]
    assert d.slide_files()[2] == (tmp_path / "s" / "2_methods.html").resolve()
    assert d.build_dir(tmp_path / "out") == (tmp_path / "out").resolve() and (tmp_path / "out").is_dir()
    assert d.fixes_dir() == (tmp_path / "fixes").resolve()


def test_explicit_name_wins(tmp_path):
    write_deck(tmp_path, {"title": "Anything", "name": "my-deck", "slides": ["a.html"]})
    assert Deck.load(tmp_path).name == "my-deck"


def test_empty_slides_and_missing_file_raise(tmp_path):
    write_deck(tmp_path, {"title": "x"})
    with pytest.raises(ValueError):
        Deck.load(tmp_path)
    with pytest.raises(FileNotFoundError):
        Deck.load(tmp_path / "nowhere")


def test_notes_for(tmp_path):
    write_deck(tmp_path, {"slides": ["01-a.html", "02-b.html"]})
    (tmp_path / "01-a.notes.md").write_text("  Say the claim first.\n", encoding="utf-8")
    d = Deck.load(tmp_path)
    assert d.notes_for(1) == "Say the claim first." and d.notes_for(2) == ""
