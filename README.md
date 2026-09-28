# Financial niche screening and outreach

Two Python scripts use company website evidence, a financial niche dashboard, and TypeSafe to screen leads and prepare role-specific outreach drafts.

- [`screen.py`](screen.py) fetches public company pages and classifies companies as `POTENTIAL_FIT`, `OUT_OF_NICHE`, or `REVIEW`.
- [`outreach.py`](outreach.py) evaluates every potential-fit contact against dashboard offers and their job title, composes an opener followed by a service pitch, then checks the draft. Unsupported or uncertain cases remain `HOLD` with a reason and blank copy.

The workflow does not send messages. TypeSafe makes typed judgments; Python composes the copy from templates and dashboard text. Similar roles and offers can produce similar phrasing.

## Setup

Python 3.10 or newer is required.

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
mkdir -p inputs
```

Supply your own private files at these paths:

```text
inputs/top-leads-with-copy.csv
inputs/US_Financial_Niche_Matrix-Dashboard.csv
```

The lead CSV needs `First Name`, `Last Name`, `Website`, `Email`, `company_name`, and `job_title`. Additional columns are preserved, including any original outreach copy. Websites must be valid public domain names or URLs. Validate input rows before starting a run.

The dashboard parser is specific to the financial matrix layout used by this project:

- A category summary headed `Category,Average Score,Niches`, followed by the 13 names in `screen.CATEGORIES`.
- Fifteen ranked offer records with rank in column A, an `A -` or `B -` tier in B, prospect business in D, category in E, offer name in F, and pitch in G. Their rank meanings must match `outreach.ANGLES`.
- Four starting-lane records named `Financial operations & compliance`, `Specialty finance origination`, `Insurance distribution & risk`, and `Proprietary acquisition origination`. Lane source niche is in F and source offer text in I.

The original lead list and dashboard are intentionally not included. For a different dashboard, review the taxonomy, parser, offer catalog, and opportunity angles before running. This is not a general-purpose CSV schema detector. The four lane pitches are explicit code-defined interpretations of their source rows.

Set `TYPESAFE_API_KEY` through your shell or secret manager. Never commit a key, put it in command arguments, or include it in an input file. API calls require a TypeSafe account and may incur usage charges.

## Run both stages

```sh
python3 -m unittest -v
python3 screen.py --profile
python3 screen.py --workers 24
python3 audit_results.py
python3 outreach.py --workers 16
python3 audit_outreach.py
```

No `--limit` means process the full eligible pool. For an initial sample, use `--limit 30 --sample` on either main script. A limited run overwrites aggregate exports with explicit `NOT_PROCESSED` rows; run again without the limit to restore complete exports. Run only one process per output directory.

The default locations above work for both stages and audits. Screening also supports `--leads`, `--matrix`, and `--out`, but outreach currently expects the default retained inputs and `results/` directory. Keep those defaults for the end-to-end workflow. `python3 SCRIPT.py --help` lists options for each main script.

## Outputs

| File | Contents |
| --- | --- |
| `results/potential_fit.csv` | Companies with supported financial category membership |
| `results/out_of_niche.csv` | Clear outsiders under the configured exclusion rules |
| `results/needs_review.csv` | Unclear, blocked, or unresolved companies |
| `results/all_leads_screened.csv` | Original rows and screening fields |
| `outreach/outreach_drafts.csv` | Review drafts with separate opener, pitch, CTA, and combined copy |
| `outreach/outreach_holds.csv` | Held rows and reasons, including ineligible screening rows |
| `outreach/all_leads_with_outreach.csv` | Full original list with both stages attached |
| `outreach/draft_summary.json` | Eligible-pool counts, hold reasons, and configured thresholds |

Filter held rows to `screen_status=POTENTIAL_FIT` to inspect the outreach-stage holds. Financial category fit does not by itself imply a supported offer or relevant buyer role.

Evidence and raw judgments are saved locally for inspection. Website evidence is reused for up to seven days; `screen.py --refresh` fetches it again. Successful judgments are reused only for an identical request hash. Errors remain review/hold cases and retry on the next run. A cached judgment is not automatically rerun when the `jev-latest` alias changes. Local artifacts contain contact data and should remain private; `.gitignore` excludes them.

## Evidence and limits

Screening uses company identity, evidence sufficiency, category, exclusion, and literal excerpt checks. It fetches a homepage and up to two linked pages by default, without JavaScript execution or access-control bypass. Page failures do not imply exclusion. External-domain redirects require review.

Outreach selects an offer, role family, and literal website term, then checks business fit, role fit, opener grounding, proposed audience fit, supported claims, and readability. Business and audience checks assess compatibility, not predicted commercial success. The question definitions are recorded in `outreach_check_revision.json`; numeric gates are in `outreach.QA_MINIMUMS`.

The screening API context contains company names, domains, and public site text. Outreach adds job titles. Recipient names and emails stay local; names are merged into greetings after judgment. All original lead fields remain in local CSV exports.

Tests use synthetic evidence and dashboard records and need no API key or private files. Audits verify preservation, partitions, provenance, and saved routing decisions. Neither tests nor audits establish classification accuracy, current employment, buying intent, geography, sender capabilities, or copy effectiveness. Drafts require editorial review, and service claims must match what the sender can actually deliver.

TypeSafe documentation: [HTTP API](https://docs.typesafe.ai/api), [Choice](https://docs.typesafe.ai/primitives/choice), [Noul](https://docs.typesafe.ai/primitives/noul).
