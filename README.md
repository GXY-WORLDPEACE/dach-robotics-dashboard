# DACH Robotics Tender Intelligence

Live public tender dashboard: https://gxy-worldpeace.github.io/dach-robotics-dashboard/

## Sources and scope
- **TED connected**: official keyless `POST https://api.ted.europa.eu/v3/notices/search`, Germany/Austria buyers, competition notices, future submission deadlines. Queries robot/cobot/manipulator/humanoid/automation terms in procedure title and description. Software licences, construction and consulting titles are excluded. This is a targeted search, not complete DACH coverage.
- **SIMAP not connected**: official Swagger https://www.simap.ch/api-doc/ and OpenAPI https://www.simap.ch/api/specifications/simap.yaml verified. The specification exposes `/publications/v2/project/project-search` and publication detail endpoints. Search/detail field mapping, pagination and operational reliability remain unverified; no Swiss records are fabricated or imported.
- National below-threshold platforms are not connected.

## Run and validate
Python 3.12+, standard library only. No API key required.

```
python -m unittest discover -s tests -v
python -m collector.fetch
```

`data/tenders.json` contains current active notices; `data/history.json` retains previously collected records. IDs are TED publication numbers with a source prefix; repeated scans update the same notice and retain first_seen. Distinct official publications/corrections retain separate IDs in history; the dashboard displays the latest publication per procedure_id when available. Last successful data survives API errors, with error status published and workflow failure. Partial/pagination failures fail closed. Missing budgets stay null; amounts are procedure-level estimates, not device prices. Multiple future lot deadlines are stored, the earliest is displayed. A missing time is date-only (assumed valid until that local day's end), and must be checked manually. Removed notices are marked unavailable in history; this is not proof of cancellation.

P1: explicit product-family keywords; P2: generic robotics; P3: broad automation or specialist medical/cleaning/lab applications. Reasons and candidate DOBOT families appear on cards. This is preliminary matching, not technical qualification. Verify payload, reach, interfaces, safety, lots and deadlines in official documents. No private customer data or secrets belong here.

## Automation and Pages
Collection runs at UTC 06:00 and 07:00 with a Europe/Berlin timezone guard choosing 08:00 local time (CET/CEST). A same-local-day success guard avoids duplicate scheduled runs. GitHub Actions may delay or skip scheduled runs; this is not a strict delivery SLA. Manual runs bypass the guard.

The collector tests, queries TED, commits JSON to main. Pages runs on main pushes **and collection workflow completion**, because GITHUB_TOKEN pushes do not trigger another push workflow. Pages always checks out main and packages docs plus data. A failed scan deploys its error status while retaining prior successful data. Enable GitHub Pages with GitHub Actions and allow contents writes. `collector/sources.json` is a source inventory; TED implementation and filtering live in `collector/ted.py`.
