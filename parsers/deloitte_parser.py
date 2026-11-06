import re

JOB_RE = re.compile(
    r'href="(\/job\/[^"]+?\/(\d{6,})\/?)"[^>]*class="jobTitle-link"[^>]*>([^<]+)<\/a>'
)
LOC_RE = re.compile(r'class="jobLocation"[^>]*>\s*([\w\s,()./\'-]+?)\s*<\/span>')


def _decode(s):
    for esc, char in [('&amp;', '&'), ('&#39;', "'"), ('&quot;', '"'), ('&lt;', '<'), ('&gt;', '>')]:
        s = s.replace(esc, char)
    return s.strip()


def parse_deloitte_jobs(html):
    jobs = []
    seen = set()

    for m in JOB_RE.finditer(html):
        job_id = m.group(2)
        if job_id in seen:
            continue
        seen.add(job_id)

        path  = m.group(1)
        title = _decode(m.group(3))
        chunk = html[m.start():m.start() + 2000]
        loc_m = LOC_RE.search(chunk)
        raw   = re.sub(r'\s+', ' ', loc_m.group(1)).strip() if loc_m else 'India'
        location = re.sub(r',\s*IN\s*$', ', India', raw)

        jobs.append({
            'id':       f'deloitte-{job_id}',
            'title':    title,
            'location': location,
            'url':      f'https://southasiacareers.deloitte.com{path}',
            'source':   'Deloitte',
        })

    return jobs


def parse_deloitte_job_detail(html):
    """Extract the full plain-text job description from a Deloitte detail page."""
    text = re.sub(r'<[^>]+>', ' ', html)
    return re.sub(r'\s+', ' ', text)
