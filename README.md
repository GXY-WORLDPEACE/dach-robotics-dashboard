# DACH Robotics Tender Intelligence

Public, mobile-friendly robotics procurement dashboard for Germany (DE), Austria (AT), and Switzerland (CH). GitHub Pages + scheduled GitHub Actions + JSON. **Starter project; NOT a complete live procurement service.**

## Features
- Responsive Chinese-language tender cards, keyword/country/priority filters and CSV export.
- Rule-based DOBOT product matching (preliminary keyword heuristic; not technical compliance verification).
- Deduplication by source notice ID or URL; first-seen date retention.
- RSS/Atom collector with explicit configured sources and error reporting.
- Daily GitHub Actions scan and automatic GitHub Pages deployment after data commits.
- No private CRM data, credentials, or internal commercial notes in the public repository.

## Deploy
1. Create a **public** GitHub repository and upload this project to its `main` branch (`git init`, `git add .`, `git commit`, `git branch -M main`, `git remote add origin ...`, `git push -u origin main`).
2. In **Settings → Pages → Build and deployment**, select **GitHub Actions**.
3. In **Settings → Actions → General**, ensure workflow permissions allow the collector to push commits (read/write). Organization policy may override this.
4. In **Actions**, run **Deploy Pages** manually once. Your URL will resemble `https://USERNAME.github.io/REPO/`.
5. Edit `collector/sources.json` to add **verified official RSS/Atom feeds**, for example `{ "name": "Verified feed name", "url": "https://official.example/rss", "country": "DE", "enabled": true }`. The example URL is illustrative only and MUST NOT be enabled as-is. Confirm access terms and feed semantics. **No official feeds are enabled by default.**
6. Run **Collect public tenders** manually; inspect `data/scan_status.json` for failures. Future scans run automatically, and data changes trigger Pages deployment.

## Schedule and reliability
GitHub Actions uses UTC and may run late or be skipped during load. Current schedule `07:15 UTC` is 08:15 in winter (CET) and 09:15 in summer (CEST); it is **not DST-aware**. For an exact 08:00 Europe/Berlin requirement, use an external timezone-aware scheduler or add an hourly trigger with a local-time guard. This workflow is separate from the existing ChatGPT 08:00 report.

## Data integrity and limitations
- Initial `data/tenders.json` intentionally contains **zero** tenders. No demo tenders are presented as real.
- RSS feeds often omit deadline, budget and technical attachments. Missing fields remain null, with status marked unverified.
- A real comprehensive collector for TED, e-Vergabe, SIMAP and Austria requires platform-specific APIs/search integrations, legal/terms checks, rate limiting, pagination and often official document parsing. Those integrations are **not implemented in this starter**.
- Scoring is only keyword matching. Manual validation against tender documents is required before bids.
- `data/tenders.json` is **public**. Do not store customer notes, quotes, contacts that are not public, API keys, or confidential information here.
- GitHub Pages is public hosting; it provides no private user login. A private CRM requires a separate authenticated backend and database.

## Local testing
```bash
python -m unittest discover -s tests -v
python -m collector.fetch
python -m http.server 8000
```
For local preview open `http://localhost:8000/docs/` but note the relative `data/` URL assumes the Pages build structure. To preview the full deployed structure, create `_site` as in `.github/workflows/pages.yml`, then serve `_site`.

## Files
- `docs/index.html` — static dashboard UI
- `collector/core.py` — normalization, deduplication and matching
- `collector/fetch.py` — RSS/Atom feed collector
- `collector/sources.json` — configurable official feed endpoints
- `data/tenders.json` — published data
- `data/scan_status.json` — collection health
- `.github/workflows/collect.yml` — daily collection
- `.github/workflows/pages.yml` — GitHub Pages deployment
