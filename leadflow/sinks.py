"""Where cleaned leads go: a CSV for import anywhere, or HubSpot via the CRM v3 API."""
import csv
import json
import os
from dataclasses import asdict
from pathlib import Path

import httpx

CSV_FIELDS = ["name", "email", "phone", "company", "job_title", "country", "budget", "timeline", "score", "grade",
              "route", "source", "merged_from", "message"]


def write_csv(leads, path: Path) -> Path:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for lead in leads:
            row = asdict(lead)
            row["merged_from"] = ";".join(lead.merged_from)
            w.writerow(row)
    return path


def hubspot_properties(lead) -> dict:
    first, _, last = lead.name.partition(" ")
    props = {
        "email": lead.email,
        "firstname": first,
        "lastname": last,
        "phone": lead.phone,
        "company": lead.company,
        "jobtitle": lead.job_title,
        "country": lead.country,
        "hs_lead_status": "NEW",
        # custom properties – create these once in HubSpot (Settings → Properties)
        "leadflow_score": lead.score,
        "leadflow_grade": lead.grade,
        "leadflow_route": lead.route,
        "leadflow_source": lead.source,
    }
    return {k: v for k, v in props.items() if v not in (None, "")}


class HubSpot:
    """Batch upsert contacts by email. Leads without an email are skipped (HubSpot needs a unique key)."""

    URL = "https://api.hubapi.com/crm/v3/objects/contacts/batch/upsert"

    def __init__(self, token: str | None = None, client: httpx.Client | None = None, dry_run: bool = True):
        self.token = token or os.getenv("HUBSPOT_TOKEN")
        self.client = client or httpx.Client(timeout=30)
        self.dry_run = dry_run or not self.token

    def push(self, leads, out_dir: Path) -> dict:
        inputs = [{"idProperty": "email", "id": l.email, "properties": hubspot_properties(l)} for l in leads if l.email]
        skipped = sum(1 for l in leads if not l.email)
        batches = [inputs[i:i + 100] for i in range(0, len(inputs), 100)]  # API limit is 100 per call

        if self.dry_run:
            (out_dir / "hubspot_payload.json").write_text(json.dumps({"batches": batches}, indent=2), encoding="utf-8")
            return {"mode": "dry_run", "contacts": len(inputs), "skipped_no_email": skipped}

        created = updated = 0
        for batch in batches:
            r = self.client.post(self.URL, headers={"Authorization": f"Bearer {self.token}"}, json={"inputs": batch})
            r.raise_for_status()
            for res in r.json().get("results", []):
                created += res.get("new", False)
                updated += not res.get("new", False)
        return {"mode": "live", "created": created, "updated": updated, "skipped_no_email": skipped}
