import re

H3_RE       = re.compile(r'<h3[^>]*>([\s\S]*?)</h3>')
JOB_ID_RE   = re.compile(r'jobs/results/(\d+)')
LOCATION_RE = re.compile(r'([A-Za-z][A-Za-z .\'-]*(?:,\s*[A-Za-z][A-Za-z .\'"-]*){1,3})')
POSTED_RE   = re.compile(
    r'(\d+\s*(?:minute|minutes|hour|hours|day|days|week|weeks|m|h|d)\s*ago'
    r'|just\s*(?:now|posted))',
    re.IGNORECASE,
)


def _strip_tags(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    for esc, char in [('&amp;', '&'), ('&#39;', "'"), ('&quot;', '"'), ('&lt;', '<'), ('&gt;', '>')]:
        text = text.replace(esc, char)
    return re.sub(r'\s+', ' ', text).strip()


def parse_google_jobs(html):
    headings = [
        {'pos': m.start(), 'text': _strip_tags(m.group(1))}
        for m in H3_RE.finditer(html)
        if _strip_tags(m.group(1))
    ]

    jobs = []
    seen = set()
    for m in JOB_ID_RE.finditer(html):
        job_id = m.group(1)
        if job_id in seen:
            continue
        seen.add(job_id)
        pos = m.start()

        title = next(
            (h['text'] for h in reversed(headings) if h['pos'] < pos),
            None,
        )
        if not title:
            continue

        window = html[max(0, pos - 3000):pos]
        loc_matches = LOCATION_RE.findall(window)
        location = ' / '.join(dict.fromkeys(l.strip() for l in loc_matches)) or 'Unknown'
        posted_m = POSTED_RE.search(window)

        jobs.append({
            'id':       job_id,
            'title':    title,
            'location': location,
            'posted':   posted_m.group(1) if posted_m else None,
            'url':      f'https://www.google.com/about/careers/applications/jobs/results/{job_id}',
            'source':   'Google',
        })

    return jobs
