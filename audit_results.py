#!/usr/bin/env python3
"""Offline integrity audit. Does not reclassify companies or contact any service."""
import csv
import json
from collections import Counter
from pathlib import Path

import screen


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def audit(directory):
    root = Path(directory)
    summary = json.loads((root / "summary.json").read_text())
    original = read_csv(summary["lead_file"])
    enriched = read_csv(root / "all_leads_screened.csv")
    assert len(original) == len(enriched) == summary["total_leads"], "Missing/added lead rows"
    assert screen.digest(Path(summary["lead_file"]).read_bytes()) == summary["lead_sha256"], "Source leads changed"
    assert screen.digest(Path(summary["matrix_file"]).read_bytes()) == summary["matrix_sha256"], "Source matrix changed"
    for number, (before, after) in enumerate(zip(original, enriched), 2):
        assert all(after[key] == value for key, value in before.items()), f"Original fields changed at row {number}"
        assert int(after["screen_source_row"]) == number, "Source row mapping changed"
        assert after["screen_domain"] == screen.domain_of(before["Website"]), "Domain join changed"
    assert Counter(r["screen_status"] for r in enriched) == summary["lead_counts"], "Lead counts differ"
    companies = read_csv(root / "companies.csv")
    by_domain = {row["domain"]: row for row in companies}
    assert len(by_domain) == len(companies) == summary["processed_domains"], "Duplicate/missing company records"
    assert Counter(r["screen_status"] for r in companies) == summary["company_counts"], "Company counts differ"
    checks = Counter()
    for row in enriched:
        company = by_domain.get(row["screen_domain"])
        if company:
            assert row["screen_status"] == company["screen_status"], "Inconsistent contact join"
    for status, filename in [("OUT_OF_NICHE", "out_of_niche.csv"), ("POTENTIAL_FIT", "potential_fit.csv"), ("REVIEW", "needs_review.csv")]:
        actual = read_csv(root / filename)
        expected = [r for r in enriched if r["screen_status"] == status]
        assert actual == expected, f"Partition mismatch: {filename}"
    for company in companies:
        if not company.get("screen_judgment_file"):
            assert company["screen_status"] == "REVIEW", "Evidence-free company escaped review"
            continue
        evidence = json.loads(Path(company["screen_evidence_file"]).read_text())
        judgment = json.loads(Path(company["screen_judgment_file"]).read_text())
        request, response = judgment["request"], judgment["response"]
        assert screen.digest(evidence) == company["screen_evidence_hash"], "Evidence hash mismatch"
        assert screen.digest(request) == company["screen_request_hash"], "Request hash mismatch"
        assert set(request["state"]["company"]) == {"domain", "names"}, "Unexpected company data submitted"
        screen.validate_response(response, request)
        decision = screen.decide(evidence, request, response)
        for key, value in decision.items():
            assert str(value) == company[key], f"Decision mismatch for {company['domain']} {key}"
        excerpt = decision["screen_evidence_excerpt"]
        if excerpt:
            matching_pages = [page for page in evidence["pages"] if page["url"] == decision["screen_evidence_url"]]
            assert matching_pages, "Missing excerpt source URL"
            assert any(all(line in page["text"] for line in excerpt.splitlines()) for page in matching_pages), "Excerpt contains text absent from source"
        checks[company["screen_status"]] += 1
    report = {"audited_at": screen.now(), "original_fields_preserved": True,
              "partition_files_exact": True, "lead_rows": len(original), "company_rows": len(companies),
              "decision_and_evidence_checks": dict(checks),
              "unprocessed_leads": sum(r["screen_status"] == "NOT_PROCESSED" for r in enriched),
              "meaning": "File integrity, provenance and routing checks only; not semantic accuracy validation"}
    screen.save(root / "integrity_audit.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default=screen.ROOT / "results")
    audit(parser.parse_args().directory)
