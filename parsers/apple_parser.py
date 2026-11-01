import re

POS_ID_RE   = re.compile(r'\\"positionId\\":\\"(\d+)\\"')
TITLE_RE    = re.compile(r'\\"postingTitle\\":\\"([^"\\\\]+)\\"')
SLUG_RE     = re.compile(r'\\"transformedPostingTitle\\":\\"([^"\\\\]+)\\"')
LOC_NAME_RE = re.compile(r'\\"name\\":\\"([^"\\\\]+)\\",\\"countryID\\":\\"iso-country-IND\\"')


def _unescape(s):
    return re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)


def parse_apple_jobs(html):
    jobs = []
    seen = set()
    pos_matches = list(POS_ID_RE.finditer(html))

    for i, m in enumerate(pos_matches):
        job_id = m.group(1)
        if job_id in seen:
            continue
        seen.add(job_id)

        start = m.start()
        end   = pos_matches[i + 1].start() if i + 1 < len(pos_matches) else start + 4000
        chunk = html[start:end]

        title_m = TITLE_RE.search(chunk)
        if not title_m:
            continue

        slug_m   = SLUG_RE.search(chunk)
        cities   = list(dict.fromkeys(LOC_NAME_RE.findall(chunk)))
        title    = _unescape(title_m.group(1))
        slug     = slug_m.group(1) if slug_m else str(job_id)
        location = ', '.join(cities) + ', India' if cities else 'India'

        jobs.append({
            'id':       f'apple-{job_id}',
            'title':    title,
            'location': location,
            'url':      f'https://jobs.apple.com/en-in/details/{job_id}/{slug}',
            'source':   'Apple',
        })

    return jobs
