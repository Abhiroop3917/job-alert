#!/usr/bin/env python3
"""Job monitor — fetches all sources, notifies via ntfy.sh for new matching jobs."""

import json
import re
import smtplib
import sys
import time
from email.mime.text import MIMEText
from pathlib import Path

import requests

import config
from parsers.google_parser import parse_google_jobs
from parsers.servicenow_parser import parse_servicenow_jobs
from parsers.apple_parser import parse_apple_jobs, parse_apple_job_detail
from parsers.deloitte_parser import parse_deloitte_jobs, parse_deloitte_job_detail
from parsers.experience import is_entry_level_experience
from parsers.ibm_parser import parse_ibm_jobs
from parsers.amazon_parser import parse_amazon_jobs
from parsers.microsoft_parser import parse_microsoft_jobs
from parsers.meta_parser import parse_meta_jobs, parse_meta_job_detail, META_VARIABLES, META_GRAPHQL_URL, META_DOC_ID

SEEN_FILE     = Path("seen_jobs.json")
BULK_THRESHOLD = 20   # if more new jobs than this, only notify a preview
PREVIEW_COUNT  = 5    # how many to notify during a bulk seed
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 60


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def load_seen():
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2))


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def _get(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def _post_json(url, body):
    r = requests.post(
        url,
        json=body,
        headers={**HEADERS, "Content-Type": "application/json", "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def fetch_all_pages(base_url, parser_fn, page_param="page", page_start=1, page_step=1):
    base = re.sub(rf'[?&]{re.escape(page_param)}=\d+', '', base_url).rstrip('?&')
    sep  = '&' if '?' in base else '?'
    all_jobs, seen_ids = [], set()

    for page_val in range(page_start, page_start + 10 * page_step, page_step):
        try:
            jobs = parser_fn(_get(f'{base}{sep}{page_param}={page_val}'))
            if not jobs:
                break
            for job in jobs:
                if job['id'] not in seen_ids:
                    seen_ids.add(job['id'])
                    all_jobs.append(job)
        except Exception as e:
            print(f"    page {page_val} error: {e}")
            break

    return all_jobs


def fetch_ibm_jobs():
    all_jobs, seen_ids = [], set()
    page_size = 30

    for from_idx in range(0, 300, page_size):
        try:
            data = _post_json("https://www-api.ibm.com/search/api/v2", {
                "appId": "careers",
                "scopes": ["careers2"],
                "query": {"bool": {"must": []}},
                "post_filter": {"bool": {"must": [
                    {"term": {"field_keyword_18": "Entry Level"}},
                    {"term": {"field_keyword_05": "India"}},
                ]}},
                "size": page_size,
                "from": from_idx,
                "sort": [{"_score": "desc"}, {"pageviews": "desc"}],
                "lang": "zz",
                "localeSelector": {},
                "_source": ["_id", "title", "url", "field_keyword_18", "field_keyword_19"],
            })
            jobs = parse_ibm_jobs(data)
            if not jobs:
                break
            for job in jobs:
                if job['id'] not in seen_ids:
                    seen_ids.add(job['id'])
                    all_jobs.append(job)
            if len(jobs) < page_size:
                break
        except Exception as e:
            print(f"    IBM page {from_idx} error: {e}")
            break

    return all_jobs


def fetch_amazon_jobs():
    all_jobs, seen_ids = [], set()

    for offset in range(0, 1000, 100):
        try:
            import json as _json
            jobs = parse_amazon_jobs(_json.loads(_get(f'{config.AMAZON_URL}&offset={offset}')))
            if not jobs:
                break
            for job in jobs:
                if job['id'] not in seen_ids:
                    seen_ids.add(job['id'])
                    all_jobs.append(job)
            if len(jobs) < 100:
                break
        except Exception as e:
            print(f"    Amazon offset {offset} error: {e}")
            break

    return all_jobs


def fetch_apple_jobs():
    all_jobs, seen_ids = [], set()

    for page in range(1, 11):
        try:
            jobs = parse_apple_jobs(_get(f'{config.APPLE_URL}&page={page}'))
            if not jobs:
                break
            for job in jobs:
                if job['id'] not in seen_ids:
                    seen_ids.add(job['id'])
                    all_jobs.append(job)
            if len(jobs) < 20:
                break
        except Exception as e:
            print(f"    Apple page {page} error: {e}")
            break

    filtered = []
    for job in all_jobs:
        try:
            detail_html = _get(job['url'])
            qualifications = parse_apple_job_detail(detail_html)
            if is_entry_level_experience(qualifications):
                filtered.append(job)
        except Exception as e:
            print(f"    Apple detail fetch error ({job['id']}): {e}")
            filtered.append(job)   # include on error — better to over-notify than miss

    return filtered


def fetch_deloitte_jobs():
    all_jobs, seen_ids = [], set()

    for startrow in range(0, 300, 25):
        try:
            jobs = parse_deloitte_jobs(_get(f'{config.DELOITTE_URL}&startrow={startrow}'))
            if not jobs:
                break
            for job in jobs:
                if job['id'] not in seen_ids:
                    seen_ids.add(job['id'])
                    all_jobs.append(job)
            if len(jobs) < 25:
                break
        except Exception as e:
            print(f"    Deloitte startrow {startrow} error: {e}")
            break

    filtered = []
    for job in all_jobs:
        try:
            detail_html = _get(job['url'])
            description = parse_deloitte_job_detail(detail_html)
            if is_entry_level_experience(description):
                filtered.append(job)
        except Exception as e:
            print(f"    Deloitte detail fetch error ({job['id']}): {e}")
            filtered.append(job)   # include on error

    return filtered


def fetch_microsoft_jobs():    session = requests.Session()
    # Step 1: load the page to obtain the CSRF token and session cookies
    r = session.get(config.MICROSOFT_URL, headers=HEADERS, timeout=TIMEOUT)
    csrf = r.headers.get('x-csrf-token', '')

    # Step 2: call the JSON search API with the CSRF token
    api_headers = {
        **HEADERS,
        'Accept': 'application/json, text/plain, */*',
        'X-CSRF-Token': csrf,
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': config.MICROSOFT_URL,
    }
    api_resp = session.get(
        'https://apply.careers.microsoft.com/api/pcsx/search',
        params={
            'domain': 'microsoft.com',
            'query': '',
            'location': 'India',
            'start': '0',
            'num_rec': '100',
            'sort_by': 'recent',
            'filter_include_remote': '1',
            'filter_seniority': 'Entry',
        },
        headers=api_headers,
        timeout=TIMEOUT,
    )
    api_resp.raise_for_status()
    return parse_microsoft_jobs(api_resp.json())


def fetch_meta_jobs():
    import json as _json

    # Step 1: load the Meta page with browser-like headers to extract session tokens
    meta_page_headers = {
        **HEADERS,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
    }
    page_html = requests.get(config.META_PAGE_URL, headers=meta_page_headers, timeout=TIMEOUT).text

    lsd_m    = re.search(r'"LSD",\[\],\{"token":"([^"]+)"', page_html)
    spin_r_m = re.search(r'"__spin_r":(\d+)', page_html)
    spin_t_m = re.search(r'"__spin_t":(\d+)', page_html)

    if not (lsd_m and spin_r_m and spin_t_m):
        raise ValueError("Meta: could not extract session tokens from page")

    lsd    = lsd_m.group(1)
    spin_r = spin_r_m.group(1)
    spin_t = spin_t_m.group(1)

    # Step 2: call the Meta GraphQL search API
    api_resp = requests.post(
        META_GRAPHQL_URL,
        data={
            'av': '0',
            '__user': '0',
            '__a': '1',
            'lsd': lsd,
            '__rev': spin_r,
            '__spin_r': spin_r,
            '__spin_b': 'trunk',
            '__spin_t': spin_t,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'CareersJobSearchResultsV2DataQuery',
            'server_timestamps': 'true',
            'variables': _json.dumps(META_VARIABLES),
            'doc_id': META_DOC_ID,
        },
        headers={
            **HEADERS,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.metacareers.com',
            'Referer': 'https://www.metacareers.com/jobsearch/',
        },
        timeout=TIMEOUT,
    )
    api_resp.raise_for_status()
    all_jobs = parse_meta_jobs(api_resp.json())

    # Step 3: filter each job using its detail page qualifications text
    filtered = []
    for job in all_jobs:
        try:
            detail_html = _get(job['url'])
            qualifications = parse_meta_job_detail(detail_html)
            if is_entry_level_experience(qualifications):
                filtered.append(job)
        except Exception as e:
            print(f"    Meta detail fetch error ({job['id']}): {e}")
            filtered.append(job)  # include on error — better to over-notify than miss

    return filtered


def fetch_all_jobs():
    sources = [
        ("Google",     lambda: fetch_all_pages(config.GOOGLE_URL, parse_google_jobs)),
        ("ServiceNow", lambda: parse_servicenow_jobs(_get(config.SERVICENOW_URL))),
        ("Apple",      fetch_apple_jobs),
        ("Deloitte",   fetch_deloitte_jobs),
        ("IBM",        fetch_ibm_jobs),
        ("Amazon",     fetch_amazon_jobs),
        ("Microsoft",  fetch_microsoft_jobs),
        ("Meta",       fetch_meta_jobs),
    ]

    results = []
    for name, fn in sources:
        print(f"  Fetching {name}...")
        try:
            jobs = fn()
            print(f"    {len(jobs)} jobs found")
            results.extend(jobs)
        except Exception as e:
            print(f"    {name} failed: {e}")
    return results


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def apply_filters(jobs):
    out = []
    for job in jobs:
        if config.LOCATIONS:
            loc = job.get('location', '').lower()
            if not any(l.lower() in loc for l in config.LOCATIONS):
                continue
        if config.KEYWORDS:
            title = job.get('title', '').lower()
            if not any(k.lower() in title for k in config.KEYWORDS):
                continue
        out.append(job)
    return out


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

def notify(job):
    if not config.NTFY_TOPIC:
        return
    source   = job.get('source', 'Job')
    location = job.get('location', '')
    posted   = job.get('posted', '')
    url      = job.get('url', '')

    body = job['title']
    if location:
        body += f"\n{location}"
    if posted:
        body += f"\nPosted: {posted}"

    try:
        requests.post(
            f"https://ntfy.sh/{config.NTFY_TOPIC}",
            data=body.encode('utf-8'),
            headers={
                "Title": f"New {source} Job!",
                "Tags": "briefcase",
                "Click": url,
                "Priority": "default",
            },
            timeout=10,
        )
    except Exception as e:
        print(f"    ntfy failed: {e}")


def notify_email_digest(new_jobs):
    if not config.GMAIL_ADDRESS or not config.GMAIL_APP_PASSWORD or not new_jobs:
        return

    lines = []
    for job in new_jobs:
        lines.append(f"[{job.get('source')}] {job['title']}")
        if job.get('location'):
            lines.append(f"  Location: {job['location']}")
        if job.get('url'):
            lines.append(f"  Apply: {job['url']}")
        lines.append("")

    body = "\n".join(lines)
    msg = MIMEText(body)
    msg['Subject'] = f"Job Alert: {len(new_jobs)} new job(s) found"
    msg['From']    = config.GMAIL_ADDRESS
    msg['To']      = config.GMAIL_ADDRESS

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
            s.send_message(msg)
        print(f"  Email digest sent: {len(new_jobs)} jobs")
    except Exception as e:
        print(f"    email failed: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not config.NTFY_TOPIC:
        print("ERROR: NTFY_TOPIC environment variable not set.")
        sys.exit(1)

    print("=== Job Monitor ===")
    seen = load_seen()
    print(f"Seen IDs loaded: {len(seen)}")

    print("\nFetching jobs...")
    all_jobs  = fetch_all_jobs()
    matching  = apply_filters(all_jobs)
    print(f"\nMatching: {len(matching)} of {len(all_jobs)} total")

    new_jobs = [j for j in matching if j['id'] not in seen]
    print(f"New jobs: {len(new_jobs)}")

    # When a new source is added for the first time it floods hundreds of jobs.
    # Seed all as seen but only notify about the 5 most recent as a preview.
    if len(new_jobs) > BULK_THRESHOLD:
        print(f"  Bulk seed detected ({len(new_jobs)} new) — notifying latest {PREVIEW_COUNT} only")
        notify_jobs = new_jobs[:PREVIEW_COUNT]
    else:
        notify_jobs = new_jobs

    ntfy_limit = 10  # cap push notifications per run to avoid rate limiting
    for i, job in enumerate(notify_jobs):
        print(f"  NEW [{job.get('source')}] {job['title']} — {job.get('location')}")
        if i < ntfy_limit:
            notify(job)
            time.sleep(0.3)

    if len(notify_jobs) > ntfy_limit:
        print(f"  (ntfy capped at {ntfy_limit}; full list in email digest)")

    # Always mark ALL new jobs as seen (prevents re-flood on next run)
    for job in new_jobs:
        seen.add(job['id'])

    notify_email_digest(notify_jobs)

    save_seen(seen)
    print(f"\nDone. Seen IDs saved: {len(seen)}")


if __name__ == "__main__":
    main()
