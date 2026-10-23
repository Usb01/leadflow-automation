import csv
import json
from pathlib import Path

from .normalize import (InvalidLead, Lead, clean_budget, clean_country, clean_email, clean_name, clean_phone)

CONFIG = Path(__file__).resolve().parent.parent / "config" / "sources.json"


def load_mappings(path: Path | None = None) -> dict:
    data = json.loads((path or CONFIG).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def read_source(path: Path, source: str, mapping: dict, default_country: str = "SA"):
    """Yield (Lead | None, error | None, raw_row) for every row of a CSV export."""
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for i, raw in enumerate(csv.DictReader(fh), start=2):  # row 1 is the header
            fields = {mapping[k.strip()]: (v or "").strip() for k, v in raw.items() if k and k.strip() in mapping}
            try:
                yield to_lead(fields, source, i, default_country), None, raw
            except InvalidLead as exc:
                yield None, str(exc), raw | {"_ref": f"{source}:{i}"}


def to_lead(f: dict, source: str, row: int, default_country: str) -> Lead:
    email = clean_email(f.get("email"))
    country = clean_country(f.get("country"))
    phone, phone_country = clean_phone(f.get("phone"), country or default_country)
    if not email and not phone:
        raise InvalidLead("no email or phone – can't contact")
    return Lead(
        source=source,
        row=row,
        name=clean_name(f.get("name")),
        email=email,
        phone=phone,
        company=f.get("company") or None,
        job_title=f.get("job_title") or None,
        country=country or phone_country,
        budget=clean_budget(f.get("budget")),
        timeline=f.get("timeline") or None,
        message=f.get("message") or None,
        submitted_at=f.get("submitted_at") or None,
    )
