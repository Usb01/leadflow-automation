"""Points-based lead scoring driven by config/scoring.json, so sales can tune it without code changes."""
import json
import re
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "scoring.json"


def load_config(path: Path | None = None) -> dict:
    return json.loads((path or DEFAULT_CONFIG).read_text(encoding="utf-8"))


def score(lead, cfg: dict):
    pts, reasons = 0, []

    def add(p, why):
        nonlocal pts
        if not p:
            return
        pts += p
        reasons.append(f"{'+' if p >= 0 else ''}{p} {why}")

    if lead.budget is not None:
        for band in cfg["budget_bands"]:
            if lead.budget >= band["min"]:
                add(band["points"], f"budget ≥ {band['min']:,}")
                break
    else:
        add(cfg["missing_budget"], "no budget given")

    if lead.timeline:
        t = lead.timeline.lower()
        for rule in cfg["timeline"]:
            if re.search(rule["pattern"], t):
                add(rule["points"], f"timeline '{lead.timeline}'")
                break

    if lead.business_email:
        add(cfg["business_email"], "business email")
    if lead.job_title:
        for rule in cfg["titles"]:
            if re.search(rule["pattern"], lead.job_title, re.I):
                add(rule["points"], f"title '{lead.job_title}'")
                break
    if lead.country in cfg["target_countries"]:
        add(cfg["target_country_points"], f"target market {lead.country}")
    if lead.phone:
        add(cfg["has_phone"], "phone number")
    if lead.merged_from:
        add(cfg["repeat_interest"], "contacted us more than once")
    if any("disposable" in r for r in lead.reasons):
        add(cfg["disposable_email"], "disposable email")

    lead.score = max(0, min(100, pts))
    lead.grade = next(g["grade"] for g in cfg["grades"] if lead.score >= g["min"])
    lead.route = cfg["routes"][lead.grade]
    lead.reasons = [r for r in lead.reasons if "disposable" not in r] + reasons
    return lead
