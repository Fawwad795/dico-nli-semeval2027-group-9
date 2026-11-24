"""Number extraction, the supported() rounding rule, citation markers, spelling and doubled words."""
from __future__ import annotations

from decimal import Decimal

import pytest

from pcv.checks_content import CITE, NUM, check_content, source_numbers, supported, to_decimal
from pcv.deckcfg import DEFAULTS, _merge


def nums(s: str) -> list[str]:
    return [m.group(0) for m in NUM.finditer(s)]


def ok(token: str, sources: list[str]) -> bool:
    x, places, _ = to_decimal(token)
    return supported(x, places, source_numbers(sources))


# ---------- extraction ----------

def test_extracts_percentages_thousands_and_decimals():
    assert nums("Accuracy 81.4% on 1,250 pairs and 12,500.75 tokens") == ["81.4%", "1,250", "12,500.75"]


def test_ignores_numbers_glued_to_words_hyphens_and_dates():
    assert nums("model v2, a 3-way split, run on 2026-11-24, file a/b/7") == []


def test_unicode_minus_and_signs():
    assert nums("delta −3.5 and +2.0") == ["−3.5", "+2.0"]
    assert to_decimal("−3.5") == (Decimal("-3.5"), 1, False)
    assert to_decimal("+2.0") == (Decimal("2.0"), 1, False)


def test_to_decimal_places_and_percent_flag():
    assert to_decimal("1,250") == (Decimal("1250"), 0, False)
    assert to_decimal("81.40%") == (Decimal("81.40"), 2, True)
    assert to_decimal("12,500.75") == (Decimal("12500.75"), 2, False)


# ---------- supported(): rounding to the slide's own precision ----------

@pytest.mark.parametrize("token", ["0.8137", "0.814", "0.81", "81.37%", "81.4%", "81%"])
def test_ratio_in_source_supports_rounded_slide_values(token):
    assert ok(token, ["dev accuracy 0.8137"])


@pytest.mark.parametrize("token", ["81.3%", "0.82", "82%", "81.5"])
def test_wrongly_rounded_or_different_values_are_not_supported(token):
    assert not ok(token, ["dev accuracy 0.8137"])


def test_percentage_in_source_supports_ratio_on_slide():
    assert ok("0.814", ["accuracy 81.4%"])
    assert ok("81.4", ["accuracy 81.4%"])


def test_thousands_separators_either_side():
    assert ok("12,500", ["12500 pairs"])
    assert ok("12500", ["12,500 pairs"])
    assert not ok("12,600", ["12,500 pairs"])


def test_exact_half_accepts_half_up_and_half_even():
    # 0.8125 -> 81.25 %: written as 81.3 % by the usual half-up convention and as 81.2 % by
    # Python's formatting of an exact tie (half-even). Both are faithful roundings of the source.
    assert ok("81.3%", ["0.8125"])
    assert ok("81.2%", ["0.8125"])
    assert not ok("81.4%", ["0.8125"])
    assert ok("2.5", ["2.45"]) and ok("2.4", ["2.45"])


def test_sign_is_not_compared():
    # Documented rule: a slide may state a drop as a positive magnitude ("fell 3.2 points").
    assert ok("3.2", ["delta -3.2"])
    assert ok("-3.2", ["delta 3.2"])


# ---------- check_content on synthetic DOMs ----------

def _text(s: str, **flags) -> dict:
    fl = {"nocheck": False, "source": False, "spelling": False, "title": False}
    fl.update(flags)
    return {"text": s, "path": "p:nth-child(1)", "flags": fl}


def _cfg(**over) -> dict:
    return _merge(DEFAULTS, {"slides": ["a.html"], **over})


@pytest.fixture
def src(tmp_path):
    p = tmp_path / "results.csv"
    p.write_text("metric,value\ndev_accuracy,0.814\nphrase_pairs,1250\n", encoding="utf-8")
    return [p]


def codes(F, slide=None):
    return [f["code"] for f in F if slide is None or f["slide"] == slide]


def test_unsupported_number_flagged_with_policy_severity(src):
    doms = {1: {"texts": [_text("Recall reached 97.3% on the test split.")], "refs": []}}
    F = check_content(doms, _cfg(rules={"spelling": False}), src)
    hits = [f for f in F if f["code"] == "unsupported-number"]
    assert len(hits) == 1 and hits[0]["severity"] == "major" and hits[0]["evidence"]["number"] == "97.3%"


def test_supported_numbers_small_integers_source_and_nocheck_text_pass(src):
    doms = {1: {"texts": [
        _text("Accuracy reached 81.4% on 1,250 phrase pairs in 3 steps."),
        _text("Source: run 7731", source=True),
        _text("Build 4471", nocheck=True),
    ], "refs": []}}
    assert codes(check_content(doms, _cfg(rules={"spelling": False}), src)) == []


def test_small_percentages_are_checked(src):
    doms = {1: {"texts": [_text("Only 5% improved.")], "refs": []}}
    assert codes(check_content(doms, _cfg(rules={"spelling": False}), src)) == ["unsupported-number"]


def test_number_policy_off_and_minor(src):
    doms = {1: {"texts": [_text("Recall reached 97.3%.")], "refs": []}}
    assert codes(check_content(doms, _cfg(rules={"spelling": False, "number_policy": "off"}), src)) == []
    F = check_content(doms, _cfg(rules={"spelling": False, "number_policy": "minor"}), src)
    assert [f["severity"] for f in F] == ["minor"]


def test_number_without_source_note_when_required(src):
    doms = {1: {"texts": [_text("Accuracy 81.4%.")], "refs": []}}
    F = check_content(doms, _cfg(rules={"spelling": False, "require_source_for_numbers": True}), src)
    assert codes(F) == ["number-without-source"]
    doms[1]["texts"].append(_text("Source: results.csv", source=True))
    assert codes(check_content(doms, _cfg(rules={"spelling": False, "require_source_for_numbers": True}), src)) == []


def test_missing_source_file_is_reported(tmp_path):
    doms = {1: {"texts": [], "refs": []}}
    F = check_content(doms, _cfg(rules={"spelling": False}), [tmp_path / "nope.csv"])
    assert codes(F) == ["source-unreadable"]


# ---------- citations ----------

def test_citation_marker_regex():
    assert [m.group(1) for m in CITE.finditer("see [1], [1, 2] and [2–4] but not [a]")] == ["1", "1, 2", "2–4"]


def test_citation_markers_beyond_reference_count_are_missing(src):
    cfg = _cfg(rules={"spelling": False}, references={"a": "A.", "b": "B."})
    doms = {1: {"texts": [_text("Shown before [1, 2] and again [3].")], "refs": []}}
    F = check_content(doms, cfg, src)
    assert codes(F) == ["missing-reference"] and F[0]["evidence"]["marker"] == "[3]"


def test_data_ref_keys_must_exist(src):
    cfg = _cfg(rules={"spelling": False}, references={"smith2020": "A. Smith."})
    doms = {1: {"texts": [], "refs": ["smith2020", "nobody2099"]}}
    F = check_content(doms, cfg, src)
    assert codes(F) == ["missing-reference"] and F[0]["evidence"]["key"] == "nobody2099"


# ---------- spelling and doubled words ----------

def test_spelling_flags_misspelling_but_not_glossary_source_words_or_acronyms(src):
    cfg = _cfg(glossary=["DiCo"], rules={"number_policy": "off"})
    doms = {1: {"texts": [
        _text("The resluts were stable."),
        _text("Dico phrase_pairs dev_accuracy NLI SemEval"),  # glossary (case-insensitive), source words, acronym, CamelCase
        _text("Wrnog but deliberate", spelling=True),
    ], "refs": []}}
    F = check_content(doms, cfg, src)
    sp = [f for f in F if f["code"] == "spelling"]
    assert [f["evidence"]["word"] for f in sp] == ["resluts"]
    assert sp[0]["severity"] == "minor"


def test_doubled_word(src):
    doms = {1: {"texts": [_text("This is the the result, 10 10 times.")], "refs": []}}
    F = check_content(doms, _cfg(rules={"spelling": False, "number_policy": "off"}), src)
    assert codes(F) == ["doubled-word"]
