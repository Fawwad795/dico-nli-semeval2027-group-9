"""Scoring (rubric in references/scoring-rubric.md) and the Markdown validation report."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from .util import CATEGORIES

WEIGHTS = {
    "visual_design": 15, "typography": 12, "layout": 12, "hierarchy": 10, "content_accuracy": 15,
    "storytelling": 10, "data_visualization": 8, "consistency": 8, "technical": 10,
}
LABELS = {
    "visual_design": "Visual design and aesthetics", "typography": "Typography and readability",
    "layout": "Layout and composition", "hierarchy": "Information hierarchy", "content_accuracy": "Content accuracy",
    "storytelling": "Storytelling and narrative flow", "data_visualization": "Data visualization",
    "consistency": "Consistency across slides", "technical": "Technical integrity",
}


def cap_for(findings: list[dict]) -> float:
    """Ceiling that open deterministic findings put on a category score."""
    n = Counter(f["severity"] for f in findings)
    cap = 10.0 - 1.0 * n["major"] - min(2.0, 0.25 * n["minor"])
    if n["critical"]:
        cap = min(cap, 4.0 - (n["critical"] - 1))
    return max(0.0, cap)


def score(findings: list[dict], review: dict | None, review_problems: list[str], stages: dict) -> dict:
    open_f = [f for f in findings if f.get("status", "open") == "open"]
    by_cat = {c: [f for f in open_f if f["category"] == c] for c in CATEGORIES}
    cats = {}
    for c in CATEGORIES:
        cap = cap_for(by_cat[c])
        if c == "technical":
            cats[c] = {"score": round(cap, 1), "basis": "deterministic checks", "cap": cap}
            continue
        r = (review or {}).get("categories", {}).get(c) if review and not review_problems else None
        if r is None:
            cats[c] = {"score": None, "basis": "not assessed (visual review missing or incomplete)", "cap": cap}
        elif r["score"] == "n/a" and by_cat[c]:
            # "Not applicable" cannot erase open findings in the category; their cap stands as the score.
            cats[c] = {"score": round(cap, 1), "cap": cap,
                       "basis": f"reviewer marked n/a, but {len(by_cat[c])} open finding(s) exist; scored by their cap"}
        elif r["score"] == "n/a":
            cats[c] = {"score": "n/a", "basis": r.get("rationale") or "", "cap": cap}
        else:
            s = min(float(r["score"]), cap)
            basis = r.get("rationale", "")
            if s < float(r["score"]):
                basis += f" [capped from {r['score']} to {cap:.1f} by open findings]"
            cats[c] = {"score": round(s, 1), "basis": basis, "cap": cap}
    assessed = all(v["score"] is not None for v in cats.values())
    overall = None
    if assessed:
        num = sum(WEIGHTS[c] * v["score"] for c, v in cats.items() if v["score"] != "n/a")
        den = sum(WEIGHTS[c] for c, v in cats.items() if v["score"] != "n/a")
        overall = round(10 * num / den, 1) if den else None
    sev = Counter(f["severity"] for f in open_f)
    if sev["critical"]:
        status = "NOT READY"
    elif not assessed or not all(v for k, v in stages.items() if k != "renderback_verified"):
        status = "INCOMPLETE"
    elif sev["major"] or stages.get("renderback_verified") is not True:
        status = "READY WITH WARNINGS"
    else:
        status = "PRODUCTION-READY"
    return {"overall": overall, "categories": cats, "status": status, "counts": dict(sev)}


def _flist(fs: list[dict]) -> list[str]:
    out = []
    for f in sorted(fs, key=lambda f: (f["slide"] or 0, f["code"])):
        where = f"slide {f['slide']}" if f["slide"] else "deck"
        out.append(f"- **{where}** · `{f['code']}` · {f['message']}")
    return out or ["- none"]


def report_md(deck_title: str, result: dict, findings: list[dict], fixed: list[dict], refused: list[dict],
              review: dict | None, review_problems: list[str], meta: dict) -> str:
    open_f = [f for f in findings if f.get("status", "open") == "open"]
    L = [f"# Validation report: {deck_title}", "",
         f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by presentation-creator-validator.", "",
         f"**Status: {result['status']}**", ""]
    L.append(f"**Overall score: {result['overall']} / 100**" if result["overall"] is not None else
             "**Overall score: not computed.** The visual review is missing or incomplete, and the categories it judges cannot be scored from automated checks alone.")
    L += ["", "| Category | Weight | Score / 10 | Basis |", "|---|---:|---:|---|"]
    for c in CATEGORIES:
        v = result["categories"][c]
        s = "-" if v["score"] is None else v["score"]
        L.append(f"| {LABELS[c]} | {WEIGHTS[c]} | {s} | {v['basis'].replace('|', '/')[:300]} |")
    L += ["", "Scores come from references/scoring-rubric.md. A category's score is the reviewer's score, capped by open automated findings; "
          "technical integrity is scored from automated checks only.", ""]
    L += ["## Pipeline facts", ""]
    for k, v in meta.items():
        L.append(f"- {k}: {v}")
    if review_problems:
        L += ["", "## Visual review", "", *[f"- {p}" for p in review_problems]]
    elif review:
        L += ["", "## Visual review", "", f"- Reviewer: {review.get('reviewer')}; slides inspected: {review.get('inspected')}"]
    for sev, title in (("critical", "Critical issues"), ("major", "Major issues"), ("minor", "Minor issues")):
        L += ["", f"## {title}", "", *_flist([f for f in open_f if f["severity"] == sev])]
    info = [f for f in open_f if f["severity"] == "info"]
    if info:
        L += ["", "## Notes", "", *_flist(info)]
    L += ["", "## Automatically corrected", "", *(_flist(fixed) if fixed else ["- none"])]
    L += ["", "## Not fixed automatically (needs a person)", ""]
    L += [f"- **slide {f['slide']}** · `{f['code']}` · {f['reason']}" for f in refused] or ["- none"]
    if review and review.get("slide_notes"):
        L += ["", "## Slide-by-slide observations", ""]
        L += [f"- **slide {k}**: {v}" for k, v in sorted(review["slide_notes"].items(),
                                                          key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0) if v]
    recs = [f for f in (review or {}).get("findings", []) if f.get("recommendation")]
    if recs:
        L += ["", "## Recommended improvements", ""]
        L += [f"- **slide {f.get('slide') or '-'}** ({f['severity']}): {f['recommendation']}" for f in recs]
    L.append("")
    return "\n".join(L)
