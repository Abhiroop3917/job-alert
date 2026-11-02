import re

# Amazon's JSON API ignores the industry_experience=less_than_1_year URL filter.
# These title patterns identify senior/experienced roles to exclude.
_SENIOR_RE = re.compile(
    r'\b(sr|senior|manager|director|principal|lead|staff|head|vp|vice\s+president'
    r'|sdm|sde\s*iii|sde\s*ii|ii|iii|iv)\b',
    re.IGNORECASE,
)


def _is_entry_level(title):
    return not _SENIOR_RE.search(title)


def parse_amazon_jobs(data):
    """Parse Amazon Jobs JSON API response, keeping only entry-level roles."""
    jobs = []
    for j in data.get('jobs', []):
        jid = str(j.get('id_icims', ''))
        if not jid:
            continue
        title = j.get('title', '').strip()
        if not _is_entry_level(title):
            continue
        jobs.append({
            'id':       f'amazon-{jid}',
            'title':    title,
            'location': j.get('location', ''),
            'url':      f"https://amazon.jobs{j.get('job_path', '')}",
            'posted':   j.get('posted_date', ''),
            'source':   'Amazon',
        })
    return jobs
