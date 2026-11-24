"""Score caps from open findings and the release status rules."""
from __future__ import annotations

import pytest

from pcv.review import MODEL_CATEGORIES
from pcv.score import WEIGHTS, cap_for, report_md, score
from pcv.util import CATEGORIES, finding

STAGES_OK = {"rendered": True, "pptx": True, "pdf": True, "renderback_verified": True}


def F(sev: str, cat: str = "layout", slide: int | None = 1) -> dict:
    return {**finding("x", sev, cat, "m", slide), "status": "open"}


def review(score_value=9, **over) -> dict:
    cats = {c: {"score": score_value, "rationale": "looked at every slide", "slides": []} for c in MODEL_CATEGORIES}
    cats.update(over)
    return {"reviewer": "independent-subagent", "inspected": [1], "contact_sheet_inspected": True,
            "categories": cats, "findings": [], "slide_notes": {}}


@pytest.mark.parametrize("sevs, cap", [
    ([], 10.0),
    (["minor"], 9.75),
    (["major", "major", "minor", "minor", "minor"], 7.25),
    (["minor"] * 20, 8.0),            # minors cost at most 2 points
    (["info"] * 5, 10.0),             # info never caps
    (["critical"], 4.0),
    (["critical", "critical"], 3.0),
    (["critical"] + ["major"] * 7, 3.0),
    (["critical"] * 9, 0.0),          # never negative
    (["major"] * 12, 0.0),
])
def test_cap_for(sevs, cap):
    assert cap_for([F(s) for s in sevs]) == pytest.approx(cap)


def test_weights_cover_every_category_and_sum_to_100():
    assert set(WEIGHTS) == set(CATEGORIES)
    assert sum(WEIGHTS.values()) == 100


def test_production_ready_with_clean_findings_and_full_review():
    r = score([], review(10), [], STAGES_OK)
    assert r["status"] == "PRODUCTION-READY" and r["overall"] == 100.0


def test_any_open_critical_means_not_ready_even_with_perfect_review():
    r = score([F("critical")], review(10), [], STAGES_OK)
    assert r["status"] == "NOT READY"
    assert r["categories"]["layout"]["score"] == 4.0
    assert "capped from 10" in r["categories"]["layout"]["basis"]


def test_fixed_findings_do_not_count():
    f = F("critical")
    f["status"] = "fixed"
    assert score([f], review(10), [], STAGES_OK)["status"] == "PRODUCTION-READY"


def test_major_or_failed_renderback_gives_warnings():
    assert score([F("major")], review(10), [], STAGES_OK)["status"] == "READY WITH WARNINGS"
    stages = {**STAGES_OK, "renderback_verified": False}
    assert score([], review(10), [], stages)["status"] == "READY WITH WARNINGS"


def test_missing_review_or_stage_is_incomplete_and_unscored():
    r = score([], None, ["no review.json: the visual review has not been done"], STAGES_OK)
    assert r["status"] == "INCOMPLETE" and r["overall"] is None
    assert r["categories"]["technical"]["score"] == 10.0  # technical comes from automated checks only
    assert r["categories"]["layout"]["score"] is None
    r = score([], review(10), [], {**STAGES_OK, "pdf": False})
    assert r["status"] == "INCOMPLETE"


def test_review_with_problems_is_ignored():
    r = score([], review(10), ["slides not inspected: [2]"], STAGES_OK)
    assert r["status"] == "INCOMPLETE" and r["overall"] is None


def test_review_score_is_capped_by_category_findings_only():
    r = score([F("major", "typography"), F("major", "typography")], review(9), [], STAGES_OK)
    assert r["categories"]["typography"]["score"] == 8.0
    assert r["categories"]["layout"]["score"] == 9.0


def test_na_category_is_dropped_from_weighted_overall():
    r = score([], review(8, data_visualization={"score": "n/a", "rationale": "no charts"}), [], STAGES_OK)
    assert r["categories"]["data_visualization"]["score"] == "n/a"
    # all remaining model categories 8, technical 10 (weight 10 of the remaining 92)
    assert r["overall"] == pytest.approx(round(10 * (82 * 8 + 10 * 10) / 92, 1))


def test_report_md_states_status_and_lists_findings():
    findings = [F("critical"), F("minor", "typography", 2)]
    result = score(findings, None, ["no review.json"], STAGES_OK)
    md = report_md("Deck", result, findings, [], [], None, ["no review.json"], {"slides": 2})
    assert "**Status: NOT READY**" in md and "Overall score: not computed" in md
    assert "## Critical issues" in md and "**slide 2**" in md
