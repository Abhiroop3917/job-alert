# Tech Jobs India Alert

Monitors 8 company career portals for entry-level tech jobs in India and sends real-time notifications. Two delivery modes — a GitHub Actions backend and a Chrome extension — both run independently.

---

## How it works

Every run fetches jobs from all 7 sources, filters for 0–2 year experience based on description text, deduplicates against previously seen IDs, and notifies only for new jobs.

| Source | Filter applied |
|---|---|
| Google | URL params (`target_level=EARLY`, `location=India`) |
| IBM | API params (`Entry Level`, `India`) |
| Microsoft | API params (`Entry`, `India`) |
| Amazon | URL param + description year filter |
| ServiceNow | RSS description year filter |
| Apple | Detail page `minimumQualifications` year filter |
| Deloitte | Detail page full text year filter |
| Meta | Detail page `qualifications` year filter |

**Experience filter rule:** scan description text for `N years` patterns. Keep the job if the highest number found is 0 (no explicit requirement) or ≤ 2.

---

## GitHub Actions Backend

Runs on a cron schedule, stores seen job IDs back to the repo, and pushes notifications via ntfy.sh and Gmail.

### Setup

**1. Fork / clone this repo.**

**2. Add GitHub Secrets** (`Settings → Secrets and variables → Actions`):

| Secret | Description |
|---|---|
| `NTFY_TOPIC` | Your ntfy.sh topic name (e.g. `my-job-alerts`) |
| `GMAIL_ADDRESS` | Gmail address for email digest |
| `GMAIL_APP_PASSWORD` | Gmail [App Password](https://myaccount.google.com/apppasswords) (not your login password) |

`NTFY_TOPIC` is required. Gmail secrets are optional — omit them to skip the email digest.

**3. Enable the workflow.**

The workflow runs every 5 minutes via cron. You can also trigger it manually from the Actions tab (`workflow_dispatch`).

### Receiving notifications

Install the **ntfy** app ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [iOS](https://apps.apple.com/app/ntfy/id1625396347) / [Web](https://ntfy.sh)) and subscribe to your topic name.

### Running locally

```bash
pip install -r requirements.txt
export NTFY_TOPIC=your-topic
python main.py
```

---

## Chrome Extension

Runs entirely in your browser — no server needed. Checks all 7 sources on a configurable interval and fires desktop notifications for new jobs.

### Setup

1. Open `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** → select the `extension/` folder in this repo
4. The extension installs as **Tech Jobs India Alert**

### Usage

Click the extension icon to open the popup:

- **Check now** — run an immediate fetch across all sources
- **Pause / Resume** — suspend periodic checks
- **Test alert** — verify desktop notifications are working
- **Reset** — clear all seen job IDs and re-seed (useful after a long pause)
- **Settings** — configure source URLs, enable/disable IBM and Microsoft, set check interval

On first load the extension silently seeds all currently matching jobs so you only get alerted for jobs posted after installation.

---

## Project structure

```
job-alert/
├── main.py                  # GitHub Actions entry point
├── config.py                # Source URLs and environment variables
├── requirements.txt
├── seen_jobs.json           # Persisted seen job IDs (committed by CI)
├── architecture.html        # Visual architecture diagram
├── parsers/
│   ├── experience.py        # Shared 0-2 yr experience filter
│   ├── google_parser.py
│   ├── servicenow_parser.py
│   ├── apple_parser.py
│   ├── deloitte_parser.py
│   ├── ibm_parser.py
│   ├── amazon_parser.py
│   ├── microsoft_parser.py
│   └── meta_parser.py
├── tests/                   # pytest test suite
└── extension/               # Chrome extension (MV3)
    ├── manifest.json
    ├── background.js        # Service worker — orchestrates all fetching
    ├── experienceFilter.js  # Shared 0-2 yr experience filter
    ├── filters.js
    ├── storage.js
    ├── popup.html / popup.js
    ├── notifications.js
    └── *Parser.js           # One parser per source
```

---

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```
