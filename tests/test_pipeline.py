import json
import subprocess
import sys
from pathlib import Path

from leadflow.dedupe import dedupe
from leadflow.enrich import enrich
from leadflow.normalize import Lead
from leadflow.pipeline import run
from leadflow.scoring import load_config, score
from leadflow.sinks import HubSpot

ROOT = Path(__file__).resolve().parent.parent
FILES = {"website_form": ROOT / "data/website_form.csv", "meta_lead_ads": ROOT / "data/meta_lead_ads.csv",
         "event_signups": ROOT / "data/event_signups.csv"}


def lead(**kw):
    base = {"source": "t", "row": 1, "name": "X"}
    return enrich(Lead(**(base | kw)))


def test_enrich_business_vs_free_mail():
    a = lead(email="omar@brightdental.ae")
    assert a.business_email and a.company == "Brightdental"
    assert not lead(email="x@gmail.com").business_email


def test_dedupe_by_email_phone_and_fuzzy_name():
    leads = [
        lead(row=1, name="Mohammed Ali", email="m.ali@riyadhmotors.sa", company="Riyadh Motors"),
        lead(row=2, name="Mohamed Ali", email="mohammed.ali@riyadhmotors.sa", job_title="Marketing Mgr"),
        lead(row=3, name="Sara", phone="+966501234567"),
        lead(row=4, name="Sara Malik", phone="+966501234567", email="sara@gmail.com"),
    ]
    unique, log = dedupe(leads)
    assert len(unique) == 2
    assert [r for *_, r in log] == ["name+domain", "phone"]
    assert unique[0].job_title == "Marketing Mgr"          # gap filled from duplicate
    assert unique[1].email == "sara@gmail.com"


def test_score_is_explained_and_graded():
    cfg = load_config()
    l = score(lead(name="N", email="n@corp.sa", job_title="CEO", country="SA", budget=120000, timeline="ASAP",
                   phone="+966500000000"), cfg)
    assert l.grade == "A" and l.route == "sales_call" and l.score == 98
    assert any("budget" in r for r in l.reasons)


def test_disposable_email_penalised():
    l = score(lead(email="a@mailinator.com", budget=60000), load_config())
    assert l.grade != "A" and any("disposable" in r for r in l.reasons)


def test_full_run_on_samples():
    r = run(FILES)
    assert sum(r.per_source.values()) == 24
    assert len(r.rejected) == 2 and len(r.merges) == 4 and len(r.leads) == 18
    faisal = next(l for l in r.leads if l.name == "Faisal Al-Harbi")
    assert faisal.merged_from == ["meta_lead_ads:2"]
    assert r.leads == sorted(r.leads, key=lambda l: -l.score)


def test_hubspot_dry_run_payload(tmp_path):
    r = run(FILES)
    summary = HubSpot(token=None).push(r.leads, tmp_path)
    payload = json.loads((tmp_path / "hubspot_payload.json").read_text())
    first = payload["batches"][0][0]
    assert summary["mode"] == "dry_run" and summary["skipped_no_email"] == 2
    assert first["idProperty"] == "email" and "leadflow_score" in first["properties"]


def test_hubspot_live_counts_new_and_updated(tmp_path):
    import httpx
    seen = {}

    def handler(req):
        seen["auth"] = req.headers["authorization"]
        n = len(json.loads(req.content)["inputs"])
        return httpx.Response(200, json={"results": [{"new": i % 2 == 0} for i in range(n)]})

    hs = HubSpot(token="pat-test", client=httpx.Client(transport=httpx.MockTransport(handler)), dry_run=False)
    out = hs.push(run(FILES).leads, tmp_path)
    assert out["mode"] == "live" and out["created"] + out["updated"] == 16 and seen["auth"] == "Bearer pat-test"


def test_cli_second_run_pushes_nothing_new(tmp_path):
    cmd = [sys.executable, "-m", "leadflow", "run", "--website_form", str(FILES["website_form"]), "--out", str(tmp_path)]
    first = json.loads(subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, check=True).stdout.split("\nreport:")[0])
    second = json.loads(subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, check=True).stdout.split("\nreport:")[0])
    assert first["new"] == 11 and second["new"] == 0
    assert (tmp_path / "report.html").exists() and (tmp_path / "leads_clean.csv").exists()
