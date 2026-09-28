#!/usr/bin/env python3
"""Validate draft files and provenance without making semantic acceptance claims."""
import csv
import json
from collections import Counter
from pathlib import Path

import outreach as o
import screen as s


def read(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    root = s.ROOT / "outreach"
    source = read(s.DEFAULT_LEADS)
    output = read(root / "all_leads_with_outreach.csv")
    report = json.loads((root / "draft_summary.json").read_text())
    assert len(source) == len(output), "Missing or added source rows"
    assert report["lead_sha256"] == s.digest(s.DEFAULT_LEADS.read_bytes())
    assert report["matrix_sha256"] == s.digest(s.DEFAULT_MATRIX.read_bytes())
    for number, (before, after) in enumerate(zip(source, output), 2):
        assert all(before[k] == after[k] for k in before), f"Original field changed at row {number}"
        assert int(after["screen_source_row"]) == number
        if after["outreach_status"] != "DRAFT_FOR_REVIEW":
            assert not after.get("outreach_copy"), "Held/unprocessed row contains draft copy"
    assert Counter(r["outreach_status"] for r in output) == report["status_counts"]
    assert not any(r["outreach_status"] == "NOT_PROCESSED" for r in output)
    drafts = [r for r in output if r["outreach_status"] == "DRAFT_FOR_REVIEW"]
    holds = [r for r in output if r["outreach_status"] == "HOLD"]
    assert read(root / "outreach_drafts.csv") == drafts
    assert read(root / "outreach_holds.csv") == holds
    offers = o.catalog()
    for row in drafts:
        assert row["screen_status"] == "POTENTIAL_FIT"
        offer = offers[row["outreach_offer_id"]]
        assert row["outreach_service_pitch"] == o.clean_copy(offer["pitch"])
        assert int(row["outreach_offer_source_record"]) == offer["source_record"]
        assert row["outreach_copy"] == "\n\n".join(row[k] for k in ("outreach_opener", "outreach_service_pitch", "outreach_cta"))
        assert not any(char in row["outreach_copy"] for char in "-–—")
        evidence = json.loads(Path(row["screen_evidence_file"]).read_text())
        assert s.digest(evidence) == row["screen_evidence_hash"]
        assert any(page["url"] == row["outreach_website_url"] and row["outreach_website_term"] in page["text"] for page in evidence["pages"])
        qa_path = Path(row["outreach_qa_file"])
        saved = json.loads(qa_path.read_text())
        assert qa_path.stem == s.digest(saved["request"])
        s.validate_response(saved["response"], saved["request"])
        assert saved["request"]["state"]["job_title"] == row["job_title"]
        assert saved["request"]["state"]["company"]["domain"] == row["screen_domain"]
        assert saved["request"]["state"]["selected_offer"] == offer
        for key, minimum in o.QA_MINIMUMS.items():
            value = saved["response"]["answers"][key]["noul"]
            assert value >= minimum
            assert float(row["outreach_qa_" + key]) == value
    audit = {"audited_at": s.now(), "source_rows_preserved": len(source), "draft_rows": len(drafts),
             "hold_rows": len(holds), "unprocessed_rows": 0, "original_copy_preserved": True,
             "held_copy_blank": True, "source_and_offer_provenance_checked": True,
             "configured_model_gates_replayed": True,
             "limitation": "Integrity and routing validation; no independent proof of model accuracy, current employment, buying intent or outreach effectiveness"}
    s.save(root / "integrity_audit.json", audit)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
