from pathlib import Path
import json

packet = Path(__file__).resolve().parent
plan = json.loads((packet / "CASE_PLAN.json").read_text(encoding="utf-8"))
sites = []
for control in plan["groups"]["full16"]["controls"]:
    sites.append({
        "site_id": control["site_id"],
        "positive": None,
        "negative": None,
        "restore": None,
        "note": ""
    })
doc = {
    "schema": 1,
    "status": "pending_root_review",
    "group": "full16",
    "candidate_source": plan["candidate_source"],
    "run_dir": "",
    "manifest_sha256": "",
    "reviewer": "",
    "reviewed_utc": "",
    "sites": sites,
    "deferred_sites": [],
    "inventory_status_changed": False
}
(packet / "root_templates" / "ROOT_VISUAL_JUDGMENT.template.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
print("root visual rows", len(sites))
